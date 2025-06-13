"""
Context processors for CommuMap.

Provides global context data for all templates including system settings,
user permissions, and map configuration.
"""
from typing import Dict, Any
from django.http import HttpRequest
from django.conf import settings

from .models import SystemSettings, UserRole


def global_settings(request: HttpRequest) -> Dict[str, Any]:
    """
    Provide global system settings and user context to all templates.
    
    Returns system configuration, user role information, and map settings
    that are needed across all pages.
    """
    try:
        system_settings = SystemSettings.get_instance()
    except:
        # Fallback if settings not yet created
        system_settings = None
    
    # Base context
    context = {
        'system_settings': system_settings,
        'user_roles': UserRole,
        'map_config': {
            'default_center_lat': getattr(settings, 'DEFAULT_MAP_CENTER_LAT', 40.7128),
            'default_center_lng': getattr(settings, 'DEFAULT_MAP_CENTER_LNG', -74.0060),
            'default_zoom': getattr(settings, 'DEFAULT_MAP_ZOOM', 12),
            'emergency_radius_km': getattr(settings, 'EMERGENCY_SEARCH_RADIUS_KM', 5),
        },
        'debug': settings.DEBUG,
    }
    
    # Add user-specific context if authenticated
    if request.user.is_authenticated:
        user = request.user
        context.update({
            'user_display_name': user.get_display_name(),
            'user_role_display': user.get_role_display(),
            'user_can_manage_services': user.can_manage_services,
            'user_can_moderate_content': user.can_moderate_content,
            'user_is_admin': user.is_admin_user,
            'user_requires_verification': user.requires_verification and not user.is_verified,
            'verification_pending': (
                user.requires_verification and 
                user.verification_requested_at and 
                not user.is_verified
            ),
        })
        
        # Add preferred location if available
        if user.preferred_location_lat and user.preferred_location_lng:
            context['user_preferred_location'] = {
                'lat': user.preferred_location_lat,
                'lng': user.preferred_location_lng,
            }
    
    # Add system announcement if active
    if system_settings and system_settings.announcement_active and system_settings.system_announcement:
        context['system_announcement'] = system_settings.system_announcement
    
    # Add maintenance mode status
    if system_settings:
        context['maintenance_mode'] = system_settings.maintenance_mode
    
    return context


def navigation_context(request: HttpRequest) -> Dict[str, Any]:
    """
    Provide navigation-specific context based on user role.
    
    Returns appropriate navigation links and permissions for the current user.
    """
    context = {}
    
    if request.user.is_authenticated:
        user = request.user
        
        # Base navigation items available to all authenticated users
        nav_items = [
            {'name': 'Map', 'url': 'services:map', 'icon': 'map'},
            {'name': 'Services', 'url': 'services:list', 'icon': 'building'},
        ]
        
        # Role-specific navigation
        if user.role == UserRole.USER:
            nav_items.extend([
                {'name': 'Bookmarks', 'url': 'users:bookmarks', 'icon': 'bookmark'},
                {'name': 'Recommendations', 'url': 'users:recommendations', 'icon': 'star'},
                {'name': 'Profile', 'url': 'users:profile', 'icon': 'user'},
            ])
        
        elif user.role == UserRole.SERVICE_MANAGER and user.is_verified:
            nav_items.extend([
                {'name': 'Dashboard', 'url': 'manager:dashboard', 'icon': 'dashboard'},
                {'name': 'My Services', 'url': 'manager:services', 'icon': 'building'},
                {'name': 'Analytics', 'url': 'manager:analytics', 'icon': 'chart'},
                {'name': 'Profile', 'url': 'manager:profile', 'icon': 'user'},
            ])
        
        elif user.role == UserRole.COMMUNITY_MODERATOR and user.is_verified:
            nav_items.extend([
                {'name': 'Dashboard', 'url': 'moderators:dashboard', 'icon': 'shield'},
                {'name': 'Service Queue', 'url': 'moderators:services_pending', 'icon': 'clock'},
                {'name': 'Comments', 'url': 'moderators:comments_pending', 'icon': 'message'},
                {'name': 'Outreach', 'url': 'moderators:outreach', 'icon': 'megaphone'},
                {'name': 'Profile', 'url': 'moderators:profile', 'icon': 'user'},
            ])
        
        elif user.role == UserRole.ADMIN and user.is_verified:
            nav_items.extend([
                {'name': 'Admin Console', 'url': 'console:home', 'icon': 'shield'},
                {'name': 'User Management', 'url': 'console:users', 'icon': 'users'},
                {'name': 'Services', 'url': 'console:services', 'icon': 'building'},
                {'name': 'System Health', 'url': 'console:system_health', 'icon': 'activity'},
                {'name': 'Announcements', 'url': 'console:announcements', 'icon': 'megaphone'},
                {'name': 'Maintenance', 'url': 'console:maintenance', 'icon': 'settings'},
                {'name': 'Profile', 'url': 'console:profile', 'icon': 'user'},
            ])
        
        context['nav_items'] = nav_items
        
        # Quick action items based on role
        quick_actions = []
        
        if user.role == UserRole.USER:
            quick_actions = [
                {'name': 'Help Me Now', 'url': 'services:emergency', 'class': 'btn-error'},
            ]
        
        elif user.role == UserRole.SERVICE_MANAGER and user.is_verified:
            quick_actions = [
                {'name': 'Add Service', 'url': 'manager:service_create', 'class': 'btn-primary'},
                {'name': 'My Services', 'url': 'manager:services', 'class': 'btn-secondary'},
            ]
        
        elif user.role == UserRole.COMMUNITY_MODERATOR and user.is_verified:
            quick_actions = [
                {'name': 'Review Queue', 'url': 'moderators:services_pending', 'class': 'btn-warning'},
                {'name': 'Dashboard', 'url': 'moderators:dashboard', 'class': 'btn-info'},
            ]
        
        elif user.role == UserRole.ADMIN and user.is_verified:
            quick_actions = [
                {'name': 'Admin Console', 'url': 'console:home', 'class': 'btn-primary'},
                {'name': 'System Health', 'url': 'console:system_health', 'class': 'btn-info'},
                {'name': 'Emergency Toggle', 'url': 'console:emergency_mode_toggle', 'class': 'btn-error'},
            ]
        
        context['quick_actions'] = quick_actions
    
    return context 