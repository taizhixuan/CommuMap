"""
Factory classes for CommuMap service creation.

This module implements the Factory Method pattern to centralize
creation of services and related objects with proper validation
and default values.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, List
from decimal import Decimal
import uuid

from django.contrib.gis.geos import Point
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.exceptions import ValidationError

from .models import Service, ServiceCategory, ServiceAlert, RealTimeStatusUpdate, ServiceStatus
from apps.core.models import User

User = get_user_model()


class ServiceFactory(ABC):
    """
    Abstract factory for creating Service instances.
    
    Implements the Factory Method pattern to provide consistent
    service creation with validation and default values.
    """
    
    @abstractmethod
    def create_service(self, **kwargs) -> Service:
        """Create a service instance with factory-specific logic."""
        pass
    
    @abstractmethod
    def get_service_type(self) -> str:
        """Return the service type this factory creates."""
        pass
    
    def validate_location(self, location: Point) -> None:
        """Validate geographic location."""
        if not isinstance(location, Point):
            raise ValidationError("Location must be a Point instance")
        
        # Basic geographic bounds validation (can be customized per region)
        lat, lng = location.y, location.x
        if not (-90 <= lat <= 90):
            raise ValidationError(f"Invalid latitude: {lat}")
        if not (-180 <= lng <= 180):
            raise ValidationError(f"Invalid longitude: {lng}")
    
    def validate_required_fields(self, data: Dict[str, Any]) -> None:
        """Validate required fields for service creation."""
        required = ['name', 'description', 'location', 'address', 'city', 'category']
        missing = [field for field in required if not data.get(field)]
        if missing:
            raise ValidationError(f"Missing required fields: {', '.join(missing)}")
    
    def apply_default_values(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply default values for optional fields."""
        defaults = {
            'is_24_7': False,
            'accepts_walk_ins': True,
            'is_free': True,
            'requires_appointment': False,
            'is_emergency_service': False,
            'current_capacity': 0,
            'current_status': ServiceStatus.OPEN,
            'is_active': True,
            'is_verified': False,
            'quality_score': Decimal('0.00'),
            'total_ratings': 0,
            'tags': [],
            'hours_of_operation': {},
            'country': 'United States',
        }
        
        # Apply defaults for missing keys
        for key, default_value in defaults.items():
            if key not in data:
                data[key] = default_value
        
        return data


class HealthcareServiceFactory(ServiceFactory):
    """Factory for creating healthcare and medical services."""
    
    def create_service(self, **kwargs) -> Service:
        """Create a healthcare service with medical-specific defaults."""
        # Validate inputs
        self.validate_required_fields(kwargs)
        self.validate_location(kwargs['location'])
        
        # Apply healthcare-specific defaults
        healthcare_defaults = {
            'requires_appointment': True,  # Most healthcare requires appointments
            'accepts_walk_ins': False,
            'is_free': False,  # Many healthcare services have costs
            'age_restrictions': '',
            'required_documents': 'Insurance card or ID may be required',
        }
        
        # Merge with general defaults
        data = self.apply_default_values(kwargs)
        for key, value in healthcare_defaults.items():
            if key not in kwargs:  # Don't override explicit values
                data[key] = value
        
        # Ensure category is healthcare-related
        if hasattr(data['category'], 'category_type'):
            if data['category'].category_type != 'healthcare':
                raise ValidationError("Healthcare services must use healthcare category")
        
        # Add healthcare-specific tags
        healthcare_tags = ['medical', 'healthcare', 'treatment']
        existing_tags = data.get('tags', [])
        data['tags'] = list(set(existing_tags + healthcare_tags))
        
        return Service.objects.create(**data)
    
    def get_service_type(self) -> str:
        return "healthcare"


