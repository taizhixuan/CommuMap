from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from typing import Type, Any

from apps.core.models import User, UserRole
from .models import UserProfile, UserNotification


@receiver(post_save, sender=User)
def create_user_profile(sender: Type[User], instance: User, created: bool, **kwargs: Any) -> None:
    """
    Create a UserProfile when a new User is created.
    
    This signal handler ensures that every User has an associated UserProfile
    with default settings appropriate for their role.
    
    Args:
        sender: The User model class
        instance: The User instance that was saved
        created: Whether this is a new instance
        **kwargs: Additional keyword arguments
    """
    if created:
        # Create the profile with role-appropriate defaults
        profile_defaults = {
            'search_radius_km': 10,
            'email_notifications': True,
            'emergency_alerts': True,
            'service_updates': False,
            'public_profile': False,
            'share_location': False,
        }
        
        # Adjust defaults based on user role
        if instance.role == UserRole.SERVICE_MANAGER:
            profile_defaults.update({
                'service_updates': True,
                'public_profile': True,
            })
        elif instance.role == UserRole.COMMUNITY_MODERATOR:
            profile_defaults.update({
                'service_updates': True,
                'public_profile': True,
                'email_notifications': True,
            })
        elif instance.role == UserRole.ADMIN:
            profile_defaults.update({
                'service_updates': True,
                'public_profile': True,
                'email_notifications': True,
                'emergency_alerts': True,
            })
        
        UserProfile.objects.create(user=instance, **profile_defaults)
        
        # Send welcome notification
        welcome_message = _get_welcome_message(instance.role)
        UserNotification.objects.create(
            user=instance,
            notification_type='welcome',
            title=_('Welcome to CommuMap!'),
            message=welcome_message,
            priority='normal'
        )


@receiver(post_save, sender=User)
def save_user_profile(sender: Type[User], instance: User, **kwargs: Any) -> None:
    """
    Save the UserProfile when the User is saved.
    
    This ensures the profile is always saved when the user is updated,
    maintaining data consistency.
    
    Args:
        sender: The User model class
        instance: The User instance that was saved
        **kwargs: Additional keyword arguments
    """
    if hasattr(instance, 'profile'):
        instance.profile.save()


def _get_welcome_message(role: str) -> str:
    """
    Get a role-specific welcome message.
    
    Args:
        role: The user's role
        
    Returns:
        Welcome message string
    """
    messages = {
        UserRole.USER: _(
            "Welcome to CommuMap! You can now search for community services, "
            "bookmark your favorites, and stay updated on service availability. "
            "Start by exploring services in your area."
        ),
        UserRole.SERVICE_MANAGER: _(
            "Welcome to CommuMap! As a Service Manager, you can create and manage "
            "service listings, update availability, and engage with the community. "
            "Visit your dashboard to get started."
        ),
        UserRole.COMMUNITY_MODERATOR: _(
            "Welcome to CommuMap! As a Community Moderator, you help maintain "
            "service quality and assist with community engagement. "
            "Check the moderation panel for pending reviews."
        ),
        UserRole.ADMIN: _(
            "Welcome to CommuMap! As an Administrator, you have full system access "
            "to manage users, services, and system settings. "
            "Visit the admin console to begin."
        ),
    }
    
    return messages.get(role, messages[UserRole.USER]) 