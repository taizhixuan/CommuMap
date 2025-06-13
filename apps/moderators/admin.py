"""
Admin configuration for moderator models.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe

from .models import OutreachPost, ModerationAction


@admin.register(OutreachPost)
class OutreachPostAdmin(admin.ModelAdmin):
    """
    Admin interface for OutreachPost model.
    """
    list_display = [
        'title', 'created_by', 'is_active', 'view_count', 
        'expires_at', 'created_at'
    ]
    list_filter = [
        'is_active', 'created_at', 'expires_at', 'target_categories'
    ]
    search_fields = ['title', 'content', 'created_by__email']
    readonly_fields = ['view_count', 'created_at', 'updated_at']
    filter_horizontal = ['target_categories']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'content', 'banner_image', 'created_by')
        }),
        ('Status & Targeting', {
            'fields': ('is_active', 'expires_at', 'target_categories')
        }),
        ('Metrics', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(ModerationAction)
class ModerationActionAdmin(admin.ModelAdmin):
    """
    Admin interface for ModerationAction model.
    """
    list_display = [
        'moderator', 'action_type', 'target_display_short', 
        'created_at'
    ]
    list_filter = [
        'action_type', 'created_at', 'moderator'
    ]
    search_fields = [
        'moderator__email', 'reason', 'target_service__name',
        'target_comment__content'
    ]
    readonly_fields = [
        'created_at', 'updated_at', 'target_display_short'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Action Details', {
            'fields': ('moderator', 'action_type', 'reason')
        }),
        ('Targets', {
            'fields': (
                'target_service', 'target_comment', 'target_outreach'
            ),
            'description': 'Only one target should be set per action.'
        }),
        ('Metadata', {
            'fields': ('metadata', 'ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def target_display_short(self, obj):
        """Short display of the target for list view."""
        if obj.target_service:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:services_service_change', args=[obj.target_service.pk]),
                f"Service: {obj.target_service.name[:30]}..."
            )
        elif obj.target_comment:
            return f"Comment: {obj.target_comment.content[:30]}..."
        elif obj.target_outreach:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:moderators_outreachpost_change', args=[obj.target_outreach.pk]),
                f"Outreach: {obj.target_outreach.title[:30]}..."
            )
        return "System Action"
    
    target_display_short.short_description = "Target"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'moderator', 'target_service', 'target_comment', 'target_outreach'
        ) 