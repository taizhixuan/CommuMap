"""
Service models for CommuMap implementing design patterns.

This module contains the core service discovery models with PostGIS integration,
implementing Factory Method for service creation and Observer pattern for
real-time status notifications.
"""
from typing import Optional, List, Dict, Any, Tuple
import uuid
from decimal import Decimal
from django.db import models  # Using regular models instead of GIS for now
# from django.contrib.gis.geos import Point  # Commented out for now
# from django.contrib.gis.measure import Distance  # Commented out for now
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.utils.text import slugify
from slugify import slugify as python_slugify

from apps.core.models import TimestampedMixin, User


class ServiceCategory(TimestampedMixin):
    """
    Service categories for organizing different types of community services.
    
    Categories help users filter and discover relevant services more easily.
    """
    CATEGORY_TYPES = [
        ('healthcare', _('Healthcare & Medical')),
        ('shelter', _('Shelter & Housing')),
        ('food', _('Food & Nutrition')),
        ('education', _('Education & Learning')),
        ('emergency', _('Emergency Services')),
        ('social', _('Social Services')),
        ('employment', _('Employment & Training')),
        ('legal', _('Legal Aid')),
        ('transportation', _('Transportation')),
        ('utilities', _('Utilities & Basic Needs')),
        ('recreation', _('Recreation & Community')),
        ('other', _('Other Services')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text=_('Category name')
    )
    slug = models.SlugField(
        max_length=100,
        unique=True,
        help_text=_('URL-friendly category identifier')
    )
    category_type = models.CharField(
        max_length=20,
        choices=CATEGORY_TYPES,
        help_text=_('Primary category type')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Category description')
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text=_('Icon class for UI display')
    )
    color = models.CharField(
        max_length=7,
        default='#3B82F6',
        help_text=_('Hex color code for category')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this category is available for use')
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text=_('Display order (lower numbers first)')
    )
    
    class Meta:
        verbose_name = _('Service Category')
        verbose_name_plural = _('Service Categories')
        ordering = ['sort_order', 'name']
        indexes = [
            models.Index(fields=['category_type', 'is_active']),
            models.Index(fields=['sort_order']),
        ]
    
    def __str__(self) -> str:
        return self.name
    
    def save(self, *args, **kwargs):
        """Auto-generate slug from name."""
        if not self.slug:
            self.slug = python_slugify(self.name)
        super().save(*args, **kwargs)
    
    def get_absolute_url(self) -> str:
        return reverse('services:category', kwargs={'slug': self.slug})


class ServiceStatus(models.TextChoices):
    """Service operational status choices."""
    OPEN = 'open', _('Open')
    CLOSED = 'closed', _('Closed')
    TEMPORARILY_CLOSED = 'temp_closed', _('Temporarily Closed')
    FULL = 'full', _('At Capacity')
    LIMITED = 'limited', _('Limited Availability')
    EMERGENCY_ONLY = 'emergency', _('Emergency Only')


class Service(TimestampedMixin):
    """
    Core service model with PostGIS location support.
    
    Represents community services with geographic data, real-time status,
    and comprehensive metadata for discovery and filtering.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    name = models.CharField(
        max_length=200,
        help_text=_('Service name')
    )
    slug = models.SlugField(
        max_length=250,
        unique=True,
        help_text=_('URL-friendly service identifier')
    )
    description = models.TextField(
        help_text=_('Detailed service description')
    )
    short_description = models.CharField(
        max_length=300,
        help_text=_('Brief service summary for listings')
    )
    
    # Categorization
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name='services',
        help_text=_('Primary service category')
    )
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Additional searchable tags')
    )
    
    # Geographic data - using lat/lng instead of PointField for now
    latitude = models.FloatField(
        help_text=_('Service location latitude')
    )
    longitude = models.FloatField(
        help_text=_('Service location longitude')
    )
    address = models.CharField(
        max_length=300,
        help_text=_('Physical address')
    )
    postal_code = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Postal/ZIP code')
    )
    city = models.CharField(
        max_length=100,
        help_text=_('City name')
    )
    state_province = models.CharField(
        max_length=100,
        help_text=_('State or province')
    )
    country = models.CharField(
        max_length=100,
        default='Malaysia',
        help_text=_('Country name')
    )
    
    # Contact information
    phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Primary phone number')
    )
    phone_alt = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Alternative phone number')
    )
    email = models.EmailField(
        blank=True,
        help_text=_('Contact email address')
    )
    website = models.URLField(
        blank=True,
        help_text=_('Official website URL')
    )
    
    # Operating information
    hours_of_operation = models.JSONField(
        default=dict,
        help_text=_('Weekly operating hours by day')
    )
    is_24_7 = models.BooleanField(
        default=False,
        help_text=_('Open 24 hours, 7 days a week')
    )
    seasonal_info = models.TextField(
        blank=True,
        help_text=_('Seasonal operation details')
    )
    
    # Capacity and status
    max_capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=_('Maximum service capacity')
    )
    current_capacity = models.PositiveIntegerField(
        default=0,
        help_text=_('Current occupancy/usage')
    )
    capacity_last_updated = models.DateTimeField(
        auto_now=True,
        help_text=_('When capacity was last updated')
    )
    
    # Service characteristics
    is_emergency_service = models.BooleanField(
        default=False,
        help_text=_('Available during emergencies')
    )
    requires_appointment = models.BooleanField(
        default=False,
        help_text=_('Requires advance appointment')
    )
    accepts_walk_ins = models.BooleanField(
        default=True,
        help_text=_('Accepts walk-in clients')
    )
    is_free = models.BooleanField(
        default=True,
        help_text=_('Service is provided free of charge')
    )
    cost_info = models.TextField(
        blank=True,
        help_text=_('Cost and payment information')
    )
    
    # Eligibility and requirements
    eligibility_criteria = models.TextField(
        blank=True,
        help_text=_('Who is eligible for this service')
    )
    required_documents = models.TextField(
        blank=True,
        help_text=_('Required documentation')
    )
    age_restrictions = models.CharField(
        max_length=100,
        blank=True,
        help_text=_('Age restrictions (e.g., "18+", "Children only")')
    )
    
    # Administrative
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='managed_services',
        help_text=_('Service manager responsible for updates')
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Service has been verified by moderators')
    )
    verified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='verified_services',
        help_text=_('Moderator who verified this service')
    )
    verified_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When service was verified')
    )
    
    # Status tracking
    current_status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        default=ServiceStatus.OPEN,
        help_text=_('Current operational status')
    )
    status_updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='status_updates',
        help_text=_('User who last updated status')
    )
    
    # Visibility and quality
    is_active = models.BooleanField(
        default=True,
        help_text=_('Service is active and visible to users')
    )
    quality_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text=_('Quality score based on feedback (0-5)')
    )
    total_ratings = models.PositiveIntegerField(
        default=0,
        help_text=_('Total number of ratings received')
    )
    
    # Search optimization
    search_vector = models.TextField(
        blank=True,
        help_text=_('Pre-computed search text for full-text search')
    )
    
    class Meta:
        verbose_name = _('Service')
        verbose_name_plural = _('Services')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['category', 'is_active', 'is_verified']),
            models.Index(fields=['current_status', 'is_emergency_service']),
            models.Index(fields=['city', 'state_province']),
            models.Index(fields=['is_verified', 'is_active']),
            models.Index(fields=['quality_score']),
            models.Index(fields=['manager']),
        ]
    
    def __str__(self) -> str:
        return f"{self.name} ({self.city})"
    
    def save(self, *args, **kwargs):
        """Auto-generate slug and search vector."""
        if not self.slug:
            base_slug = python_slugify(f"{self.name}-{self.city}")
            # Ensure uniqueness
            counter = 1
            slug = base_slug
            while Service.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        
        # Update search vector
        self._update_search_vector()
        
        super().save(*args, **kwargs)
    
    def _update_search_vector(self) -> None:
        """Update the search vector for full-text search."""
        search_text = ' '.join(filter(None, [
            self.name,
            self.description,
            self.short_description,
            self.address,
            self.city,
            self.category.name if self.category else '',
            ' '.join(self.tags) if self.tags else '',
            self.eligibility_criteria,
        ]))
        self.search_vector = search_text.lower()
    
    def get_absolute_url(self) -> str:
        return reverse('services:detail', kwargs={'pk': self.pk})
    
    @property
    def capacity_percentage(self) -> Optional[float]:
        """Calculate current capacity as percentage."""
        if self.max_capacity and self.max_capacity > 0:
            return (self.current_capacity / self.max_capacity) * 100
        return None
    
    @property
    def is_near_capacity(self) -> bool:
        """Check if service is near capacity (>90%)."""
        capacity_pct = self.capacity_percentage
        return capacity_pct is not None and capacity_pct >= 90
    
    @property
    def is_at_capacity(self) -> bool:
        """Check if service is at full capacity."""
        capacity_pct = self.capacity_percentage
        return capacity_pct is not None and capacity_pct >= 100
    
    @property
    def display_capacity_status(self) -> str:
        """Get display-friendly capacity status."""
        if not self.max_capacity:
            return _('Capacity unknown')
        
        capacity_pct = self.capacity_percentage
        if capacity_pct >= 100:
            return _('Full')
        elif capacity_pct >= 90:
            return _('Nearly full')
        elif capacity_pct >= 70:
            return _('Moderately busy')
        elif capacity_pct >= 30:
            return _('Available')
        else:
            return _('Plenty of space')
    
    @property
    def coordinates(self) -> Tuple[float, float]:
        """Get coordinates as (lat, lng) tuple."""
        return (self.latitude, self.longitude)
    
    def is_open_now(self) -> bool:
        """Check if service is currently open based on hours."""
        if self.current_status not in [ServiceStatus.OPEN, ServiceStatus.LIMITED]:
            return False
        
        if self.is_24_7:
            return True
        
        # TODO: Implement hour-based logic using hours_of_operation JSON
        # For now, assume open if status is OPEN
        return self.current_status == ServiceStatus.OPEN
    
    def distance_from(self, point: Tuple[float, float]) -> float:
        """Calculate distance from given point."""
        # TODO: Implement distance calculation without PostGIS
        # This method needs to be updated to use the new latitude and longitude fields
        # For now, we'll return 0 as a placeholder
        return 0.0  # self.location.distance(point)
    
    def update_capacity(self, new_capacity: int, updated_by: User) -> None:
        """Update current capacity and trigger notifications."""
        old_capacity = self.current_capacity
        self.current_capacity = new_capacity
        self.capacity_last_updated = timezone.now()
        self.status_updated_by = updated_by
        
        # Auto-update status based on capacity
        if self.is_at_capacity and self.current_status == ServiceStatus.OPEN:
            self.current_status = ServiceStatus.FULL
        elif not self.is_at_capacity and self.current_status == ServiceStatus.FULL:
            self.current_status = ServiceStatus.OPEN
        
        self.save(update_fields=[
            'current_capacity', 'capacity_last_updated', 
            'status_updated_by', 'current_status'
        ])
        
        # Trigger Observer pattern notification (implemented in signals)
        from django.db.models.signals import post_save
        post_save.send(sender=self.__class__, instance=self, created=False)
    
    def verify_service(self, verified_by: User) -> None:
        """Mark service as verified by a moderator."""
        if verified_by.can_moderate_content:
            self.is_verified = True
            self.verified_by = verified_by
            self.verified_at = timezone.now()
            self.save(update_fields=['is_verified', 'verified_by', 'verified_at'])


class RealTimeStatusUpdate(TimestampedMixin):
    """
    Real-time status updates for services implementing Observer pattern.
    
    Tracks status changes over time and enables notifications to
    subscribed users and external systems.
    """
    CHANGE_TYPES = [
        ('status', _('Status Change')),
        ('capacity', _('Capacity Update')),
        ('hours', _('Hours Change')),
        ('emergency', _('Emergency Alert')),
        ('closure', _('Temporary Closure')),
        ('reopening', _('Reopening')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='status_updates',
        help_text=_('Service being updated')
    )
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPES,
        help_text=_('Type of status change')
    )
    
    # Status change details
    old_status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        blank=True,
        help_text=_('Previous status')
    )
    new_status = models.CharField(
        max_length=20,
        choices=ServiceStatus.choices,
        blank=True,
        help_text=_('New status')
    )
    
    # Capacity change details
    old_capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=_('Previous capacity')
    )
    new_capacity = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text=_('New capacity')
    )
    
    # Update details
    message = models.TextField(
        blank=True,
        help_text=_('Optional update message')
    )
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_updates',
        help_text=_('User who made the update')
    )
    
    # Notification tracking
    notifications_sent = models.BooleanField(
        default=False,
        help_text=_('Whether notifications have been sent')
    )
    notification_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of notifications sent')
    )
    
    # Metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional update context')
    )
    
    class Meta:
        verbose_name = _('Real-time Status Update')
        verbose_name_plural = _('Real-time Status Updates')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service', 'change_type', 'created_at']),
            models.Index(fields=['notifications_sent']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.service.name} - {self.get_change_type_display()} at {self.created_at}"
    
    @property
    def capacity_change_direction(self) -> Optional[str]:
        """Get direction of capacity change."""
        if self.old_capacity is not None and self.new_capacity is not None:
            if self.new_capacity > self.old_capacity:
                return 'increased'
            elif self.new_capacity < self.old_capacity:
                return 'decreased'
            else:
                return 'unchanged'
        return None
    
    @property
    def is_emergency_related(self) -> bool:
        """Check if update is emergency-related."""
        emergency_types = ['emergency', 'closure']
        emergency_statuses = [ServiceStatus.EMERGENCY_ONLY, ServiceStatus.TEMPORARILY_CLOSED]
        
        return (
            self.change_type in emergency_types or
            self.new_status in emergency_statuses or
            (self.service.is_emergency_service and self.change_type == 'status')
        )
    
    def mark_notifications_sent(self, count: int = 0) -> None:
        """Mark that notifications have been sent for this update."""
        self.notifications_sent = True
        self.notification_count = count
        self.save(update_fields=['notifications_sent', 'notification_count'])


class ServiceAlert(TimestampedMixin):
    """
    Service alerts for temporary announcements and urgent updates.
    
    Used by service managers to communicate important information
    to users in real-time.
    """
    ALERT_TYPES = [
        ('info', _('Information')),
        ('warning', _('Warning')),
        ('urgent', _('Urgent')),
        ('closure', _('Temporary Closure')),
        ('capacity', _('Capacity Alert')),
        ('schedule', _('Schedule Change')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='alerts',
        help_text=_('Service this alert relates to')
    )
    alert_type = models.CharField(
        max_length=20,
        choices=ALERT_TYPES,
        help_text=_('Type of alert')
    )
    title = models.CharField(
        max_length=200,
        help_text=_('Alert title')
    )
    message = models.TextField(
        help_text=_('Alert message content')
    )
    
    # Visibility and timing
    is_active = models.BooleanField(
        default=True,
        help_text=_('Alert is currently active')
    )
    start_time = models.DateTimeField(
        default=timezone.now,
        help_text=_('When alert becomes active')
    )
    end_time = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When alert expires (null = no expiration)')
    )
    
    # Priority and display
    priority = models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Alert priority (1=low, 5=critical)')
    )
    show_on_map = models.BooleanField(
        default=True,
        help_text=_('Show alert indicator on map')
    )
    requires_acknowledgment = models.BooleanField(
        default=False,
        help_text=_('Users must acknowledge before accessing service')
    )
    
    # Administrative
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_alerts',
        help_text=_('User who created this alert')
    )
    
    class Meta:
        verbose_name = _('Service Alert')
        verbose_name_plural = _('Service Alerts')
        ordering = ['-priority', '-created_at']
        indexes = [
            models.Index(fields=['service', 'is_active', 'start_time']),
            models.Index(fields=['alert_type', 'priority']),
            models.Index(fields=['end_time']),
        ]
    
    def __str__(self) -> str:
        return f"{self.service.name} - {self.title}"
    
    @property
    def is_expired(self) -> bool:
        """Check if alert has expired."""
        if self.end_time:
            return timezone.now() > self.end_time
        return False
    
    @property
    def is_current(self) -> bool:
        """Check if alert is currently active and not expired."""
        now = timezone.now()
        return (
            self.is_active and
            self.start_time <= now and
            (self.end_time is None or self.end_time > now)
        )
    
    @property
    def priority_display(self) -> str:
        """Get display-friendly priority level."""
        priority_map = {
            1: _('Low'),
            2: _('Normal'),
            3: _('Medium'),
            4: _('High'),
            5: _('Critical'),
        }
        return priority_map.get(self.priority, _('Unknown'))
    
    def expire_alert(self) -> None:
        """Manually expire the alert."""
        self.end_time = timezone.now()
        self.is_active = False
        self.save(update_fields=['end_time', 'is_active'])


# Model managers and querysets for efficient database operations

class ServiceQuerySet(models.QuerySet):
    """Custom queryset for Service model with common filters."""
    
    def active(self):
        """Filter to active services only."""
        return self.filter(is_active=True)
    
    def verified(self):
        """Filter to verified services only."""
        return self.filter(is_verified=True)
    
    def public(self):
        """Filter to services visible to public users."""
        return self.active().verified()
    
    def emergency_eligible(self):
        """Filter to services available during emergencies."""
        return self.filter(is_emergency_service=True)
    
    def open_now(self):
        """Filter to services currently open."""
        return self.filter(current_status__in=[ServiceStatus.OPEN, ServiceStatus.LIMITED])
    
    def near_point(self, point: Tuple[float, float], distance_km: float):
        """Filter services within specified distance of point."""
        # TODO: Implement distance filtering without PostGIS
        # This method needs to be updated to use the new latitude and longitude fields
        # For now, we'll return all services as a placeholder
        return self  # .filter(location__distance_lte=(point, Distance(km=distance_km)))
    
    def by_category(self, category_slug: str):
        """Filter by category slug."""
        return self.filter(category__slug=category_slug)
    
    def search(self, query: str):
        """Basic text search across service fields."""
        if not query:
            return self
        
        query_lower = query.lower()
        return self.filter(search_vector__icontains=query_lower)


# Apply custom manager to Service model
Service.add_to_class('objects', ServiceQuerySet.as_manager()) 