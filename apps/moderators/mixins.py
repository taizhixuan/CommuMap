"""
Mixins for moderator access control and functionality.
"""
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages

from apps.core.models import UserRole


class ModeratorRequiredMixin(LoginRequiredMixin):
    """
    Mixin that requires the user to be a verified Community Moderator or Admin.
    """
    
    def dispatch(self, request, *args, **kwargs):
        # First check if user is logged in
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user has moderator role and is verified
        if not (
            request.user.role in [UserRole.COMMUNITY_MODERATOR, UserRole.ADMIN] 
            and request.user.is_verified
        ):
            messages.error(
                request, 
                'Access denied. Community Moderator privileges required.'
            )
            raise PermissionDenied("Community Moderator access required")
        
        return super().dispatch(request, *args, **kwargs) 