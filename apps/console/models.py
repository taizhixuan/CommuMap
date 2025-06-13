"""
Admin Console models for CommuMap.

This module provides models for system announcements, maintenance tasks,
and system metrics monitoring.
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import TimestampedMixin, User


class SystemAnnouncement(TimestampedMixin):
    """
    System-wide announcements that can be displayed to users.
    
    Supports targeting specific user roles and scheduling announcements.
    """
    ANNOUNCEMENT_TYPES = [
        ('info', _('Information')),
        ('warning', _('Warning')),
        ('emergency', _('Emergency')),
        ('maintenance', _('Maintenance')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(
        max_length=200,
        help_text=_('Title of the announcement.')
    )
    content = models.TextField(
        help_text=_('Rich text content of the announcement.')
    )
    announcement_type = models.CharField(
        max_length=20,
        choices=ANNOUNCEMENT_TYPES,
        default='info',
        help_text=_('Type of announcement.')
    )
    target_roles = models.JSONField(
        default=list,
        help_text=_('List of user roles to target (empty = all users).')
    )
    target_regions = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Geographic regions to target (optional).')
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether the announcement is currently active.')
    )
    show_from = models.DateTimeField(
        default=timezone.now,
        help_text=_('When to start showing the announcement.')
    )
    show_until = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When to stop showing the announcement (optional).')
    )
    is_urgent = models.BooleanField(
        default=False,
        help_text=_('Mark as urgent for prominent display.')
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='announcements_created',
        help_text=_('Admin who created the announcement.')
    )
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times the announcement has been viewed.')
    )
    
    class Meta:
        verbose_name = _('System Announcement')
        verbose_name_plural = _('System Announcements')
        ordering = ['-is_urgent', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'show_from', 'show_until']),
            models.Index(fields=['announcement_type', 'is_active']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} ({self.get_announcement_type_display()})"
    
    @property
    def is_currently_active(self) -> bool:
        """Check if announcement should be displayed now."""
        if not self.is_active:
            return False
        
        now = timezone.now()
        if self.show_from > now:
            return False
        
        if self.show_until and self.show_until < now:
            return False
        
        return True
    
    def increment_view_count(self):
        """Increment the view count for this announcement."""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class MaintenanceTask(TimestampedMixin):
    """
    System maintenance tasks that can be executed by admins.
    
    Tracks maintenance operations like backups, cache clearing, etc.
    """
    TASK_TYPES = [
        ('backup', _('Database Backup')),
        ('cache_clear', _('Cache Clear')),
        ('log_rotation', _('Log Rotation')),
        ('feature_toggle', _('Feature Toggle')),
        ('system_update', _('System Update')),
        ('user_cleanup', _('User Data Cleanup')),
        ('service_reindex', _('Service Reindexing')),
        ('notification_cleanup', _('Notification Cleanup')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('running', _('Running')),
        ('completed', _('Completed')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    task_type = models.CharField(
        max_length=20,
        choices=TASK_TYPES,
        help_text=_('Type of maintenance task.')
    )
    title = models.CharField(
        max_length=200,
        help_text=_('Human-readable title for the task.')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Detailed description of the task.')
    )
    initiated_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='maintenance_tasks_initiated',
        help_text=_('Admin who initiated the task.')
    )
    parameters = models.JSONField(
        default=dict,
        help_text=_('Task-specific parameters and configuration.')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Current status of the task.')
    )
    result_data = models.JSONField(
        default=dict,
        help_text=_('Task execution results and output data.')
    )
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if task failed.')
    )
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the task execution started.')
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the task was completed.')
    )
    duration_seconds = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text=_('Task execution duration in seconds.')
    )
    
    class Meta:
        verbose_name = _('Maintenance Task')
        verbose_name_plural = _('Maintenance Tasks')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['task_type', 'status']),
            models.Index(fields=['initiated_by', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} ({self.get_status_display()})"
    
    def mark_started(self):
        """Mark the task as started."""
        self.status = 'running'
        self.started_at = timezone.now()
        self.save(update_fields=['status', 'started_at'])
    
    def mark_completed(self, result_data=None):
        """Mark the task as completed with optional result data."""
        self.status = 'completed'
        self.completed_at = timezone.now()
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        if result_data:
            self.result_data = result_data
        self.save(update_fields=['status', 'completed_at', 'duration_seconds', 'result_data'])
    
    def mark_failed(self, error_message):
        """Mark the task as failed with error message."""
        self.status = 'failed'
        self.completed_at = timezone.now()
        self.error_message = error_message
        if self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_seconds = int(delta.total_seconds())
        self.save(update_fields=['status', 'completed_at', 'error_message', 'duration_seconds'])


class SystemMetrics(TimestampedMixin):
    """
    System performance and usage metrics for monitoring.
    
    Stores time-series data for system health monitoring and analytics.
    """
    METRIC_CATEGORIES = [
        ('performance', _('Performance')),
        ('usage', _('Usage')),
        ('security', _('Security')),
        ('storage', _('Storage')),
        ('network', _('Network')),
        ('application', _('Application')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    metric_name = models.CharField(
        max_length=100,
        help_text=_('Name of the metric being recorded.')
    )
    metric_value = models.FloatField(
        help_text=_('Numeric value of the metric.')
    )
    metric_unit = models.CharField(
        max_length=20,
        help_text=_('Unit of measurement (e.g., MB, %, seconds).')
    )
    metric_category = models.CharField(
        max_length=50,
        choices=METRIC_CATEGORIES,
        help_text=_('Category classification of the metric.')
    )
    tags = models.JSONField(
        default=dict,
        help_text=_('Additional tags for metric filtering and grouping.')
    )
    recorded_at = models.DateTimeField(
        auto_now_add=True,
        help_text=_('When the metric was recorded.')
    )
    
    class Meta:
        verbose_name = _('System Metric')
        verbose_name_plural = _('System Metrics')
        ordering = ['-recorded_at']
        indexes = [
            models.Index(fields=['metric_name', 'recorded_at']),
            models.Index(fields=['metric_category', 'recorded_at']),
            models.Index(fields=['recorded_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.metric_name}: {self.metric_value} {self.metric_unit}"


class NotificationQueue(TimestampedMixin):
    """
    Queue for managing system notifications and alerts.
    
    Used by the NotificationDispatcher singleton to manage notification delivery.
    """
    NOTIFICATION_TYPES = [
        ('email', _('Email')),
        ('sms', _('SMS')),
        ('in_app', _('In-App')),
        ('system', _('System Alert')),
        ('emergency', _('Emergency Alert')),
    ]
    
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('sent', _('Sent')),
        ('failed', _('Failed')),
        ('cancelled', _('Cancelled')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        help_text=_('Type of notification.')
    )
    recipient_email = models.EmailField(
        blank=True,
        help_text=_('Recipient email address.')
    )
    recipient_phone = models.CharField(
        max_length=20,
        blank=True,
        help_text=_('Recipient phone number.')
    )
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='notifications_received',
        help_text=_('Recipient user (for in-app notifications).')
    )
    subject = models.CharField(
        max_length=200,
        help_text=_('Notification subject/title.')
    )
    message = models.TextField(
        help_text=_('Notification message content.')
    )
    data = models.JSONField(
        default=dict,
        help_text=_('Additional notification data and metadata.')
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        help_text=_('Current status of the notification.')
    )
    scheduled_for = models.DateTimeField(
        default=timezone.now,
        help_text=_('When the notification should be sent.')
    )
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=_('When the notification was actually sent.')
    )
    error_message = models.TextField(
        blank=True,
        help_text=_('Error message if sending failed.')
    )
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of retry attempts.')
    )
    
    class Meta:
        verbose_name = _('Notification Queue')
        verbose_name_plural = _('Notification Queue')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'scheduled_for']),
            models.Index(fields=['notification_type', 'status']),
            models.Index(fields=['recipient_user', 'created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.subject} ({self.get_notification_type_display()})"
