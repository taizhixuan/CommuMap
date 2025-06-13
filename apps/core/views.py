"""
Core views for CommuMap.

This module contains the main landing page, authentication views,
and common utility views that don't fit into specific apps.
"""
from typing import Dict, Any, Optional
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, CreateView, FormView
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.conf import settings

from .models import User, UserRole, SystemSettings
from .forms import UserRegistrationForm, CustomLoginForm
from apps.services.models import Service, ServiceCategory


class LandingPageView(TemplateView):
    """
    Landing page view showing hero map and registration/login options.
    
    This is the main entry point for public users and provides
    overview of available services and quick access to key features.
    """
    template_name = 'core/landing.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        """Add landing page specific context."""
        context = super().get_context_data(**kwargs)
        
        # Get basic statistics for the hero section
        try:
            total_services = Service.objects.public().count()
            total_categories = ServiceCategory.objects.filter(is_active=True).count()
            emergency_services = Service.objects.public().filter(is_emergency_service=True).count()
        except:
            # Fallback if database not ready
            total_services = 0
            total_categories = 0
            emergency_services = 0
        
        context.update({
            'stats': {
                'total_services': total_services,
                'total_categories': total_categories,
                'emergency_services': emergency_services,
            },
            'featured_categories': ServiceCategory.objects.filter(
                is_active=True
            ).order_by('sort_order')[:6],
            'show_hero_map': True,
        })
        
        return context


class CustomLoginView(LoginView):
    """
    Custom login view with role-based redirection.
    
    Redirects users to appropriate dashboards based on their role
    after successful authentication.
    """
    form_class = CustomLoginForm
    template_name = 'core/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self) -> str:
        """Redirect to appropriate dashboard based on user role."""
        user = self.request.user
        
        if user.role == UserRole.USER:
            return reverse('users:dashboard')
        elif user.role == UserRole.SERVICE_MANAGER and user.is_verified:
            return reverse('manager:dashboard')
        elif user.role == UserRole.COMMUNITY_MODERATOR and user.is_verified:
            return reverse('moderators:dashboard')
        elif user.role == UserRole.ADMIN and user.is_verified:
            return reverse('console:home')
        else:
            # For unverified special roles or fallback
            return reverse('core:landing')
    
    def form_valid(self, form):
        """Handle successful login with custom logic."""
        response = super().form_valid(form)
        
        # Update last active timestamp
        self.request.user.last_active = timezone.now()
        self.request.user.save(update_fields=['last_active'])
        
        # Show welcome message
        messages.success(
            self.request,
            _(f'Welcome back, {self.request.user.get_display_name()}!')
        )
        
        return response
    
    def form_invalid(self, form):
        """Handle login failure."""
        messages.error(
            self.request,
            _('Invalid email or password. Please try again.')
        )
        return super().form_invalid(form)


class UserRegistrationView(CreateView):
    """
    User registration view with role selection.
    
    Handles registration for all user types with appropriate
    verification workflows for special roles.
    """
    model = User
    form_class = UserRegistrationForm
    template_name = 'core/signup.html'
    success_url = reverse_lazy('core:registration_success')
    
    def form_valid(self, form):
        """Handle successful registration."""
        response = super().form_valid(form)
        user = self.object
        
        # Handle different user roles after registration
        if user.role == UserRole.USER:
            # For regular users, store success message and let them see the registration success page
            # They can log in from there using the "Start Your Journey" button
            messages.success(
                self.request,
                _(f'Welcome to CommuMap, {user.get_display_name()}! Your account has been created successfully.')
            )
        else:
            # For special roles, request verification
            user.request_verification()
            messages.info(
                self.request,
                _('Your account has been created. Verification is required for your role. '
                  'You will receive access once an admin approves your account.')
            )
        
        # Always redirect to registration success page
        return response
    
    def form_invalid(self, form):
        """Handle registration failure."""
        messages.error(
            self.request,
            _('Please correct the errors below and try again.')
        )
        return super().form_invalid(form)


class RegistrationSuccessView(TemplateView):
    """Success page after registration."""
    template_name = 'core/registration_success.html'


class CustomLogoutView(LogoutView):
    """Custom logout view with message."""
    next_page = 'core:landing'  # Redirect to landing page after logout
    
    def dispatch(self, request, *args, **kwargs):
        """Add logout message."""
        if request.user.is_authenticated:
            messages.success(request, _('You have been successfully logged out.'))
        return super().dispatch(request, *args, **kwargs)


class PrivacyPolicyView(TemplateView):
    """Privacy policy page."""
    template_name = 'core/privacy.html'


class TermsOfServiceView(TemplateView):
    """Terms of service page."""
    template_name = 'core/terms.html'


class AboutView(TemplateView):
    """About page with project information."""
    template_name = 'core/about.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'version': getattr(settings, 'VERSION', '1.0.0'),
            'contact_email': getattr(settings, 'CONTACT_EMAIL', 'contact@commumap.org'),
        })
        return context


