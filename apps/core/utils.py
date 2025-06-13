from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
from typing import List, Union
from django.http import HttpRequest


class RoleRequiredMixin(UserPassesTestMixin):
    """
    Mixin that requires user to have specific roles to access the view.
    
    This mixin extends UserPassesTestMixin to provide role-based access control
    for Django class-based views.
    """
    
    required_roles: Union[str, List[str]] = []
    redirect_url: str = '/'
    
    def test_func(self) -> bool:
        """
        Test if the user has the required role(s).
        
        Returns:
            bool: True if user has required role, False otherwise
        """
        if not self.request.user.is_authenticated:
            return False
            
        user_role = self.request.user.role
        
        if isinstance(self.required_roles, str):
            return user_role == self.required_roles
        elif isinstance(self.required_roles, list):
            return user_role in self.required_roles
            
        return False
    
    def handle_no_permission(self):
        """
        Handle cases where user doesn't have permission.
        
        Shows an appropriate error message and redirects.
        """
        if not self.request.user.is_authenticated:
            messages.error(
                self.request, 
                _('You must be logged in to access this page.')
            )
        else:
            messages.error(
                self.request,
                _('You do not have permission to access this page.')
            )
            
        return redirect(self.redirect_url)


def get_user_dashboard_url(user) -> str:
    """
    Get the appropriate dashboard URL based on user role.
    
    Args:
        user: User instance
        
    Returns:
        str: URL to user's role-specific dashboard
    """
    from apps.core.models import User
    
    role_urls = {
        User.Role.USER: '/dashboard/',
        User.Role.SERVICE_MANAGER: '/manager/dashboard/',
        User.Role.COMMUNITY_MODERATOR: '/moderator/dashboard/',
        User.Role.ADMIN: '/admin/dashboard/',
    }
    
    return role_urls.get(user.role, '/dashboard/')


def format_distance(distance_km: float) -> str:
    """
    Format distance for display.
    
    Args:
        distance_km: Distance in kilometers
        
    Returns:
        str: Formatted distance string
    """
    if distance_km < 1:
        meters = int(distance_km * 1000)
        return f"{meters}m"
    else:
        return f"{distance_km:.1f}km"


def get_client_ip(request: HttpRequest) -> str:
    """
    Get the client's IP address from the request.
    
    Args:
        request: Django HttpRequest object
        
    Returns:
        str: Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip 