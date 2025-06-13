"""
Django signals implementing Observer pattern for CommuMap services.

This module provides real-time notifications for service status changes
using Django's signal system as the Observer pattern implementation.
"""
import logging
from typing import List, Dict, Any, Optional
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver, Signal
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.utils import timezone

from .models import Service, RealTimeStatusUpdate, ServiceAlert, ServiceStatus
from apps.core.models import AuditLog

User = get_user_model()
logger = logging.getLogger(__name__)

# Custom signals for specific events
service_capacity_changed = Signal()
service_status_changed = Signal()
emergency_alert_created = Signal()


class NotificationDispatcher:
    """
    Singleton notification dispatcher implementing Observer pattern.
    
    Manages subscriptions and dispatches notifications to various
    observers (WebSocket clients, external systems, etc.).
    """
    _instance = None
    _observers = []
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._observers = []
        return cls._instance
    
    def subscribe(self, observer):
        """Add an observer to the notification list."""
        if observer not in self._observers:
            self._observers.append(observer)
            logger.debug(f"Observer {observer} subscribed to notifications")
    
    def unsubscribe(self, observer):
        """Remove an observer from the notification list."""
        if observer in self._observers:
            self._observers.remove(observer)
            logger.debug(f"Observer {observer} unsubscribed from notifications")
    
    def notify_observers(self, event_type: str, data: Dict[str, Any]):
        """Notify all observers of an event."""
        for observer in self._observers:
            try:
                if hasattr(observer, 'handle_notification'):
                    observer.handle_notification(event_type, data)
                else:
                    logger.warning(f"Observer {observer} doesn't implement handle_notification")
            except Exception as e:
                logger.error(f"Error notifying observer {observer}: {e}")
    
    def get_observer_count(self) -> int:
        """Get the number of registered observers."""
        return len(self._observers)


# Get the singleton instance
notification_dispatcher = NotificationDispatcher()


@receiver(pre_save, sender=Service)
def capture_service_changes(sender, instance, **kwargs):
    """
    Capture service changes before save to track what changed.
    
    This signal runs before a Service is saved to store the previous
    state for comparison in the post_save signal.
    """
    if instance.pk:  # Only for existing services
        try:
            old_service = Service.objects.get(pk=instance.pk)
            # Store old values in a cache key
            cache_key = f"service_old_state_{instance.pk}"
            old_state = {
                'current_status': old_service.current_status,
                'current_capacity': old_service.current_capacity,
                'max_capacity': old_service.max_capacity,
                'is_verified': old_service.is_verified,
                'is_active': old_service.is_active,
            }
            cache.set(cache_key, old_state, 300)  # 5 minutes cache
        except Service.DoesNotExist:
            pass


@receiver(post_save, sender=Service)
def handle_service_update(sender, instance, created, **kwargs):
    """
    Handle service updates and trigger appropriate notifications.
    
    This is the main Observer pattern implementation for service changes.
    It detects what changed and dispatches notifications accordingly.
    """
    try:
        if created:
            # New service created
            _handle_service_created(instance)
        else:
            # Existing service updated
            _handle_service_updated(instance)
    except Exception as e:
        logger.error(f"Error handling service update for {instance}: {e}")


def _handle_service_created(service: Service):
    """Handle new service creation."""
    logger.info(f"New service created: {service.name}")
    
    # Create audit log
    AuditLog.objects.create(
        user=service.manager,
        action='service_created',
        description=f"Created service: {service.name}",
        metadata={
            'service_id': str(service.id),
            'service_name': service.name,
            'category': service.category.name if service.category else None,
        }
    )
    
    # Notify observers
    notification_data = {
        'service_id': str(service.id),
        'service_name': service.name,
        'category': service.category.name if service.category else None,
        'location': {
            'lat': service.location.y,
            'lng': service.location.x,
        },
        'created_at': service.created_at.isoformat(),
    }
    
    notification_dispatcher.notify_observers('service_created', notification_data)


def _handle_service_updated(service: Service):
    """Handle service updates and detect specific changes."""
    cache_key = f"service_old_state_{service.pk}"
    old_state = cache.get(cache_key)
    
    if not old_state:
        return  # Can't compare without old state
    
    changes_detected = []
    
    # Check for status changes
    if old_state['current_status'] != service.current_status:
        changes_detected.append('status')
        _handle_status_change(service, old_state['current_status'], service.current_status)
    
    # Check for capacity changes
    if old_state['current_capacity'] != service.current_capacity:
        changes_detected.append('capacity')
        _handle_capacity_change(service, old_state['current_capacity'], service.current_capacity)
    
    # Check for verification changes
    if old_state['is_verified'] != service.is_verified and service.is_verified:
        changes_detected.append('verification')
        _handle_service_verified(service)
    
    # Check for activation changes
    if old_state['is_active'] != service.is_active:
        changes_detected.append('activation')
        _handle_activation_change(service, service.is_active)
    
    # Clean up cache
    cache.delete(cache_key)
    
    if changes_detected:
        logger.info(f"Service {service.name} updated. Changes: {', '.join(changes_detected)}")


def _handle_status_change(service: Service, old_status: str, new_status: str):
    """Handle service status changes."""
    from .factories import StatusUpdateFactory
    
    # Create status update record
    try:
        status_update = StatusUpdateFactory.create_status_change_update(
            service=service,
            old_status=old_status,
            new_status=new_status,
            updated_by=service.status_updated_by
        )
        
        # Create audit log
        AuditLog.objects.create(
            user=service.status_updated_by,
            action='service_status_changed',
            description=f"Service {service.name} status changed from {old_status} to {new_status}",
            metadata={
                'service_id': str(service.id),
                'old_status': old_status,
                'new_status': new_status,
            }
        )
        
        # Emit custom signal
        service_status_changed.send(
            sender=Service,
            service=service,
            old_status=old_status,
            new_status=new_status,
            status_update=status_update
        )
        
        # Check if this is an emergency-related change
        emergency_statuses = [ServiceStatus.EMERGENCY_ONLY, ServiceStatus.TEMPORARILY_CLOSED]
        if new_status in emergency_statuses or (service.is_emergency_service and new_status == ServiceStatus.CLOSED):
            _handle_emergency_status_change(service, old_status, new_status)
        
        # Notify observers
        notification_data = {
            'service_id': str(service.id),
            'service_name': service.name,
            'old_status': old_status,
            'new_status': new_status,
            'timestamp': timezone.now().isoformat(),
            'is_emergency_related': service.is_emergency_service,
        }
        
        notification_dispatcher.notify_observers('status_changed', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling status change for {service}: {e}")


def _handle_capacity_change(service: Service, old_capacity: int, new_capacity: int):
    """Handle service capacity changes."""
    from .factories import StatusUpdateFactory, AlertFactory
    
    try:
        # Create capacity update record
        capacity_update = StatusUpdateFactory.create_capacity_update(
            service=service,
            old_capacity=old_capacity,
            new_capacity=new_capacity,
            updated_by=service.status_updated_by
        )
        
        # Emit custom signal
        service_capacity_changed.send(
            sender=Service,
            service=service,
            old_capacity=old_capacity,
            new_capacity=new_capacity,
            capacity_update=capacity_update
        )
        
        # Check if capacity alerts are needed
        capacity_percentage = service.capacity_percentage
        if capacity_percentage:
            # Create alerts for significant capacity changes
            if capacity_percentage >= 90 and (old_capacity / service.max_capacity * 100) < 90:
                # Crossed into high capacity
                AlertFactory.create_capacity_alert(service, service.status_updated_by)
            elif capacity_percentage >= 100 and old_capacity < service.max_capacity:
                # Reached full capacity
                AlertFactory.create_alert(
                    service=service,
                    alert_type='capacity',
                    title=f"{service.name} is at full capacity",
                    message="This service is currently at full capacity. Please check back later.",
                    created_by=service.status_updated_by,
                    priority=4
                )
        
        # Notify observers
        notification_data = {
            'service_id': str(service.id),
            'service_name': service.name,
            'old_capacity': old_capacity,
            'new_capacity': new_capacity,
            'max_capacity': service.max_capacity,
            'capacity_percentage': capacity_percentage,
            'timestamp': timezone.now().isoformat(),
        }
        
        notification_dispatcher.notify_observers('capacity_changed', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling capacity change for {service}: {e}")


def _handle_service_verified(service: Service):
    """Handle service verification."""
    try:
        # Create audit log
        AuditLog.objects.create(
            user=service.verified_by,
            action='service_verified',
            description=f"Service {service.name} was verified",
            metadata={
                'service_id': str(service.id),
                'verified_by': str(service.verified_by.id) if service.verified_by else None,
                'verified_at': service.verified_at.isoformat() if service.verified_at else None,
            }
        )
        
        # Notify service manager if available
        if service.manager and service.manager.email:
            _queue_verification_notification(service)
        
        # Notify observers
        notification_data = {
            'service_id': str(service.id),
            'service_name': service.name,
            'verified_by': service.verified_by.get_display_name() if service.verified_by else None,
            'timestamp': timezone.now().isoformat(),
        }
        
        notification_dispatcher.notify_observers('service_verified', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling service verification for {service}: {e}")


def _handle_activation_change(service: Service, is_active: bool):
    """Handle service activation/deactivation."""
    try:
        action = 'activated' if is_active else 'deactivated'
        
        # Create audit log
        AuditLog.objects.create(
            user=service.status_updated_by,
            action=f'service_{action}',
            description=f"Service {service.name} was {action}",
            metadata={
                'service_id': str(service.id),
                'is_active': is_active,
            }
        )
        
        # Notify observers
        notification_data = {
            'service_id': str(service.id),
            'service_name': service.name,
            'is_active': is_active,
            'action': action,
            'timestamp': timezone.now().isoformat(),
        }
        
        notification_dispatcher.notify_observers('service_activation_changed', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling activation change for {service}: {e}")


def _handle_emergency_status_change(service: Service, old_status: str, new_status: str):
    """Handle emergency-related status changes."""
    try:
        # Create emergency alert
        if new_status == ServiceStatus.EMERGENCY_ONLY:
            message = f"{service.name} is now operating in emergency-only mode."
        elif new_status == ServiceStatus.TEMPORARILY_CLOSED:
            message = f"{service.name} has been temporarily closed."
        else:
            message = f"{service.name} emergency status has changed."
        
        from .factories import AlertFactory
        alert = AlertFactory.create_emergency_alert(
            service=service,
            emergency_message=message,
            created_by=service.status_updated_by
        )
        
        # Emit emergency signal
        emergency_alert_created.send(
            sender=ServiceAlert,
            alert=alert,
            service=service
        )
        
        # High-priority notification
        notification_data = {
            'service_id': str(service.id),
            'service_name': service.name,
            'alert_id': str(alert.id),
            'alert_message': message,
            'priority': 'emergency',
            'timestamp': timezone.now().isoformat(),
        }
        
        notification_dispatcher.notify_observers('emergency_alert', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling emergency status change for {service}: {e}")


def _queue_verification_notification(service: Service):
    """Queue email notification for service verification (placeholder)."""
    # This would integrate with a task queue like Celery in production
    logger.info(f"Queuing verification notification for {service.manager.email}")


@receiver(post_save, sender=ServiceAlert)
def handle_alert_created(sender, instance, created, **kwargs):
    """Handle new service alerts."""
    if created and instance.is_current:
        try:
            # Notify observers of new alert
            notification_data = {
                'alert_id': str(instance.id),
                'service_id': str(instance.service.id),
                'service_name': instance.service.name,
                'alert_type': instance.alert_type,
                'title': instance.title,
                'message': instance.message,
                'priority': instance.priority,
                'show_on_map': instance.show_on_map,
                'timestamp': instance.created_at.isoformat(),
            }
            
            event_type = 'emergency_alert' if instance.priority >= 4 else 'service_alert'
            notification_dispatcher.notify_observers(event_type, notification_data)
            
        except Exception as e:
            logger.error(f"Error handling alert creation for {instance}: {e}")


@receiver(post_delete, sender=Service)
def handle_service_deleted(sender, instance, **kwargs):
    """Handle service deletion."""
    try:
        # Create audit log
        AuditLog.objects.create(
            action='service_deleted',
            description=f"Service {instance.name} was deleted",
            metadata={
                'service_id': str(instance.id),
                'service_name': instance.name,
            }
        )
        
        # Notify observers
        notification_data = {
            'service_id': str(instance.id),
            'service_name': instance.name,
            'timestamp': timezone.now().isoformat(),
        }
        
        notification_dispatcher.notify_observers('service_deleted', notification_data)
        
    except Exception as e:
        logger.error(f"Error handling service deletion: {e}")


# WebSocket notification observer (placeholder for real-time features)
class WebSocketNotificationObserver:
    """
    Observer for sending real-time notifications via WebSocket.
    
    This would integrate with Django Channels in a full implementation.
    """
    
    def handle_notification(self, event_type: str, data: Dict[str, Any]):
        """Handle notification by sending to WebSocket clients."""
        try:
            # This would use Django Channels to send to connected clients
            logger.info(f"WebSocket notification: {event_type} - {data.get('service_name', 'Unknown')}")
            
            # Placeholder for actual WebSocket implementation
            # from channels.layers import get_channel_layer
            # channel_layer = get_channel_layer()
            # async_to_sync(channel_layer.group_send)(
            #     "service_updates",
            #     {
            #         "type": "service_notification",
            #         "event_type": event_type,
            #         "data": data,
            #     }
            # )
            
        except Exception as e:
            logger.error(f"Error sending WebSocket notification: {e}")


# Email notification observer (placeholder)
class EmailNotificationObserver:
    """
    Observer for sending email notifications to subscribed users.
    """
    
    def handle_notification(self, event_type: str, data: Dict[str, Any]):
        """Handle notification by sending emails."""
        try:
            # Placeholder for email notification logic
            # This would integrate with Django's email system or a service like SendGrid
            if event_type in ['emergency_alert', 'service_verified']:
                logger.info(f"Email notification: {event_type} - {data.get('service_name', 'Unknown')}")
                
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")


# Register default observers
websocket_observer = WebSocketNotificationObserver()
email_observer = EmailNotificationObserver()

notification_dispatcher.subscribe(websocket_observer)
notification_dispatcher.subscribe(email_observer)


# Utility functions for external integration
def get_notification_dispatcher() -> NotificationDispatcher:
    """Get the singleton notification dispatcher instance."""
    return notification_dispatcher


def register_notification_observer(observer) -> None:
    """Register a new notification observer."""
    notification_dispatcher.subscribe(observer)


def unregister_notification_observer(observer) -> None:
    """Unregister a notification observer."""
    notification_dispatcher.unsubscribe(observer) 