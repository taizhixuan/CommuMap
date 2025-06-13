"""
Feedback models for CommuMap including user reviews and comments.

This module implements user feedback system with reviews, ratings,
and threaded comments for community engagement.
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.utils import timezone

from apps.core.models import TimestampedMixin, User
from apps.services.models import Service


class ServiceReview(TimestampedMixin):
    """
    User reviews for services with star ratings and detailed feedback.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text=_('Service being reviewed')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reviews',
        help_text=_('User who wrote the review')
    )
    
    # Review content
    rating = models.PositiveIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_('Star rating from 1 to 5')
    )
    title = models.CharField(
        max_length=200,
        help_text=_('Review title')
    )
    content = models.TextField(
        help_text=_('Detailed review content')
    )
    
    # Review categories/tags
    REVIEW_TAGS = [
        ('helpful_staff', _('Helpful Staff')),
        ('clean_facility', _('Clean Facility')),
        ('easy_access', _('Easy Access')),
        ('quick_service', _('Quick Service')),
        ('good_hours', _('Good Hours')),
        ('professional', _('Professional')),
        ('welcoming', _('Welcoming Environment')),
        ('needs_improvement', _('Needs Improvement')),
    ]
    
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text=_('Review category tags')
    )
    
    # Visit information
    visit_date = models.DateField(
        blank=True,
        null=True,
        help_text=_('Date of service visit')
    )
    
    # Review status
    is_verified = models.BooleanField(
        default=False,
        help_text=_('Review has been verified as legitimate')
    )
    is_anonymous = models.BooleanField(
        default=False,
        help_text=_('Hide reviewer name from public display')
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text=_('Review has been flagged for moderation')
    )
    
    # Moderation
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_reviews',
        help_text=_('Moderator who approved this review')
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When review was approved')
    )
    
    # Engagement
    helpful_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of "helpful" votes')
    )
    unhelpful_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of "unhelpful" votes')
    )
    
    class Meta:
        verbose_name = _('Service Review')
        verbose_name_plural = _('Service Reviews')
        ordering = ['-created_at']
        unique_together = ['service', 'user']  # One review per user per service
        indexes = [
            models.Index(fields=['service', 'rating']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['is_verified', 'is_flagged']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_display_name()}: {self.rating}★ for {self.service.name}"
    
    def get_absolute_url(self) -> str:
        return reverse('feedback:review_detail', kwargs={'pk': self.pk})
    
    @property
    def helpful_ratio(self) -> float:
        """Calculate ratio of helpful to total votes."""
        total_votes = self.helpful_count + self.unhelpful_count
        if total_votes == 0:
            return 0.0
        return self.helpful_count / total_votes
    
    @property
    def display_name(self) -> str:
        """Return reviewer name or Anonymous."""
        if self.is_anonymous:
            return _('Anonymous User')
        return self.user.get_display_name()


class ServiceComment(TimestampedMixin):
    """
    Threaded comments system for community discussion about services.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Core relationships
    service = models.ForeignKey(
        Service,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('Service being discussed')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comments',
        help_text=_('User who posted the comment')
    )
    
    # Threading support
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
        help_text=_('Parent comment for threading')
    )
    
    # Comment content
    content = models.TextField(
        help_text=_('Comment content')
    )
    
    # Comment status
    is_approved = models.BooleanField(
        default=False,
        help_text=_('Comment has been approved for public display')
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text=_('Comment has been flagged for moderation')
    )
    is_edited = models.BooleanField(
        default=False,
        help_text=_('Comment has been edited')
    )
    
    # Moderation
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='approved_comments',
        help_text=_('Moderator who approved this comment')
    )
    approved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When comment was approved')
    )
    
    # Engagement
    like_count = models.PositiveIntegerField(
        default=0,
        help_text=_('Number of likes')
    )
    
    class Meta:
        verbose_name = _('Service Comment')
        verbose_name_plural = _('Service Comments')
        ordering = ['created_at']  # Chronological for threading
        indexes = [
            models.Index(fields=['service', 'created_at']),
            models.Index(fields=['parent', 'created_at']),
            models.Index(fields=['is_approved', 'is_flagged']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_display_name()}: Comment on {self.service.name}"
    
    def get_absolute_url(self) -> str:
        return reverse('services:detail', kwargs={'pk': self.service.pk}) + f'#comment-{self.pk}'
    
    @property
    def is_reply(self) -> bool:
        """Check if this is a reply to another comment."""
        return self.parent is not None
    
    @property
    def thread_level(self) -> int:
        """Calculate nesting level of this comment."""
        level = 0
        parent = self.parent
        while parent:
            level += 1
            parent = parent.parent
            if level > 5:  # Prevent infinite loops
                break
        return level


class ReviewHelpfulVote(TimestampedMixin):
    """
    User votes on review helpfulness.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    review = models.ForeignKey(
        ServiceReview,
        on_delete=models.CASCADE,
        related_name='votes',
        help_text=_('Review being voted on')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='review_votes',
        help_text=_('User casting the vote')
    )
    is_helpful = models.BooleanField(
        help_text=_('True for helpful, False for unhelpful')
    )
    
    class Meta:
        verbose_name = _('Review Vote')
        verbose_name_plural = _('Review Votes')
        unique_together = ['review', 'user']  # One vote per user per review
        indexes = [
            models.Index(fields=['review', 'is_helpful']),
        ]
    
    def __str__(self) -> str:
        vote_type = "helpful" if self.is_helpful else "unhelpful"
        return f"{self.user.get_display_name()}: {vote_type} for review {self.review.pk}"


class CommentLike(TimestampedMixin):
    """
    User likes on comments.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    comment = models.ForeignKey(
        ServiceComment,
        on_delete=models.CASCADE,
        related_name='likes',
        help_text=_('Comment being liked')
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='comment_likes',
        help_text=_('User who liked the comment')
    )
    
    class Meta:
        verbose_name = _('Comment Like')
        verbose_name_plural = _('Comment Likes')
        unique_together = ['comment', 'user']  # One like per user per comment
        indexes = [
            models.Index(fields=['comment', 'user']),
        ]
    
    def __str__(self) -> str:
        return f"{self.user.get_display_name()}: Liked comment {self.comment.pk}"


class FlaggedContent(TimestampedMixin):
    """
    Content flagging system for moderation.
    """
    FLAG_REASONS = [
        ('spam', _('Spam')),
        ('inappropriate', _('Inappropriate Content')),
        ('offensive', _('Offensive Language')),
        ('harassment', _('Harassment')),
        ('misinformation', _('Misinformation')),
        ('off_topic', _('Off Topic')),
        ('duplicate', _('Duplicate Content')),
        ('other', _('Other')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Flagged user and content
    flagged_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='flags_submitted',
        help_text=_('User who submitted the flag')
    )
    
    # Content being flagged (using generic relation would be better but this is simpler)
    review = models.ForeignKey(
        ServiceReview,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='flags',
        help_text=_('Flagged review')
    )
    comment = models.ForeignKey(
        ServiceComment,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='flags',
        help_text=_('Flagged comment')
    )
    
    # Flag details
    reason = models.CharField(
        max_length=20,
        choices=FLAG_REASONS,
        help_text=_('Reason for flagging')
    )
    description = models.TextField(
        blank=True,
        help_text=_('Additional details about the flag')
    )
    
    # Moderation status
    is_resolved = models.BooleanField(
        default=False,
        help_text=_('Flag has been reviewed and resolved')
    )
    resolved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='flags_resolved',
        help_text=_('Moderator who resolved this flag')
    )
    resolved_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=_('When flag was resolved')
    )
    resolution_notes = models.TextField(
        blank=True,
        help_text=_('Moderator notes on resolution')
    )
    
    class Meta:
        verbose_name = _('Flagged Content')
        verbose_name_plural = _('Flagged Content')
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_resolved', 'created_at']),
            models.Index(fields=['reason', 'is_resolved']),
        ]
    
    def __str__(self) -> str:
        content_type = "review" if self.review else "comment"
        return f"Flag: {self.reason} on {content_type} by {self.flagged_by.get_display_name()}"
    
    def resolve_flag(self, resolved_by: User, notes: str = '') -> None:
        """Mark flag as resolved."""
        self.is_resolved = True
        self.resolved_by = resolved_by
        self.resolved_at = timezone.now()
        self.resolution_notes = notes
        self.save()
