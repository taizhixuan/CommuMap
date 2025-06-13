"""
Singleton managers for the Admin Console.

This module implements the Singleton pattern for system-wide managers
including NotificationDispatcher and SettingsLoader.
"""
import logging
import threading
from typing import Dict, List, Optional, Any
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.db import transaction
from apps.core.models import SystemSettings, User


logger = logging.getLogger(__name__)


class NotificationDispatcher:
    """
    Singleton notification manager for system-wide messaging.
    
    Handles email, SMS, and in-app notifications with queue management
    and delivery tracking.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the notification dispatcher."""
        self._notification_queues = {
            'email': [],
            'sms': [],
            'in_app': [],
            'system': [],
            'emergency': []
        }
        self._initialized = True
        logger.info("NotificationDispatcher singleton initialized")
    
    def send_system_announcement(self, message: str, title: str = "System Announcement", 
                                target_roles: Optional[List[str]] = None, 
                                announcement_type: str = 'info') -> bool:
        """
        Send a system-wide announcement to targeted user roles.
        
        Args:
            message: The announcement message
            title: The announcement title
            target_roles: List of user roles to target (None = all users)
            announcement_type: Type of announcement (info, warning, emergency, maintenance)
        
        Returns:
            bool: True if announcement was queued successfully
        """
        try:
            from .models import SystemAnnouncement
            
            # Get the admin user making this announcement
            admin_user = User.objects.filter(role='admin', is_verified=True).first()
            if not admin_user:
                logger.error("No verified admin user found for system announcement")
                return False
            
            # Create the announcement
            announcement = SystemAnnouncement.objects.create(
                title=title,
                content=message,
                announcement_type=announcement_type,
                target_roles=target_roles or [],
                created_by=admin_user,
                is_active=True
            )
            
            # Queue notifications for targeted users
            target_users = self._get_users_by_roles(target_roles)
            
            for user in target_users:
                self.queue_notification(
                    notification_type='in_app',
                    recipients=[user],
                    data={
                        'subject': title,
                        'message': message,
                        'announcement_id': str(announcement.id),
                        'announcement_type': announcement_type
                    }
                )
            
            logger.info(f"System announcement '{title}' queued for {len(target_users)} users")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send system announcement: {str(e)}")
            return False
    
    def send_verification_notification(self, user: User, verification_type: str = 'account') -> bool:
        """
        Send verification notification to a user.
        
        Args:
            user: User to notify
            verification_type: Type of verification (account, role_change, etc.)
        
        Returns:
            bool: True if notification was queued successfully
        """
        try:
            if verification_type == 'account':
                subject = "Account Verification Required"
                template = 'console/emails/account_verification.html'
            elif verification_type == 'role_change':
                subject = "Account Verified Successfully"
                template = 'console/emails/role_change.html'
            elif verification_type == 'rejection':
                subject = "Account Verification Update"
                template = 'console/emails/verification_rejected.html'
            else:
                subject = "Verification Notification"
                template = 'console/emails/generic_verification.html'
            
            context = {
                'user': user,
                'verification_type': verification_type,
                'site_name': getattr(settings, 'SITE_NAME', 'CommuMap')
            }
            
            try:
                message = render_to_string(template, context)
            except Exception as template_error:
                logger.warning(f"Template {template} not found or error: {template_error}")
                # Fallback to simple text message
                if verification_type == 'role_change':
                    message = f"Hello {user.get_display_name() or user.email},\n\nYour account has been verified successfully! You now have {user.get_role_display()} privileges.\n\nBest regards,\n{getattr(settings, 'SITE_NAME', 'CommuMap')} Team"
                elif verification_type == 'rejection':
                    message = f"Hello {user.get_display_name() or user.email},\n\nYour verification request has been reviewed. Unfortunately, it has not been approved at this time.\n\nBest regards,\n{getattr(settings, 'SITE_NAME', 'CommuMap')} Team"
                else:
                    message = f"Hello {user.get_display_name() or user.email},\n\nThis is a verification notification from {getattr(settings, 'SITE_NAME', 'CommuMap')}.\n\nBest regards,\nThe Team"
            
            return self.queue_notification(
                notification_type='email',
                recipients=[user],
                data={
                    'subject': subject,
                    'message': message,
                    'verification_type': verification_type
                }
            )
            
        except Exception as e:
            logger.error(f"Failed to send verification notification: {str(e)}")
            return False
    
    def send_emergency_alert(self, service, message: str, alert_type: str = 'emergency') -> bool:
        """
        Send emergency alert for a service to relevant users.
        
        Args:
            service: Service object requiring emergency alert
            message: Emergency message
            alert_type: Type of alert (emergency, urgent, etc.)
        
        Returns:
            bool: True if alert was queued successfully
        """
        try:
            # Get users in the service area who should be notified
            nearby_users = self._get_users_near_service(service)
            
            subject = f"⚠️ Emergency Alert: {service.name}"
            
            for user in nearby_users:
                self.queue_notification(
                    notification_type='emergency',
                    recipients=[user],
                    data={
                        'subject': subject,
                        'message': message,
                        'service_id': str(service.id),
                        'service_name': service.name,
                        'alert_type': alert_type,
                        'urgent': True
                    }
                )
            
            logger.info(f"Emergency alert queued for {len(nearby_users)} users near {service.name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send emergency alert: {str(e)}")
            return False
    
    def queue_notification(self, notification_type: str, recipients: List[User], 
                          data: Dict[str, Any]) -> bool:
        """
        Queue a notification for delivery.
        
        Args:
            notification_type: Type of notification (email, sms, in_app, etc.)
            recipients: List of users to notify
            data: Notification data including subject, message, etc.
        
        Returns:
            bool: True if queued successfully
        """
        try:
            try:
                from .models import NotificationQueue
            except ImportError:
                logger.warning("NotificationQueue model not available, notifications will be logged only")
                for user in recipients:
                    logger.info(f"Would send {notification_type} notification to {user.email}: {data.get('subject', '')}")
                return True
            
            queued_count = 0
            
            for user in recipients:
                notification = NotificationQueue.objects.create(
                    notification_type=notification_type,
                    recipient_user=user,
                    recipient_email=user.email if notification_type == 'email' else '',
                    recipient_phone=user.phone if notification_type == 'sms' else '',
                    subject=data.get('subject', ''),
                    message=data.get('message', ''),
                    data=data,
                    scheduled_for=timezone.now()
                )
                queued_count += 1
            
            logger.info(f"Queued {queued_count} {notification_type} notifications")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue notifications: {str(e)}")
            return False
    
    def process_notification_queue(self) -> int:
        """
        Process pending notifications in the queue.
        
        Returns:
            int: Number of notifications processed
        """
        try:
            from .models import NotificationQueue
            
            pending_notifications = NotificationQueue.objects.filter(
                status='pending',
                scheduled_for__lte=timezone.now()
            )[:100]  # Process in batches
            
            processed_count = 0
            
            for notification in pending_notifications:
                try:
                    if notification.notification_type == 'email':
                        self._send_email_notification(notification)
                    elif notification.notification_type == 'sms':
                        self._send_sms_notification(notification)
                    elif notification.notification_type in ['in_app', 'system', 'emergency']:
                        self._send_in_app_notification(notification)
                    
                    notification.status = 'sent'
                    notification.sent_at = timezone.now()
                    notification.save(update_fields=['status', 'sent_at'])
                    processed_count += 1
                    
                except Exception as e:
                    notification.status = 'failed'
                    notification.error_message = str(e)
                    notification.retry_count += 1
                    notification.save(update_fields=['status', 'error_message', 'retry_count'])
                    logger.error(f"Failed to send notification {notification.id}: {str(e)}")
            
            return processed_count
            
        except Exception as e:
            logger.error(f"Failed to process notification queue: {str(e)}")
            return 0
    
    def _get_users_by_roles(self, roles: Optional[List[str]]) -> List[User]:
        """Get users filtered by roles."""
        if not roles:
            return list(User.objects.filter(is_active=True))
        return list(User.objects.filter(role__in=roles, is_active=True))
    
    def _get_users_near_service(self, service) -> List[User]:
        """Get users near a service for emergency alerts."""
        # For now, return all active users - can be enhanced with geo queries
        return list(User.objects.filter(is_active=True))
    
    def _send_email_notification(self, notification):
        """Send email notification."""
        send_mail(
            subject=notification.subject,
            message=notification.message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[notification.recipient_email],
            html_message=notification.message
        )
    
    def _send_sms_notification(self, notification):
        """Send SMS notification (placeholder for SMS service integration)."""
        # Placeholder for SMS service integration
        logger.info(f"SMS notification sent to {notification.recipient_phone}: {notification.subject}")
    
    def _send_in_app_notification(self, notification):
        """Send in-app notification (stored in database)."""
        # In-app notifications are already stored in the queue
        logger.info(f"In-app notification sent to {notification.recipient_user.email}: {notification.subject}")


