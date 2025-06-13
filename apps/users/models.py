from django.db import models
# from django.contrib.gis.db import models as gis_models  # Commented out for now
# from django.contrib.gis.geos import Point  # Commented out for now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from typing import Dict, Any, Optional, List
import uuid
from django.utils import timezone

from apps.core.models import User, TimestampedMixin  # Fixed import name


class UserProfile(TimestampedMixin):
    """
    Extended user profile with geographic preferences and community settings.
    
    This model extends the base User model with additional fields for
    geographic preferences, accessibility needs, and community participation.
    """
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name=_('User')
    )
    
    # Geographic preferences - using lat/lng instead of PointField for now
    preferred_location_lat = models.FloatField(
        null=True,
        blank=True,
        help_text=_('User\'s preferred location latitude'),
        verbose_name=_('Preferred Location Latitude')
    )
    preferred_location_lng = models.FloatField(
        null=True,
        blank=True,
        help_text=_('User\'s preferred location longitude'),
        verbose_name=_('Preferred Location Longitude')
    )
    
    search_radius_km = models.PositiveIntegerField(
        default=10,
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        help_text=_('Default search radius in kilometers'),
        verbose_name=_('Search Radius (km)')
    )
    
    # Accessibility preferences
    requires_wheelchair_access = models.BooleanField(
        default=False,
        verbose_name=_('Requires Wheelchair Access')
    )
    
    requires_sign_language = models.BooleanField(
        default=False,
        verbose_name=_('Requires Sign Language Support')
    )
    
    preferred_languages = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of preferred language codes'),
        verbose_name=_('Preferred Languages')
    )
    
    # Communication preferences
    email_notifications = models.BooleanField(
        default=True,
        verbose_name=_('Email Notifications')
    )
    
    emergency_alerts = models.BooleanField(
        default=True,
        verbose_name=_('Emergency Alerts')
    )
    
    service_updates = models.BooleanField(
        default=False,
        verbose_name=_('Service Updates')
    )
    
    # Privacy settings
    public_profile = models.BooleanField(
        default=False,
        verbose_name=_('Public Profile')
    )
    
    share_location = models.BooleanField(
        default=False,
        verbose_name=_('Share Location')
    )
    
    # Additional metadata
    bio = models.TextField(
        max_length=500,
        blank=True,
        verbose_name=_('Bio')
    )
    
    # avatar = models.ImageField(
    #     upload_to='avatars/',
    #     null=True,
    #     blank=True,
    #     verbose_name=_('Avatar')
    # )
    
    class Meta:
        verbose_name = _('User Profile')
        verbose_name_plural = _('User Profiles')
        db_table = 'users_profile'
    
    def __str__(self) -> str:
        return f"{self.user.get_full_name()} Profile"
    
    def get_preferred_location_display(self) -> Optional[str]:
        """
        Get a human-readable display of the preferred location.
        
        Returns:
            String representation of the location or None
        """
        if self.preferred_location_lat and self.preferred_location_lng:
            return f"({self.preferred_location_lat:.4f}, {self.preferred_location_lng:.4f})"
        return None
    
    def get_accessibility_needs(self) -> List[str]:
        """
        Get a list of accessibility needs for this user.
        
        Returns:
            List of accessibility requirement strings
        """
        needs = []
        if self.requires_wheelchair_access:
            needs.append("Wheelchair Access")
        if self.requires_sign_language:
            needs.append("Sign Language Support")
        return needs


class ServiceBookmark(TimestampedMixin):
    """
    User bookmarks for saving favorite services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='bookmarks',
        help_text=_('User who bookmarked the service')
    )
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='bookmarked_by',
        help_text=_('Bookmarked service')
    )
    
    # Optional organization
    folder_name = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Optional folder name for organizing bookmarks')
    )
    notes = models.TextField(
        blank=True,
        help_text=_('Personal notes about this service')
    )
    
    # Usage tracking
    last_accessed = models.DateTimeField(
        default=timezone.now,
        help_text=_('When bookmark was last accessed')
    )
    access_count = models.PositiveIntegerField(
        default=1,
        help_text=_('Number of times bookmark was accessed')
    )
    
    class Meta:
        verbose_name = _('Service Bookmark')
        verbose_name_plural = _('Service Bookmarks')
        unique_together = ['user', 'service']  # One bookmark per user per service
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['user', 'folder_name']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_display_name()}: {self.service.name}"
    
    def mark_accessed(self) -> None:
        """Update access tracking when bookmark is used."""
        self.last_accessed = timezone.now()
        self.access_count += 1
        self.save(update_fields=['last_accessed', 'access_count'])


class SearchHistory(TimestampedMixin):
    """
    Track user search patterns for analytics and recommendations.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='search_history',
        help_text=_('User who performed the search (null for anonymous)')
    )
    
    # Search parameters
    query = models.CharField(
        max_length=500,
        blank=True,
        help_text=_('Search query text')
    )
    search_location = models.CharField(
        max_length=200,
        blank=True,
        help_text=_('Search location (stored as string for now)')
    )
    search_radius_km = models.FloatField(
        blank=True,
        null=True,
        help_text=_('Search radius in kilometers')
    )
    category_filter = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Category filter applied')
    )
    
    # Search results
    results_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of results returned')
    )
    
    # Session tracking
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Session identifier for anonymous users')
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=_('IP address of the search request')
    )
    
    # Additional metadata
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )
    referrer = models.URLField(
        blank=True,
        help_text=_('Page that referred to search')
    )
    
    class Meta:
        verbose_name = _('Search History')
        verbose_name_plural = _('Search Histories')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['session_id', '-created_at']),
            models.Index(fields=['query', '-created_at']),
        ]
    
    def __str__(self) -> str:
        user_str = self.user.get_display_name() if self.user else f"Anonymous ({self.session_id})"
        return f"{user_str}: '{self.query}' ({self.results_count} results)"


class UserNotification(TimestampedMixin):
    """
    User notifications for service updates and system messages.
    
    Handles various types of notifications including service updates,
    emergency alerts, and system announcements.
    """
    
    NOTIFICATION_TYPES = [
        ('service_update', _('Service Update')),
        ('emergency_alert', _('Emergency Alert')),
        ('bookmark_update', _('Bookmark Update')),
        ('system_announcement', _('System Announcement')),
        ('welcome', _('Welcome Message')),
        ('reminder', _('Reminder')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name=_('User')
    )
    
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='system_announcement',
        verbose_name=_('Notification Type')
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name=_('Title')
    )
    
    message = models.TextField(
        verbose_name=_('Message')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        verbose_name=_('Priority')
    )
    
    is_read = models.BooleanField(
        default=False,
        verbose_name=_('Is Read')
    )
    
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name=_('Read At')
    )
    
    related_service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='user_notifications',
        verbose_name=_('Related Service')
    )
    
    action_url = models.URLField(
        blank=True,
        help_text=_('URL for notification action'),
        verbose_name=_('Action URL')
    )
    
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When this notification expires'),
        verbose_name=_('Expires At')
    )
    
    class Meta:
        verbose_name = _('User Notification')
        verbose_name_plural = _('User Notifications')
        db_table = 'users_notification'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'is_read', '-created_at']),
            models.Index(fields=['notification_type', '-created_at']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_full_name()} - {self.title}"
    
    def mark_as_read(self) -> None:
        """Mark this notification as read."""
        from django.utils import timezone
        
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    def is_expired(self) -> bool:
        """Check if this notification has expired."""
        if self.expires_at:
            from django.utils import timezone
            return timezone.now() > self.expires_at
        return False


class UserPreferences(TimestampedMixin):
    """
    User preferences and settings.
    """
    THEME_CHOICES = [
        ('light', _('Light')),
        ('dark', _('Dark')),
        ('auto', _('Auto')),
    ]
    
    LANGUAGE_CHOICES = [
        ('en', _('English')),
        ('es', _('Spanish')),
        ('fr', _('French')),
        ('zh', _('Chinese')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='preferences',
        help_text=_('User these preferences belong to')
    )
    
    # Display preferences
    theme = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='light',
        help_text=_('UI theme preference')
    )
    language = models.CharField(
        max_length=5,
        choices=LANGUAGE_CHOICES,
        default='en',
        help_text=_('Preferred language')
    )
    
    # Map preferences
    default_map_zoom = models.PositiveIntegerField(
        default=12,
        help_text=_('Default map zoom level')
    )
    show_user_location = models.BooleanField(
        default=True,
        help_text=_('Show user location on map')
    )
    
    # Search preferences
    default_search_radius_km = models.PositiveIntegerField(
        default=10,
        help_text=_('Default search radius in kilometers')
    )
    preferred_categories = models.JSONField(
        default=list,
        blank=True,
        help_text=_('List of preferred service categories')
    )
    
    # Notification preferences
    email_notifications = models.BooleanField(
        default=True,
        help_text=_('Receive email notifications')
    )
    sms_notifications = models.BooleanField(
        default=False,
        help_text=_('Receive SMS notifications')
    )
    emergency_alerts = models.BooleanField(
        default=True,
        help_text=_('Receive emergency service alerts')
    )
    service_updates = models.BooleanField(
        default=True,
        help_text=_('Receive updates about bookmarked services')
    )
    
    # Privacy preferences
    profile_public = models.BooleanField(
        default=False,
        help_text=_('Make profile visible to other users')
    )
    reviews_anonymous = models.BooleanField(
        default=False,
        help_text=_('Post reviews anonymously by default')
    )
    location_sharing = models.BooleanField(
        default=True,
        help_text=_('Allow location-based recommendations')
    )
    
    class Meta:
        verbose_name = _('User Preferences')
        verbose_name_plural = _('User Preferences')
    
    def __str__(self) -> str:
        return f"Preferences for {self.user.get_display_name()}"


class UserActivity(TimestampedMixin):
    """
    Track user activity for analytics and recommendations.
    """
    ACTIVITY_TYPES = [
        ('view_service', _('Viewed Service')),
        ('bookmark_service', _('Bookmarked Service')),
        ('remove_bookmark', _('Removed Bookmark')),
        ('write_review', _('Wrote Review')),
        ('write_comment', _('Wrote Comment')),
        ('search', _('Performed Search')),
        ('emergency_search', _('Emergency Search')),
        ('profile_update', _('Updated Profile')),
        ('login', _('Logged In')),
        ('logout', _('Logged Out')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        help_text=_('User who performed the activity')
    )
    
    activity_type = models.CharField(
        max_length=20,
        choices=ACTIVITY_TYPES,
        help_text=_('Type of activity performed')
    )
    
    # Related objects (optional)
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='user_activities',
        help_text=_('Service related to this activity')
    )
    
    # Additional data
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional activity metadata')
    )
    
    # Session tracking
    session_id = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Session identifier')
    )
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=_('IP address')
    )
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )
    
    class Meta:
        verbose_name = _('User Activity')
        verbose_name_plural = _('User Activities')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['activity_type', '-created_at']),
            models.Index(fields=['service', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_display_name()}: {self.get_activity_type_display()}" 