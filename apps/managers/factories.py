"""
Factory Method pattern implementation for service creation and alert management.

This module implements the Factory Method pattern for creating services,
alerts, and notifications in the Service Manager context.
"""
from typing import Dict, Any, Optional, List
import uuid
from django.utils import timezone
# from django.contrib.gis.geos import Point  # Commented out for now
from django.db import transaction

from apps.core.models import User
from apps.services.models import Service, ServiceCategory, ServiceAlert
from apps.managers.models import ManagerNotification, ServiceStatusHistory


class ServiceFactory:
    """
    Factory for creating different types of services.
    
    Implements the Factory Method pattern to create services
    with proper validation, defaults, and manager assignment.
    """
    
    @staticmethod
    def create_service(service_type: str, manager: User, **kwargs) -> Service:
        """
        Create a service based on type with appropriate defaults.
        
        Args:
            service_type: Type of service to create
            manager: Service manager who will own the service
            **kwargs: Additional service parameters
            
        Returns:
            Created Service instance
        """
        with transaction.atomic():
            # Get or create category
            category = ServiceFactory._get_or_create_category(service_type, kwargs)
            
            # Set default values based on service type
            defaults = ServiceFactory._get_service_defaults(service_type)
            
            # Merge provided kwargs with defaults
            service_data = {**defaults, **kwargs}
            service_data['category'] = category
            service_data['manager'] = manager
            
            # Validate required fields
            ServiceFactory._validate_service_data(service_data)
            
            # Create the service
            service = Service.objects.create(**service_data)
            
            # Create initial status history entry
            ServiceStatusHistory.objects.create(
                service=service,
                manager=manager,
                change_type='service_created',
                new_value=service.current_status,
                description=f"Service '{service.name}' created by {manager.get_display_name()}"
            )
            
            # Create welcome notification for manager
            ManagerNotification.objects.create(
                manager=manager,
                notification_type='service_approved',
                title=f"Service '{service.name}' Created Successfully",
                message=f"Your new service has been created and is ready for management. You can now update its status, capacity, and other details.",
                priority='normal',
                related_service=service,
                action_url=f"/manager/services/{service.id}/edit/"
            )
            
            return service
    
    @staticmethod
    def create_emergency_service(manager: User, **kwargs) -> Service:
        """Create an emergency service with emergency-specific defaults."""
        emergency_defaults = {
            'is_emergency_service': True,
            'is_24_7': True,
            'accepts_walk_ins': True,
            'is_free': True,
            'current_status': 'open',
        }
        return ServiceFactory.create_service('emergency', manager, **emergency_defaults, **kwargs)
    
    @staticmethod
    def create_healthcare_service(manager: User, **kwargs) -> Service:
        """Create a healthcare service with healthcare-specific defaults."""
        healthcare_defaults = {
            'requires_appointment': True,
            'accepts_walk_ins': False,
            'is_free': False,
        }
        return ServiceFactory.create_service('healthcare', manager, **healthcare_defaults, **kwargs)
    
    @staticmethod
    def create_shelter_service(manager: User, **kwargs) -> Service:
        """Create a shelter service with shelter-specific defaults."""
        shelter_defaults = {
            'is_24_7': True,
            'accepts_walk_ins': True,
            'is_free': True,
            'max_capacity': 50,  # Default capacity for shelters
        }
        return ServiceFactory.create_service('shelter', manager, **shelter_defaults, **kwargs)
    
    @staticmethod
    def create_food_service(manager: User, **kwargs) -> Service:
        """Create a food service with food-specific defaults."""
        food_defaults = {
            'accepts_walk_ins': True,
            'is_free': True,
            'max_capacity': 100,
        }
        return ServiceFactory.create_service('food', manager, **food_defaults, **kwargs)
    
    @staticmethod
    def _get_or_create_category(service_type: str, kwargs: Dict[str, Any]) -> ServiceCategory:
        """Get or create appropriate category for service type."""
        if 'category' in kwargs and kwargs['category']:
            return kwargs.pop('category')
        
        # Map service types to categories
        category_mapping = {
            'emergency': 'emergency',
            'healthcare': 'healthcare',
            'shelter': 'shelter',
            'food': 'food',
            'education': 'education',
            'social': 'social',
            'employment': 'employment',
            'legal': 'legal',
            'transportation': 'transportation',
            'utilities': 'utilities',
            'recreation': 'recreation',
        }
        
        category_type = category_mapping.get(service_type, 'other')
        category, created = ServiceCategory.objects.get_or_create(
            category_type=category_type,
            defaults={
                'name': service_type.title() + ' Services',
                'description': f'Services related to {service_type}',
                'is_active': True,
            }
        )
        return category
    
    @staticmethod
    def _get_service_defaults(service_type: str) -> Dict[str, Any]:
        """Get default values for specific service types."""
        common_defaults = {
            'current_status': 'open',
            'current_capacity': 0,
            'is_verified': False,
            'is_active': True,
            'quality_score': 0.00,
            'total_ratings': 0,
            'search_vector': '',
        }
        
        type_specific_defaults = {
            'emergency': {
                'is_emergency_service': True,
                'is_24_7': True,
                'accepts_walk_ins': True,
                'is_free': True,
            },
            'healthcare': {
                'requires_appointment': True,
                'accepts_walk_ins': False,
                'is_free': False,
            },
            'shelter': {
                'is_24_7': True,
                'accepts_walk_ins': True,
                'is_free': True,
                'max_capacity': 50,
            },
            'food': {
                'accepts_walk_ins': True,
                'is_free': True,
                'max_capacity': 100,
            },
        }
        
        defaults = common_defaults.copy()
        defaults.update(type_specific_defaults.get(service_type, {}))
        return defaults
    
    @staticmethod
    def _validate_service_data(service_data: Dict[str, Any]) -> None:
        """Validate required service data."""
        required_fields = ['name', 'description', 'address', 'latitude', 'longitude', 'city']
        missing_fields = [field for field in required_fields if not service_data.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required fields: {', '.join(missing_fields)}")
        
        # Validate coordinates
        lat, lng = service_data.get('latitude'), service_data.get('longitude')
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            raise ValueError("Invalid latitude/longitude coordinates")


class ServiceAlertFactory:
    """
    Factory for creating different types of service alerts.
    
    Creates alerts with appropriate defaults based on alert type
    and automatically handles notification creation.
    """
    
    @staticmethod
    def create_alert(alert_type: str, service: Service, manager: User, **kwargs) -> ServiceAlert:
        """
        Create a service alert based on type.
        
        Args:
            alert_type: Type of alert to create
            service: Service the alert relates to
            manager: Manager creating the alert
            **kwargs: Additional alert parameters
            
        Returns:
            Created ServiceAlert instance
        """
        with transaction.atomic():
            # Get default values for alert type
            defaults = ServiceAlertFactory._get_alert_defaults(alert_type)
            
            # Merge provided kwargs with defaults
            alert_data = {**defaults, **kwargs}
            alert_data['service'] = service
            alert_data['created_by'] = manager
            alert_data['alert_type'] = alert_type
            
            # Validate alert data
            ServiceAlertFactory._validate_alert_data(alert_data)
            
            # Create the alert
            alert = ServiceAlert.objects.create(**alert_data)
            
            # Create status history entry
            ServiceStatusHistory.objects.create(
                service=service,
                manager=manager,
                change_type='alert_created',
                new_value=alert.title,
                description=f"Alert created: {alert.title}"
            )
            
            # Create notification for manager
            ManagerNotification.objects.create(
                manager=manager,
                notification_type='system_announcement',
                title=f"Alert Created for {service.name}",
                message=f"Your alert '{alert.title}' has been created and is now active.",
                priority='normal',
                related_service=service,
                action_url=f"/manager/services/{service.id}/status/"
            )
            
            return alert
    
    @staticmethod
    def create_emergency_alert(service: Service, manager: User, message: str, **kwargs) -> ServiceAlert:
        """Create an urgent emergency alert."""
        return ServiceAlertFactory.create_alert(
            'urgent',
            service,
            manager,
            title='Emergency Alert',
            message=message,
            priority=5,
            requires_acknowledgment=True,
            **kwargs
        )
    
    @staticmethod
    def create_capacity_alert(service: Service, manager: User, capacity_level: str, **kwargs) -> ServiceAlert:
        """Create a capacity-related alert."""
        capacity_messages = {
            'full': 'Service is currently at full capacity.',
            'near_full': 'Service is approaching full capacity.',
            'limited': 'Service has limited availability.',
        }
        
        return ServiceAlertFactory.create_alert(
            'capacity',
            service,
            manager,
            title=f'Capacity Alert - {capacity_level.title()}',
            message=capacity_messages.get(capacity_level, 'Capacity status update'),
            priority=3 if capacity_level == 'full' else 2,
            **kwargs
        )
    
    @staticmethod
    def create_closure_alert(service: Service, manager: User, reason: str, end_time: Optional[timezone.datetime] = None, **kwargs) -> ServiceAlert:
        """Create a temporary closure alert."""
        return ServiceAlertFactory.create_alert(
            'closure',
            service,
            manager,
            title='Temporary Closure',
            message=f'Service temporarily closed: {reason}',
            priority=4,
            end_time=end_time,
            **kwargs
        )
    
    @staticmethod
    def create_schedule_alert(service: Service, manager: User, schedule_change: str, **kwargs) -> ServiceAlert:
        """Create a schedule change alert."""
        return ServiceAlertFactory.create_alert(
            'schedule',
            service,
            manager,
            title='Schedule Change',
            message=f'Schedule update: {schedule_change}',
            priority=2,
            **kwargs
        )
    
    @staticmethod
    def _get_alert_defaults(alert_type: str) -> Dict[str, Any]:
        """Get default values for specific alert types."""
        common_defaults = {
            'is_active': True,
            'start_time': timezone.now(),
            'show_on_map': True,
            'requires_acknowledgment': False,
        }
        
        type_specific_defaults = {
            'urgent': {
                'priority': 5,
                'requires_acknowledgment': True,
                'show_on_map': True,
            },
            'capacity': {
                'priority': 3,
                'show_on_map': True,
            },
            'closure': {
                'priority': 4,
                'requires_acknowledgment': True,
                'show_on_map': True,
            },
            'schedule': {
                'priority': 2,
                'show_on_map': False,
            },
            'info': {
                'priority': 1,
                'show_on_map': False,
            },
        }
        
        defaults = common_defaults.copy()
        defaults.update(type_specific_defaults.get(alert_type, {}))
        return defaults
    
    @staticmethod
    def _validate_alert_data(alert_data: Dict[str, Any]) -> None:
        """Validate alert data."""
        required_fields = ['title', 'message']
        missing_fields = [field for field in required_fields if not alert_data.get(field)]
        
        if missing_fields:
            raise ValueError(f"Missing required alert fields: {', '.join(missing_fields)}")
        
        # Validate priority
        priority = alert_data.get('priority', 1)
        if not (1 <= priority <= 5):
            raise ValueError("Priority must be between 1 and 5")


class NotificationFactory:
    """
    Factory for creating manager notifications.
    
    Creates notifications for various manager events and activities
    with appropriate priorities and content.
    """
    
    @staticmethod
    def create_notification(notification_type: str, manager: User, **kwargs) -> ManagerNotification:
        """
        Create a manager notification based on type.
        
        Args:
            notification_type: Type of notification to create
            manager: Manager to receive the notification
            **kwargs: Additional notification parameters
            
        Returns:
            Created ManagerNotification instance
        """
        # Get default values for notification type
        defaults = NotificationFactory._get_notification_defaults(notification_type)
        
        # Merge provided kwargs with defaults
        notification_data = {**defaults, **kwargs}
        notification_data['manager'] = manager
        notification_data['notification_type'] = notification_type
        
        # Create the notification
        return ManagerNotification.objects.create(**notification_data)
    
    @staticmethod
    def create_capacity_warning(manager: User, service: Service, capacity_percentage: float) -> ManagerNotification:
        """Create a capacity warning notification."""
        return NotificationFactory.create_notification(
            'capacity_alert',
            manager,
            title=f"Capacity Warning - {service.name}",
            message=f"Your service is at {capacity_percentage:.1f}% capacity. Consider updating availability status.",
            priority='high',
            related_service=service,
            action_url=f"/manager/services/{service.id}/status/"
        )
    
    @staticmethod
    def create_feedback_notification(manager: User, service: Service, feedback_count: int) -> ManagerNotification:
        """Create a new feedback notification."""
        return NotificationFactory.create_notification(
            'feedback_received',
            manager,
            title=f"New Feedback - {service.name}",
            message=f"You have {feedback_count} new feedback submission{'s' if feedback_count != 1 else ''} to review.",
            priority='normal',
            related_service=service,
            action_url=f"/manager/services/{service.id}/feedback/"
        )
    
    @staticmethod
    def create_status_reminder(manager: User, service: Service, hours_since_update: int) -> ManagerNotification:
        """Create a status update reminder."""
        return NotificationFactory.create_notification(
            'status_reminder',
            manager,
            title=f"Status Update Reminder - {service.name}",
            message=f"Your service status hasn't been updated in {hours_since_update} hours. Please verify current status.",
            priority='normal',
            related_service=service,
            action_url=f"/manager/services/{service.id}/status/",
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
    
    @staticmethod
    def _get_notification_defaults(notification_type: str) -> Dict[str, Any]:
        """Get default values for specific notification types."""
        return {
            'is_read': False,
            'priority': 'normal',
        } 