class ShelterServiceFactory(ServiceFactory):
    """Factory for creating shelter and housing services."""
    
    def create_service(self, **kwargs) -> Service:
        """Create a shelter service with housing-specific defaults."""
        self.validate_required_fields(kwargs)
        self.validate_location(kwargs['location'])
        
        # Shelter-specific defaults
        shelter_defaults = {
            'is_24_7': True,  # Many shelters operate 24/7
            'accepts_walk_ins': True,
            'is_free': True,  # Most shelters are free
            'requires_appointment': False,
            'is_emergency_service': True,  # Shelters are often emergency services
            'max_capacity': 50,  # Default capacity for shelters
            'eligibility_criteria': 'Must be in need of temporary housing',
            'required_documents': 'Photo ID preferred but not required',
        }
        
        data = self.apply_default_values(kwargs)
        for key, value in shelter_defaults.items():
            if key not in kwargs:
                data[key] = value
        
        # Validate capacity if provided
        if 'max_capacity' in data and data['max_capacity'] < 1:
            raise ValidationError("Shelter capacity must be at least 1")
        
        # Add shelter-specific tags
        shelter_tags = ['shelter', 'housing', 'accommodation', 'temporary']
        existing_tags = data.get('tags', [])
        data['tags'] = list(set(existing_tags + shelter_tags))
        
        return Service.objects.create(**data)
    
    def get_service_type(self) -> str:
        return "shelter"


class FoodServiceFactory(ServiceFactory):
    """Factory for creating food and nutrition services."""
    
    def create_service(self, **kwargs) -> Service:
        """Create a food service with nutrition-specific defaults."""
        self.validate_required_fields(kwargs)
        self.validate_location(kwargs['location'])
        
        # Food service defaults
        food_defaults = {
            'accepts_walk_ins': True,
            'is_free': True,  # Most food banks/pantries are free
            'requires_appointment': False,
            'eligibility_criteria': 'Income verification may be required',
            'hours_of_operation': {
                'monday': '9:00-17:00',
                'tuesday': '9:00-17:00',
                'wednesday': '9:00-17:00',
                'thursday': '9:00-17:00',
                'friday': '9:00-17:00',
                'saturday': '9:00-14:00',
                'sunday': 'closed'
            },
        }
        
        data = self.apply_default_values(kwargs)
        for key, value in food_defaults.items():
            if key not in kwargs:
                data[key] = value
        
        # Add food-specific tags
        food_tags = ['food', 'nutrition', 'meals', 'groceries']
        existing_tags = data.get('tags', [])
        data['tags'] = list(set(existing_tags + food_tags))
        
        return Service.objects.create(**data)
    
    def get_service_type(self) -> str:
        return "food"


class EmergencyServiceFactory(ServiceFactory):
    """Factory for creating emergency services."""
    
    def create_service(self, **kwargs) -> Service:
        """Create an emergency service with emergency-specific defaults."""
        self.validate_required_fields(kwargs)
        self.validate_location(kwargs['location'])
        
        # Emergency service defaults
        emergency_defaults = {
            'is_24_7': True,
            'accepts_walk_ins': True,
            'is_emergency_service': True,
            'requires_appointment': False,
            'current_status': ServiceStatus.OPEN,
            'is_verified': True,  # Emergency services should be pre-verified
        }
        
        data = self.apply_default_values(kwargs)
        for key, value in emergency_defaults.items():
            if key not in kwargs:
                data[key] = value
        
        # Emergency services must be active and emergency-eligible
        data['is_active'] = True
        data['is_emergency_service'] = True
        
        # Add emergency-specific tags
        emergency_tags = ['emergency', 'urgent', '24/7', 'immediate']
        existing_tags = data.get('tags', [])
        data['tags'] = list(set(existing_tags + emergency_tags))
        
        return Service.objects.create(**data)
    
    def get_service_type(self) -> str:
        return "emergency"


class GeneralServiceFactory(ServiceFactory):
    """Factory for creating general/other types of services."""
    
    def create_service(self, **kwargs) -> Service:
        """Create a general service with standard defaults."""
        self.validate_required_fields(kwargs)
        self.validate_location(kwargs['location'])
        
        data = self.apply_default_values(kwargs)
        return Service.objects.create(**data)
    
    def get_service_type(self) -> str:
        return "general"


