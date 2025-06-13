"""
Middleware for CommuMap role-based access control.

This module implements security middleware to enforce role-based
access control throughout the application.
"""
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

from .models import User, UserRole, SystemSettings


class RoleBasedAccessMiddleware:
    """
    Middleware to enforce role-based access control.
    
    Checks user permissions for role-specific URLs and redirects
    unauthorized users to appropriate pages.
    """
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        
        # Define role-based URL patterns
        self.role_patterns = {
            'manager/': [UserRole.SERVICE_MANAGER, UserRole.ADMIN],
            'moderator/': [UserRole.COMMUNITY_MODERATOR, UserRole.ADMIN],
            'admin/': [UserRole.ADMIN],
            'u/': [UserRole.USER, UserRole.SERVICE_MANAGER, UserRole.COMMUNITY_MODERATOR, UserRole.ADMIN],
        }
        
        # URLs that don't require authentication
        self.public_urls = [
            '/',
            '/signup',
            '/login',
            '/logout',
            '/privacy',
            '/accounts/',
            '/django-admin/',
            '/api/',
            '__debug__',
        ]
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process the request through RBAC checks."""
        # Check if system is in maintenance mode
        if self._is_maintenance_mode(request):
            return self._handle_maintenance_mode(request)
        
        # Skip RBAC for public URLs
        if self._is_public_url(request.path):
            response = self.get_response(request)
            return response
        
        # Check authentication for protected URLs
        if not request.user.is_authenticated:
            return redirect('account_login')
        
        # Check role-based access
        if not self._has_role_access(request):
            return self._handle_access_denied(request)
        
        # Check verification status for special roles
        if not self._is_verified_for_role(request.user):
            return self._handle_verification_required(request)
        
        response = self.get_response(request)
        return response
    
    def _is_maintenance_mode(self, request: HttpRequest) -> bool:
        """Check if system is in maintenance mode."""
        try:
            settings = SystemSettings.get_instance()
            return settings.maintenance_mode
        except:
            return False
    
    def _handle_maintenance_mode(self, request: HttpRequest) -> HttpResponse:
        """Handle requests during maintenance mode."""
        # Allow admin users to access during maintenance
        if (request.user.is_authenticated and 
            request.user.role == UserRole.ADMIN and 
            request.user.is_verified):
            response = self.get_response(request)
            return response
        
        # Redirect others to maintenance page
        from django.template.response import TemplateResponse
        return TemplateResponse(
            request,
            'core/maintenance.html',
            {'message': _('System is currently under maintenance. Please try again later.')},
            status=503
        )
    
    def _is_public_url(self, path: str) -> bool:
        """Check if URL is public and doesn't require authentication."""
        return any(path.startswith(url) for url in self.public_urls)
    
    def _has_role_access(self, request: HttpRequest) -> bool:
        """Check if user has role-based access to the requested URL."""
        user = request.user
        path = request.path
        
        # Check each role pattern
        for pattern, allowed_roles in self.role_patterns.items():
            if path.startswith(f'/{pattern}'):
                return user.role in allowed_roles
        
        # Default allow for other authenticated URLs
        return True
    
    def _is_verified_for_role(self, user: User) -> bool:
        """Check if user is verified for their role."""
        # Regular users don't need verification
        if user.role == UserRole.USER:
            return True
        
        # Other roles need verification
        return user.is_verified
    
    def _handle_access_denied(self, request: HttpRequest) -> HttpResponse:
        """Handle access denied scenarios."""
        messages.error(
            request,
            _('You do not have permission to access this page.')
        )
        return redirect('core:landing')
    
    def _handle_verification_required(self, request: HttpRequest) -> HttpResponse:
        """Handle verification required scenarios."""
        user = request.user
        
        # If verification not yet requested, request it
        if not user.verification_requested_at:
            user.request_verification()
            messages.info(
                request,
                _('Your account verification has been requested. '
                  'You will receive access once an admin approves your account.')
            )
        else:
            messages.warning(
                request,
                _('Your account is pending verification. '
                  'Please wait for admin approval.')
            )
        
        return redirect('core:landing')


class AuditLoggingMiddleware:
    """
    Middleware to log important user actions for audit purposes.
    
    Captures user actions, IP addresses, and other metadata
    for security and compliance purposes.
    """
    
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]):
        self.get_response = get_response
        
        # Actions to log
        self.logged_actions = {
            'POST': ['login', 'logout', 'signup', 'verify', 'approve', 'reject'],
            'DELETE': ['delete', 'remove'],
        }
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """Process request and log relevant actions."""
        response = self.get_response(request)
        
        # Log important actions
        if self._should_log_action(request, response):
            self._log_action(request, response)
        
        return response
    
    def _should_log_action(self, request: HttpRequest, response: HttpResponse) -> bool:
        """Determine if action should be logged."""
        method = request.method
        path = request.path
        
        # Log based on HTTP method and path patterns
        if method in self.logged_actions:
            action_keywords = self.logged_actions[method]
            return any(keyword in path.lower() for keyword in action_keywords)
        
        return False
    
    def _log_action(self, request: HttpRequest, response: HttpResponse) -> None:
        """Log the action to audit log."""
        try:
            from .models import AuditLog
            
            # Determine action type from request
            action = self._determine_action_type(request)
            
            # Create audit log entry
            AuditLog.objects.create(
                user=request.user if request.user.is_authenticated else None,
                action=action,
                description=f"{request.method} {request.path}",
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                metadata={
                    'method': request.method,
                    'path': request.path,
                    'status_code': response.status_code,
                    'query_params': dict(request.GET),
                }
            )
        except Exception:
            # Don't break the request if logging fails
            pass
    
    def _determine_action_type(self, request: HttpRequest) -> str:
        """Determine the action type from request path."""
        path = request.path.lower()
        
        if 'login' in path:
            return 'user_login'
        elif 'logout' in path:
            return 'user_logout'
        elif 'signup' in path:
            return 'user_created'
        elif 'verify' in path:
            return 'user_verified'
        elif 'approve' in path:
            return 'service_approved'
        elif 'reject' in path:
            return 'service_rejected'
        elif 'delete' in path:
            return 'content_deleted'
        else:
            return 'other_action'
    
    def _get_client_ip(self, request: HttpRequest) -> Optional[str]:
        """Get the real client IP address."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip 