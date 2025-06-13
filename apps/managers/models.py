"""
Manager-specific models for CommuMap Service Manager functionality.

This module contains models for service analytics, manager notifications,
and service status history tracking.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator

from apps.core.models import TimestampedMixin, User


class ServiceAnalytics(TimestampedMixin):
    """
    Analytics data for services managed by service managers.
    
    Tracks daily/weekly statistics for visits, ratings, and usage patterns.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='analytics',
        help_text=_('Service these analytics belong to')
    )
    
    # Date tracking
    date = models.DateField(
        help_text=_('Date for these analytics')
    )
    
    # Visit statistics
    total_visits = models.PositiveIntegerField(
        default=0,
        help_text=_('Total visits on this date')
    )
    unique_visitors = models.PositiveIntegerField(
        default=0,
        help_text=_('Unique visitors on this date')
    )
    
    # User engagement
    total_bookmarks = models.PositiveIntegerField(
        default=0,
        help_text=_('Total bookmarks added on this date')
    )
    feedback_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Feedback submissions on this date')
    )
    comment_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Comments posted on this date')
    )
    
    # Rating statistics
    average_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text=_('Average rating for this date')
    )
    rating_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of ratings received on this date')
    )
    
    # Capacity statistics
    average_capacity = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        help_text=_('Average capacity percentage for this date')
    )
    max_capacity_reached = models.PositiveIntegerField(
        default=0,
        help_text=_('Maximum capacity reached on this date')
    )
    
    # Peak usage times (stored as JSON)
    peak_hours = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Peak usage hours as {hour: visit_count}')
    )
    
    class Meta:
        verbose_name = _('Service Analytics')
        verbose_name_plural = _('Service Analytics')
        unique_together = ['service', 'date']
        ordering = ['-date']
        indexes = [
            models.Index(fields=['service', '-date']),
            models.Index(fields=['date']),
        ]
    
    def __str__(self) -> str:
        return f"{self.service.name} - {self.date}"


class ManagerNotification(TimestampedMixin):
    """
    Notifications specific to service managers.
    
    Handles manager-specific alerts such as capacity warnings,
    service approval updates, and system announcements.
    """
    NOTIFICATION_TYPES = [
        ('capacity_alert', _('Capacity Alert')),
        ('service_approved', _('Service Approved')),
        ('service_rejected', _('Service Rejected')),
        ('feedback_received', _('New Feedback')),
        ('comment_posted', _('New Comment')),
        ('system_announcement', _('System Announcement')),
        ('verification_required', _('Verification Required')),
        ('status_reminder', _('Status Update Reminder')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    manager = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='manager_notifications',
        help_text=_('Service manager receiving this notification')
    )
    
    notification_type = models.CharField(
        max_length=25,
        choices=NOTIFICATION_TYPES,
        help_text=_('Type of notification')
    )
    
    title = models.CharField(
        max_length=200,
        help_text=_('Notification title')
    )
    
    message = models.TextField(
        help_text=_('Notification message content')
    )
    
    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default='normal',
        help_text=_('Notification priority')
    )
    
    # Status tracking
    is_read = models.BooleanField(
        default=False,
        help_text=_('Whether notification has been read')
    )
    read_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification was read')
    )
    
    # Related objects
    related_service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='manager_notifications',
        help_text=_('Related service if applicable')
    )
    
    action_url = models.URLField(
        blank=True,
        help_text=_('URL for notification action')
    )
    
    # Expiry
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When notification expires')
    )
    
    class Meta:
        verbose_name = _('Manager Notification')
        verbose_name_plural = _('Manager Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['manager', '-created_at']),
            models.Index(fields=['manager', 'is_read']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} - {self.manager.get_display_name()}"
    
    def mark_as_read(self) -> None:
        """Mark notification as read."""
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])
    
    @property
    def is_expired(self) -> bool:
        """Check if notification has expired."""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False


class ServiceStatusHistory(TimestampedMixin):
    """
    Audit trail for service status changes made by managers.
    
    Tracks all status updates, capacity changes, and alert creations
    for accountability and analytics.
    """
    CHANGE_TYPES = [
        ('status', _('Status Change')),
        ('capacity', _('Capacity Update')),
        ('alert_created', _('Alert Created')),
        ('alert_expired', _('Alert Expired')),
        ('hours_updated', _('Hours Updated')),
        ('emergency_toggle', _('Emergency Status Toggle')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service = models.ForeignKey(
        'services.Service',
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text=_('Service that was modified')
    )
    
    manager = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='service_status_changes',
        help_text=_('Manager who made the change')
    )
    
    change_type = models.CharField(
        max_length=20,
        choices=CHANGE_TYPES,
        help_text=_('Type of change made')
    )
    
    # Change details
    old_value = models.TextField(
        blank=True,
        help_text=_('Previous value (JSON or text)')
    )
    new_value = models.TextField(
        blank=True,
        help_text=_('New value (JSON or text)')
    )
    
    description = models.TextField(
        blank=True,
        help_text=_('Description of the change')
    )
    
    # Session tracking
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text=_('IP address of the change')
    )
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )
    
    class Meta:
        verbose_name = _('Service Status History')
        verbose_name_plural = _('Service Status Histories')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['service', '-created_at']),
            models.Index(fields=['manager', '-created_at']),
            models.Index(fields=['change_type', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.service.name} - {self.get_change_type_display()} by {self.manager.get_display_name() if self.manager else 'System'}"