class ServiceFactoryRegistry:
    """
    Registry for service factories implementing Factory Method pattern.
    
    Manages different factory types and provides factory selection
    based on service category or explicit type.
    """
    
    _factories = {
        'healthcare': HealthcareServiceFactory,
        'shelter': ShelterServiceFactory,
        'food': FoodServiceFactory,
        'emergency': EmergencyServiceFactory,
        'general': GeneralServiceFactory,
    }
    
    # Map category types to factory types
    _category_mapping = {
        'healthcare': 'healthcare',
        'shelter': 'shelter',
        'food': 'food',
        'emergency': 'emergency',
        'social': 'general',
        'education': 'general',
        'employment': 'general',
        'legal': 'general',
        'transportation': 'general',
        'utilities': 'general',
        'recreation': 'general',
        'other': 'general',
    }
    
    @classmethod
    def get_factory(cls, factory_type: str = None, category: ServiceCategory = None) -> ServiceFactory:
        """
        Get appropriate factory for service creation.
        
        Args:
            factory_type: Explicit factory type name
            category: ServiceCategory instance to infer factory type
            
        Returns:
            ServiceFactory instance
            
        Raises:
            ValueError: If factory type is not found
        """
        # Determine factory type
        if factory_type:
            selected_type = factory_type
        elif category and hasattr(category, 'category_type'):
            selected_type = cls._category_mapping.get(category.category_type, 'general')
        else:
            selected_type = 'general'
        
        # Get factory class
        if selected_type not in cls._factories:
            available = ', '.join(cls._factories.keys())
            raise ValueError(f"Unknown factory type '{selected_type}'. Available: {available}")
        
        factory_class = cls._factories[selected_type]
        return factory_class()
    
    @classmethod
    def create_service(cls, factory_type: str = None, **kwargs) -> Service:
        """
        Convenience method to create a service using appropriate factory.
        
        Args:
            factory_type: Explicit factory type (optional)
            **kwargs: Service creation parameters
            
        Returns:
            Created Service instance
        """
        category = kwargs.get('category')
        factory = cls.get_factory(factory_type, category)
        return factory.create_service(**kwargs)
    
    @classmethod
    def register_factory(cls, factory_type: str, factory_class: Type[ServiceFactory]) -> None:
        """Register a new service factory type."""
        if not issubclass(factory_class, ServiceFactory):
            raise ValueError("Factory class must inherit from ServiceFactory")
        
        cls._factories[factory_type] = factory_class
    
    @classmethod
    def get_available_types(cls) -> List[str]:
        """Get list of available factory types."""
        return list(cls._factories.keys())


class AlertFactory:
    """
    Factory for creating service alerts with type-specific defaults.
    
    Provides consistent alert creation with appropriate settings
    based on alert type and urgency.
    """
    
    ALERT_DEFAULTS = {
        'info': {
            'priority': 1,
            'show_on_map': True,
            'requires_acknowledgment': False,
        },
        'warning': {
            'priority': 3,
            'show_on_map': True,
            'requires_acknowledgment': False,
        },
        'urgent': {
            'priority': 4,
            'show_on_map': True,
            'requires_acknowledgment': True,
        },
        'closure': {
            'priority': 5,
            'show_on_map': True,
            'requires_acknowledgment': True,
        },
        'capacity': {
            'priority': 2,
            'show_on_map': True,
            'requires_acknowledgment': False,
        },
        'schedule': {
            'priority': 2,
            'show_on_map': False,
            'requires_acknowledgment': False,
        },
    }
    
    @classmethod
    def create_alert(cls, service: Service, alert_type: str, title: str, 
                    message: str, created_by: User = None, **kwargs) -> ServiceAlert:
        """
        Create a service alert with type-specific defaults.
        
        Args:
            service: Service this alert relates to
            alert_type: Type of alert (info, warning, urgent, etc.)
            title: Alert title
            message: Alert message content
            created_by: User creating the alert
            **kwargs: Additional alert parameters
            
        Returns:
            Created ServiceAlert instance
        """
        # Validate alert type
        valid_types = [choice[0] for choice in ServiceAlert.ALERT_TYPES]
        if alert_type not in valid_types:
            raise ValueError(f"Invalid alert type '{alert_type}'. Valid types: {valid_types}")
        
        # Apply type-specific defaults
        defaults = cls.ALERT_DEFAULTS.get(alert_type, cls.ALERT_DEFAULTS['info'])
        
        # Prepare alert data
        alert_data = {
            'service': service,
            'alert_type': alert_type,
            'title': title,
            'message': message,
            'created_by': created_by,
            'is_active': True,
            'start_time': timezone.now(),
        }
        
        # Apply defaults for missing keys
        for key, default_value in defaults.items():
            if key not in kwargs:
                alert_data[key] = default_value
        
        # Override with any explicit values
        alert_data.update(kwargs)
        
        return ServiceAlert.objects.create(**alert_data)
    
    @classmethod
    def create_capacity_alert(cls, service: Service, created_by: User = None) -> ServiceAlert:
        """Create a capacity-related alert for a service."""
        if service.is_at_capacity:
            title = f"{service.name} is at full capacity"
            message = f"This service is currently at full capacity ({service.current_capacity}/{service.max_capacity}). Please check back later or consider alternative services."
        elif service.is_near_capacity:
            title = f"{service.name} is nearly full"
            message = f"This service is nearly at capacity ({service.current_capacity}/{service.max_capacity}). Contact them before visiting."
        else:
            title = f"{service.name} has availability"
            message = f"This service currently has availability ({service.current_capacity}/{service.max_capacity})."
        
        return cls.create_alert(
            service=service,
            alert_type='capacity',
            title=title,
            message=message,
            created_by=created_by,
            priority=2 if service.is_at_capacity else 1
        )
    
    @classmethod
    def create_closure_alert(cls, service: Service, reason: str, 
                           end_time: timezone.datetime = None, 
                           created_by: User = None) -> ServiceAlert:
        """Create a temporary closure alert."""
        title = f"{service.name} temporarily closed"
        message = f"This service is temporarily closed. Reason: {reason}"
        
        if end_time:
            message += f" Expected to reopen: {end_time.strftime('%Y-%m-%d %H:%M')}"
        
        return cls.create_alert(
            service=service,
            alert_type='closure',
            title=title,
            message=message,
            created_by=created_by,
            end_time=end_time,
            priority=5
        )
    
    @classmethod
    def create_emergency_alert(cls, service: Service, emergency_message: str,
                             created_by: User = None) -> ServiceAlert:
        """Create an emergency alert for a service."""
        title = f"EMERGENCY: {service.name}"
        
        return cls.create_alert(
            service=service,
            alert_type='urgent',
            title=title,
            message=emergency_message,
            created_by=created_by,
            priority=5,
            requires_acknowledgment=True
        )