@require_http_methods(["GET"])
def health_check(request: HttpRequest) -> JsonResponse:
    """
    Health check endpoint for monitoring.
    
    Returns basic system status and database connectivity.
    """
    try:
        # Check database connectivity
        User.objects.first()
        db_status = "healthy"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Check system settings
    try:
        settings_obj = SystemSettings.get_instance()
        maintenance_mode = settings_obj.maintenance_mode
    except:
        maintenance_mode = False
    
    return JsonResponse({
        'status': 'healthy' if db_status == "healthy" else 'degraded',
        'timestamp': timezone.now().isoformat(),
        'database': db_status,
        'maintenance_mode': maintenance_mode,
        'version': getattr(settings, 'VERSION', '1.0.0'),
    })


@require_http_methods(["GET"])
def system_status(request: HttpRequest) -> JsonResponse:
    """
    System status endpoint with detailed information.
    
    Requires authentication and provides more detailed system metrics.
    """
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        # Basic statistics
        stats = {
            'total_users': User.objects.count(),
            'total_services': Service.objects.count(),
            'verified_services': Service.objects.filter(is_verified=True).count(),
            'active_services': Service.objects.filter(is_active=True).count(),
            'emergency_services': Service.objects.filter(is_emergency_service=True).count(),
        }
        
        # Role breakdown
        role_stats = {}
        for role_code, role_name in UserRole.choices:
            role_stats[role_code] = User.objects.filter(role=role_code).count()
        
        # System settings
        system_settings = SystemSettings.get_instance()
        
        return JsonResponse({
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'statistics': stats,
            'user_roles': role_stats,
            'system_settings': {
                'maintenance_mode': system_settings.maintenance_mode,
                'registration_enabled': system_settings.registration_enabled,
                'emergency_mode': system_settings.emergency_mode,
            },
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'timestamp': timezone.now().isoformat(),
        }, status=500)


@login_required
@require_http_methods(["POST"])
def update_user_location(request: HttpRequest) -> JsonResponse:
    """
    Update user's preferred location via AJAX.
    
    Allows users to set their preferred location for service discovery.
    """
    try:
        import json
        from django.contrib.gis.geos import Point
        
        data = json.loads(request.body)
        lat = float(data.get('lat'))
        lng = float(data.get('lng'))
        
        # Validate coordinates
        if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
            return JsonResponse({'error': 'Invalid coordinates'}, status=400)
        
        # Update user location
        request.user.preferred_location = Point(lng, lat)
        request.user.save(update_fields=['preferred_location'])
        
        return JsonResponse({
            'success': True,
            'message': 'Location updated successfully',
            'location': {'lat': lat, 'lng': lng}
        })
        
    except (ValueError, KeyError, json.JSONDecodeError) as e:
        return JsonResponse({'error': 'Invalid request data'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
def get_map_config(request: HttpRequest) -> JsonResponse:
    """
    Get map configuration for frontend initialization.
    
    Returns map provider settings and user-specific preferences.
    """
    try:
        from apps.services.adapters import get_default_map_adapter
        
        # Get map adapter configuration
        map_adapter = get_default_map_adapter()
        config = map_adapter.get_map_config()
        
        # Add user-specific settings if authenticated
        if request.user.is_authenticated and request.user.preferred_location:
            config['user_location'] = {
                'lat': request.user.preferred_location.y,
                'lng': request.user.preferred_location.x,
            }
            config['user_search_radius'] = request.user.search_radius_km
        
        # Add emergency mode if active
        try:
            system_settings = SystemSettings.get_instance()
            config['emergency_mode'] = system_settings.emergency_mode
        except:
            config['emergency_mode'] = False
        
        return JsonResponse(config)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


class MaintenanceModeView(TemplateView):
    """
    Maintenance mode page shown when system is under maintenance.
    
    This view is displayed when the system is in maintenance mode
    and users cannot access normal functionality.
    """
    template_name = 'core/maintenance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            system_settings = SystemSettings.get_instance()
            context['maintenance_message'] = system_settings.system_announcement
        except:
            context['maintenance_message'] = _('System is currently under maintenance. Please try again later.')
        
        return context


class ErrorPageView(TemplateView):
    """Generic error page view."""
    
    def get_template_names(self):
        """Return appropriate error template."""
        status_code = getattr(self, 'status_code', 500)
        return [f'core/errors/{status_code}.html', 'core/errors/generic.html']
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_code'] = getattr(self, 'status_code', 500)
        return context


# Error handler views
def handler404(request, exception):
    """Custom 404 error handler."""
    return render(request, 'core/errors/404.html', status=404)


def handler500(request):
    """Custom 500 error handler."""
    return render(request, 'core/errors/500.html', status=500)


def handler403(request, exception):
    """Custom 403 error handler."""
    return render(request, 'core/errors/403.html', status=403)


def handler400(request, exception):
    """Custom 400 error handler."""
    return render(request, 'core/errors/400.html', status=400)


# Test view for development
@method_decorator(login_required, name='dispatch')
class DevTestView(TemplateView):
    """Development test view (only available in DEBUG mode)."""
    template_name = 'core/dev_test.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not settings.DEBUG:
            raise Http404("This view is only available in development mode")
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add test data for development
        context.update({
            'user_roles': UserRole.choices,
            'test_services': Service.objects.all()[:5],
            'test_categories': ServiceCategory.objects.all()[:5],
        })
        
        return context 