class SettingsLoader:
    """
    Singleton settings manager for runtime configuration changes.
    
    Handles system settings, feature flags, and configuration reloading
    without requiring application restart.
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize the settings loader."""
        self._cached_settings = {}
        self._feature_flags = {}
        self._last_reload = timezone.now()
        # Load settings during initialization
        try:
            self._reload_settings()
        except Exception as e:
            logger.warning(f"Could not load settings during initialization: {str(e)}")
        logger.info("SettingsLoader singleton initialized")
    
    def get_system_setting(self, key: str, default: Any = None) -> Any:
        """
        Get a system setting value.
        
        Args:
            key: Setting key
            default: Default value if setting not found
        
        Returns:
            Setting value or default
        """
        try:
            # Check if cache needs refresh (every 5 minutes)
            if (timezone.now() - self._last_reload).seconds > 300:
                self._reload_settings()
            
            return self._cached_settings.get(key, default)
            
        except Exception as e:
            logger.error(f"Failed to get system setting '{key}': {str(e)}")
            return default
    
    def update_setting(self, key: str, value: Any, user: Optional[User] = None) -> bool:
        """
        Update a system setting.
        
        Args:
            key: Setting key
            value: New setting value
            user: User making the change (for audit log)
        
        Returns:
            bool: True if setting was updated successfully
        """
        try:
            settings_instance = SystemSettings.get_instance()
            
            # Update the setting if it exists on the model
            if hasattr(settings_instance, key):
                setattr(settings_instance, key, value)
                settings_instance.save()
                
                # Update cache
                self._cached_settings[key] = value
                
                # Log the change
                if user:
                    from apps.core.models import AuditLog
                    AuditLog.objects.create(
                        user=user,
                        action='system_settings_changed',
                        description=f"Updated system setting '{key}' to '{value}'",
                        metadata={
                            'setting_key': key,
                            'new_value': str(value),
                            'old_value': str(self._cached_settings.get(key, 'N/A'))
                        }
                    )
                
                logger.info(f"System setting '{key}' updated to '{value}'")
                return True
            else:
                logger.warning(f"Unknown system setting '{key}'")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update system setting '{key}': {str(e)}")
            return False
    
    def toggle_feature_flag(self, feature_name: str, user: Optional[User] = None) -> bool:
        """
        Toggle a feature flag.
        
        Args:
            feature_name: Name of the feature flag
            user: User making the change
        
        Returns:
            bool: New state of the feature flag
        """
        try:
            current_state = self._feature_flags.get(feature_name, False)
            new_state = not current_state
            
            # Update in system settings
            setting_key = f"{feature_name}_enabled"
            self.update_setting(setting_key, new_state, user)
            
            # Update local cache
            self._feature_flags[feature_name] = new_state
            
            logger.info(f"Feature flag '{feature_name}' toggled to {new_state}")
            return new_state
            
        except Exception as e:
            logger.error(f"Failed to toggle feature flag '{feature_name}': {str(e)}")
            return self._feature_flags.get(feature_name, False)
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check if a feature flag is enabled.
        
        Args:
            feature_name: Name of the feature flag
        
        Returns:
            bool: True if feature is enabled
        """
        return self._feature_flags.get(feature_name, False)
    
    def reload_configuration(self) -> bool:
        """
        Reload all configuration from the database.
        
        Returns:
            bool: True if reload was successful
        """
        try:
            self._reload_settings()
            logger.info("Configuration reloaded successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {str(e)}")
            return False
    
    def backup_settings(self) -> Dict[str, Any]:
        """
        Create a backup of current settings.
        
        Returns:
            dict: Current settings backup
        """
        try:
            settings_instance = SystemSettings.get_instance()
            backup = {}
            
            # Get all fields from the settings model
            for field in settings_instance._meta.fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    backup[field.name] = getattr(settings_instance, field.name)
            
            backup['backup_timestamp'] = timezone.now().isoformat()
            backup['feature_flags'] = self._feature_flags.copy()
            
            logger.info("Settings backup created")
            return backup
            
        except Exception as e:
            logger.error(f"Failed to backup settings: {str(e)}")
            return {}
    
    def restore_settings(self, backup: Dict[str, Any], user: Optional[User] = None) -> bool:
        """
        Restore settings from backup.
        
        Args:
            backup: Settings backup dictionary
            user: User performing the restore
        
        Returns:
            bool: True if restore was successful
        """
        try:
            settings_instance = SystemSettings.get_instance()
            
            for key, value in backup.items():
                if key not in ['backup_timestamp', 'feature_flags'] and hasattr(settings_instance, key):
                    setattr(settings_instance, key, value)
            
            settings_instance.save()
            
            # Restore feature flags
            if 'feature_flags' in backup:
                self._feature_flags = backup['feature_flags'].copy()
            
            # Reload cache
            self._reload_settings()
            
            # Log the restore
            if user:
                from apps.core.models import AuditLog
                AuditLog.objects.create(
                    user=user,
                    action='system_settings_changed',
                    description="Settings restored from backup",
                    metadata={'backup_timestamp': backup.get('backup_timestamp', 'Unknown')}
                )
            
            logger.info("Settings restored from backup")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore settings: {str(e)}")
            return False
    
    def _reload_settings(self):
        """Reload settings from database into cache."""
        try:
            settings_instance = SystemSettings.get_instance()
            
            # Cache all settings
            for field in settings_instance._meta.fields:
                if field.name not in ['id', 'created_at', 'updated_at']:
                    self._cached_settings[field.name] = getattr(settings_instance, field.name)
            
            # Load feature flags
            self._feature_flags = {
                'registration': self._cached_settings.get('registration_enabled', True),
                'service_submissions': self._cached_settings.get('service_submissions_enabled', True),
                'emergency_mode': self._cached_settings.get('emergency_mode', False),
                'auto_approve_services': self._cached_settings.get('auto_approve_services', False),
                'auto_approve_comments': self._cached_settings.get('auto_approve_comments', False),
                'maintenance_mode': self._cached_settings.get('maintenance_mode', False),
            }
            
            self._last_reload = timezone.now()
            
        except Exception as e:
            logger.error(f"Failed to reload settings: {str(e)}")
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all current settings."""
        return self._cached_settings.copy()
    
    def get_all_feature_flags(self) -> Dict[str, bool]:
        """Get all current feature flags."""
        return self._feature_flags.copy()
    
    def get_feature_flags(self) -> Dict[str, bool]:
        """Get all feature flags as a dictionary (alias for compatibility)."""
        return self.get_all_feature_flags() 