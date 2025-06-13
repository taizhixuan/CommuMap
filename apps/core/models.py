"""
Core models for CommuMap including custom User model and common mixins.

This module implements the Singleton pattern for system-wide managers
and provides base models following SOLID principles.
"""
from typing import Optional, List
import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models  # Using regular models instead of GIS for now
# from django.contrib.gis.geos import Point  # Commented out for now
from django.core.validators import EmailValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


class UserRole(models.TextChoices):
    """
    User roles in CommuMap system.
    
    Implements role-based access control for the four main actors:
    - User: General public users who search and bookmark services
    - Service Manager: Manages specific service listings and real-time status
    - Community Moderator: Verifies services and moderates content
    - Admin: System-wide administration and user management
    """
    USER = 'user', _('User')
    SERVICE_MANAGER = 'service_manager', _('Service Manager')
    COMMUNITY_MODERATOR = 'community_moderator', _('Community Moderator')
    ADMIN = 'admin', _('Admin')


class TimestampedMixin(models.Model):
    """
    Abstract base model providing timestamp functionality.
    
    Follows the Single Responsibility Principle by handling only
    timestamp-related concerns.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True


class User(AbstractUser):
    """
    Custom User model with role-based permissions and verification fields.
    
    Extends Django's AbstractUser to support CommuMap's role-based
    access control system and user preferences with additional
    verification fields for Service Managers and Community Moderators.
    """
    # Remove username field, use email as identifier
    username = None
    
    # Core fields
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(
        _('email address'),
        unique=True,
        validators=[EmailValidator()],
        help_text=_('Required. Enter a valid email address.')
    )
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.USER,
        help_text=_('User role determines access permissions.')
    )
    
    # Profile information
    full_name = models.CharField(
        max_length=150,
        blank=True,
        help_text=_('Full name for display purposes.')
    )
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Contact phone number.')
    )
    # avatar = models.ImageField(
    #     upload_to='avatars/',
    #     blank=True,
    #     null=True,
    #     help_text=_('Profile picture.')
    # )
    
    # Service Manager verification fields
    service_name = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Name of the service or organization (Service Managers only).')
    )
    official_email = models.EmailField(
        blank=True,
        help_text=_('Official work email for verification (Service Managers only).')
    )
    contact_number = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Official contact number (Service Managers only).')
    )
    
    # Community Moderator verification fields
    community_experience = models.TextField(
        blank=True,
        help_text=_('Community management or moderation experience (Community Moderators only).')
    )
    relevant_community = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Relevant community or organization (Community Moderators only).')
    )
    
    # Common verification fields
    organization = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Organization name (Service Managers and Community Moderators).')
    )
    
    # Geographic preferences - using lat/lng instead of PointField for now
    preferred_location_lat = models.FloatField(
        blank=True,
        null=True,
        help_text=_('User\'s preferred location latitude.')
    )
    preferred_location_lng = models.FloatField(
        blank=True,
        null=True,
        help_text=_('User\'s preferred location longitude.')
    )
    search_radius_km = models.PositiveIntegerField(
        default=10,
        help_text=_('Default search radius in kilometers.')
    )
    
    # Account status
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Whether the user account has been verified.')
    )
    verification_requested_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When verification was requested for service managers/moderators.')
    )
    verified_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='verified_users',
        help_text=_('Admin who verified this user.')
    )
    verification_notes = models.TextField(
        blank=True,
        help_text=_('Admin notes regarding verification decision.')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_active = models.DateTimeField(default=timezone.now)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']
    
    class Meta:
        verbose_name = _('User')
        verbose_name_plural = _('Users')
        indexes = [
            models.Index(fields=['role', 'is_verified']),
            models.Index(fields=['email']),
            models.Index(fields=['last_active']),
            models.Index(fields=['verification_requested_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.email} ({self.get_role_display()})"
    
    def get_absolute_url(self) -> str:
        """Return URL for user profile based on role."""
        if self.role == UserRole.USER:
            return reverse('users:profile')
        elif self.role == UserRole.SERVICE_MANAGER:
            return reverse('manager:profile')
        elif self.role == UserRole.COMMUNITY_MODERATOR:
            return reverse('moderators:profile')
        elif self.role == UserRole.ADMIN:
            # Use manager profile temporarily until admin console is created
            return reverse('manager:profile')
        return reverse('core:landing')
    
    def get_display_name(self) -> str:
        """Return the best available display name for the user."""
        if self.full_name:
            return self.full_name
        elif self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        else:
            return self.email.split('@')[0]
    
    @property
    def requires_verification(self) -> bool:
        """Check if user role requires admin verification."""
        return self.role in [UserRole.SERVICE_MANAGER, UserRole.COMMUNITY_MODERATOR]
    
    @property
    def can_manage_services(self) -> bool:
        """Check if user can manage services."""
        return self.role in [UserRole.SERVICE_MANAGER, UserRole.ADMIN] and self.is_verified
    
    @property
    def can_moderate_content(self) -> bool:
        """Check if user can moderate content."""
        return self.role in [UserRole.COMMUNITY_MODERATOR, UserRole.ADMIN] and self.is_verified
    
    @property
    def is_admin_user(self) -> bool:
        """Check if user has admin privileges."""
        return self.role == UserRole.ADMIN and self.is_verified
    
    @property
    def verification_data(self) -> dict:
        """Get verification-specific data based on role."""
        if self.role == UserRole.SERVICE_MANAGER:
            return {
                'service_name': self.service_name,
                'official_email': self.official_email,
                'contact_number': self.contact_number,
                'organization': self.organization,
            }
        elif self.role == UserRole.COMMUNITY_MODERATOR:
            return {
                'community_experience': self.community_experience,
                'relevant_community': self.relevant_community,
                'organization': self.organization,
            }
        return {}
    
    def request_verification(self) -> None:
        """Request account verification for service managers and moderators."""
        if self.requires_verification and not self.is_verified:
            self.verification_requested_at = timezone.now()
            self.save(update_fields=['verification_requested_at'])
    
    def verify_user(self, verified_by_user: 'User', notes: str = '') -> None:
        """Verify the user account (admin only)."""
        if verified_by_user.is_admin_user:
            self.is_verified = True
            self.verified_by = verified_by_user
            self.verification_notes = notes
            self.save(update_fields=['is_verified', 'verified_by', 'verification_notes'])
    
    def reject_verification(self, rejected_by_user: 'User', notes: str = '') -> None:
        """Reject verification request (admin only)."""
        if rejected_by_user.is_admin_user:
            self.is_verified = False
            self.verified_by = rejected_by_user
            self.verification_notes = notes
            self.verification_requested_at = None
            self.save(update_fields=['is_verified', 'verified_by', 'verification_notes', 'verification_requested_at'])


class SystemSettings(models.Model):
    """
    System-wide settings model implementing the Singleton pattern.
    
    Stores global configuration that can be modified at runtime
    without requiring code changes.
    """
    # Singleton instance tracking
    _instance = None
    
    # System status
    maintenance_mode = models.BooleanField(
        default=False,
        help_text=_('Enable maintenance mode to restrict access.')
    )
    system_announcement = models.TextField(
        blank=True,
        help_text=_('System-wide announcement displayed to all users.')
    )
    announcement_active = models.BooleanField(
        default=False,
        help_text=_('Whether to display the system announcement.')
    )
    
    # Feature toggles
    registration_enabled = models.BooleanField(
        default=True,
        help_text=_('Allow new user registrations.')
    )
    service_submissions_enabled = models.BooleanField(
        default=True,
        help_text=_('Allow new service submissions.')
    )
    emergency_mode = models.BooleanField(
        default=False,
        help_text=_('Emergency mode - prioritize emergency services.')
    )
    
    # Map configuration
    default_map_center_lat = models.FloatField(
        default=40.7128,
        help_text=_('Default map center latitude.')
    )
    default_map_center_lng = models.FloatField(
        default=-74.0060,
        help_text=_('Default map center longitude.')
    )
    default_map_zoom = models.PositiveIntegerField(
        default=12,
        help_text=_('Default map zoom level.')
    )
    emergency_search_radius_km = models.PositiveIntegerField(
        default=5,
        help_text=_('Default emergency search radius in kilometers.')
    )
    
    # Content moderation
    auto_approve_services = models.BooleanField(
        default=False,
        help_text=_('Automatically approve new service submissions.')
    )
    auto_approve_comments = models.BooleanField(
        default=False,
        help_text=_('Automatically approve new comments.')
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('System Settings')
        verbose_name_plural = _('System Settings')
    
    def __str__(self) -> str:
        return f"System Settings (Updated: {self.updated_at})"
    
    @classmethod
    def get_instance(cls) -> 'SystemSettings':
        """
        Get the singleton instance of system settings.
        
        Implements the Singleton pattern to ensure only one
        SystemSettings instance exists.
        """
        if cls._instance is None:
            cls._instance, created = cls.objects.get_or_create(pk=1)
        return cls._instance
    
    def save(self, *args, **kwargs):
        """Override save to maintain singleton pattern."""
        self.pk = 1
        super().save(*args, **kwargs)
        self.__class__._instance = self
    
    def delete(self, *args, **kwargs):
        """Prevent deletion of singleton instance."""
        pass


class AuditLog(TimestampedMixin):
    """
    Audit log for tracking important system actions.
    
    Provides accountability and traceability for administrative
    actions and user activities.
    """
    ACTION_CHOICES = [
        ('user_created', _('User Created')),
        ('user_verified', _('User Verified')),
        ('user_role_changed', _('User Role Changed')),
        ('service_created', _('Service Created')),
        ('service_updated', _('Service Updated')),
        ('service_approved', _('Service Approved')),
        ('service_rejected', _('Service Rejected')),
        ('emergency_toggled', _('Emergency Status Toggled')),
        ('system_settings_changed', _('System Settings Changed')),
        ('maintenance_mode_toggled', _('Maintenance Mode Toggled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_logs',
        help_text=_('User who performed the action.')
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text=_('Type of action performed.')
    )
    description = models.TextField(
        help_text=_('Detailed description of the action.')
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=_('IP address from which the action was performed.')
    )
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string from the browser.')
    )
    
    # Additional context data (JSON)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional context data about the action.')
    )
    
    class Meta:
        verbose_name = _('Audit Log')
        verbose_name_plural = _('Audit Logs')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['action', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.get_action_display()} by {self.user} at {self.created_at}" 