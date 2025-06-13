"""
Moderator models for CommuMap including OutreachPost and ModerationAction.

This module implements moderator-specific models for content management,
outreach campaigns, and audit trail tracking.
"""
import uuid
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.models import TimestampedMixin, User
from apps.services.models import Service, ServiceCategory
from apps.feedback.models import ServiceComment


class OutreachPost(TimestampedMixin):
    """
    Outreach posts created by community moderators for promotion and announcements.
    
    Used for community engagement, service promotion, and public announcements
    that moderators can create and manage.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Basic information
    title = models.CharField(
        max_length=200,
        help_text=_('Post title for display')
    )
    content = models.TextField(
        help_text=_('Main post content')
    )
    
    # Optional banner image URL
    banner_image_url = models.URLField(
        blank=True,
        help_text=_('Optional banner image URL for the post')
    )
    
    # Created by moderator
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='outreach_posts',
        help_text=_('Moderator who created this post')
    )
    
    # Post status
    is_active = models.BooleanField(
        default=True,
        help_text=_('Whether this post is currently active')
    )
    
    # Optional expiry date
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When this post should expire (optional)')
    )
    
    # Target categories (for targeted outreach)
    target_categories = models.ManyToManyField(
        ServiceCategory,
        blank=True,
        related_name='outreach_posts',
        help_text=_('Service categories this post targets')
    )
    
    # Engagement metrics
    view_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of times this post has been viewed')
    )
    
    class Meta:
        verbose_name = _('Outreach Post')
        verbose_name_plural = _('Outreach Posts')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['expires_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} by {self.created_by.get_display_name()}"
    
    def get_absolute_url(self) -> str:
        return reverse('moderators:outreach_detail', kwargs={'pk': self.pk})
    
    @property
    def is_expired(self) -> bool:
        """Check if the post has expired."""
        if not self.expires_at:
            return False
        return timezone.now() > self.expires_at
    
    @property
    def is_visible(self) -> bool:
        """Check if the post should be visible to users."""
        return self.is_active and not self.is_expired
    
    def increment_view_count(self) -> None:
        """Increment the view count for this post."""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class ModerationAction(TimestampedMixin):
    """
    Audit trail for all moderation actions performed in the system.
    
    Provides accountability and traceability for administrative
    actions performed by community moderators.
    """
    ACTION_TYPES = [
        ('approve_service', _('Approved Service')),
        ('reject_service', _('Rejected Service')),
        ('approve_comment', _('Approved Comment')),
        ('reject_comment', _('Rejected Comment')),
        ('edit_service', _('Edited Service')),
        ('resolve_flag', _('Resolved Flag')),
        ('create_outreach', _('Created Outreach Post')),
        ('edit_outreach', _('Edited Outreach Post')),
        ('delete_outreach', _('Deleted Outreach Post')),
        ('bulk_approve_services', _('Bulk Approved Services')),
        ('bulk_reject_services', _('Bulk Rejected Services')),
        ('bulk_approve_comments', _('Bulk Approved Comments')),
        ('bulk_reject_comments', _('Bulk Rejected Comments')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Who performed the action
    moderator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='moderation_actions',
        help_text=_('Moderator who performed this action')
    )
    
    # What action was performed
    action_type = models.CharField(
        max_length=30,
        choices=ACTION_TYPES,
        help_text=_('Type of moderation action')
    )
    
    # What was acted upon (optional - only one should be set)
    target_service = models.ForeignKey(
        Service,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moderation_actions',
        help_text=_('Service that was moderated')
    )
    target_comment = models.ForeignKey(
        ServiceComment,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moderation_actions',
        help_text=_('Comment that was moderated')
    )
    target_outreach = models.ForeignKey(
        OutreachPost,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='moderation_actions',
        help_text=_('Outreach post that was moderated')
    )
    
    # Action details
    reason = models.TextField(
        blank=True,
        help_text=_('Reason for the moderation action')
    )
    
    # Additional metadata (JSON for flexibility)
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=_('Additional action metadata')
    )
    
    # IP and user agent for security tracking
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        help_text=_('IP address of the moderator')
    )
    user_agent = models.TextField(
        blank=True,
        help_text=_('User agent string')
    )
    
    class Meta:
        verbose_name = _('Moderation Action')
        verbose_name_plural = _('Moderation Actions')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['moderator', '-created_at']),
            models.Index(fields=['action_type', '-created_at']),
            models.Index(fields=['target_service', '-created_at']),
            models.Index(fields=['target_comment', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.moderator.get_display_name()}: {self.get_action_type_display()}"
    
    def get_absolute_url(self) -> str:
        return reverse('moderators:action_detail', kwargs={'pk': self.pk})
    
    @property
    def target_display(self) -> str:
        """Get a human-readable display of what was acted upon."""
        if self.target_service:
            return f"Service: {self.target_service.name}"
        elif self.target_comment:
            return f"Comment: {self.target_comment.content[:50]}..."
        elif self.target_outreach:
            return f"Outreach: {self.target_outreach.title}"
        else:
            return "System Action"
    
    @classmethod
    def log_action(cls, moderator, action_type, reason='', **kwargs):
        """
        Helper method to create moderation action logs.
        
        Args:
            moderator: User who performed the action
            action_type: Type of action from ACTION_TYPES
            reason: Optional reason for the action
            **kwargs: Additional fields (target_service, target_comment, etc.)
        """
        return cls.objects.create(
            moderator=moderator,
            action_type=action_type,
            reason=reason,
            **kwargs
        )


class ModeratorNotification(TimestampedMixin):
    """
    Notifications specific to community moderators.
    
    Handles moderator-specific alerts such as new service submissions,
    pending approvals, and system announcements.
    """
    NOTIFICATION_TYPES = [
        ('new_service_submitted', _('New Service Submitted')),
        ('new_comment_submitted', _('New Comment Submitted')),
        ('service_resubmitted', _('Service Resubmitted')),
        ('comment_reported', _('Comment Reported')),
        ('system_announcement', _('System Announcement')),
        ('bulk_action_completed', _('Bulk Action Completed')),
        ('verification_required', _('Verification Required')),
        ('urgent_review', _('Urgent Review Required')),
    ]
    
    PRIORITY_CHOICES = [
        ('low', _('Low')),
        ('normal', _('Normal')),
        ('high', _('High')),
        ('urgent', _('Urgent')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    moderator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='moderator_notifications',
        help_text=_('Community moderator receiving this notification')
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
        related_name='moderator_notifications',
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
        verbose_name = _('Moderator Notification')
        verbose_name_plural = _('Moderator Notifications')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['moderator', '-created_at']),
            models.Index(fields=['moderator', 'is_read']),
            models.Index(fields=['priority', '-created_at']),
        ]
    
    def __str__(self) -> str:
        return f"{self.title} - {self.moderator.get_display_name()}"
    
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