class StatusUpdateFactory:
    """
    Factory for creating real-time status updates.
    
    Provides consistent status update creation with proper
    change tracking and metadata.
    """
    
    @classmethod
    def create_status_update(cls, service: Service, change_type: str,
                           updated_by: User = None, message: str = '',
                           **kwargs) -> RealTimeStatusUpdate:
        """
        Create a status update for a service.
        
        Args:
            service: Service being updated
            change_type: Type of change (status, capacity, etc.)
            updated_by: User making the update
            message: Optional update message
            **kwargs: Additional update data
            
        Returns:
            Created RealTimeStatusUpdate instance
        """
        # Validate change type
        valid_types = [choice[0] for choice in RealTimeStatusUpdate.CHANGE_TYPES]
        if change_type not in valid_types:
            raise ValueError(f"Invalid change type '{change_type}'. Valid types: {valid_types}")
        
        update_data = {
            'service': service,
            'change_type': change_type,
            'updated_by': updated_by,
            'message': message,
            'notifications_sent': False,
            'notification_count': 0,
            'metadata': {},
        }
        
        # Add change-specific data
        update_data.update(kwargs)
        
        return RealTimeStatusUpdate.objects.create(**update_data)
    
    @classmethod
    def create_capacity_update(cls, service: Service, old_capacity: int,
                             new_capacity: int, updated_by: User = None) -> RealTimeStatusUpdate:
        """Create a capacity change update."""
        return cls.create_status_update(
            service=service,
            change_type='capacity',
            old_capacity=old_capacity,
            new_capacity=new_capacity,
            updated_by=updated_by,
            message=f"Capacity updated from {old_capacity} to {new_capacity}",
            metadata={
                'capacity_change': new_capacity - old_capacity,
                'capacity_percentage': service.capacity_percentage,
            }
        )
    
    @classmethod
    def create_status_change_update(cls, service: Service, old_status: str,
                                  new_status: str, updated_by: User = None) -> RealTimeStatusUpdate:
        """Create a status change update."""
        return cls.create_status_update(
            service=service,
            change_type='status',
            old_status=old_status,
            new_status=new_status,
            updated_by=updated_by,
            message=f"Status changed from {old_status} to {new_status}",
            metadata={
                'status_change_reason': 'manual_update',
            }
        ) 