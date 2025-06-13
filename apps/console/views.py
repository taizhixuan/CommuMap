"""
Admin Console views for CommuMap.

Implements comprehensive admin functionality including user management,
system monitoring, maintenance tools, and content moderation.
"""
import json
from typing import Any, Dict
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import TemplateView, ListView, CreateView, UpdateView, DeleteView, View
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import reverse_lazy, reverse
from django.db.models import Q, Count
from django.utils import timezone
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from apps.core.models import User, UserRole, SystemSettings, AuditLog
from apps.services.models import Service, ServiceCategory
from apps.feedback.models import ServiceReview, ServiceComment
from .models import SystemAnnouncement, MaintenanceTask, SystemMetrics, NotificationQueue
from .managers import NotificationDispatcher, SettingsLoader
from .monitoring import SystemMonitor
from .maintenance import MaintenanceOperations
from .forms import (
    AdminUserCreationForm, AdminUserEditForm, AdminProfileForm,
    SystemAnnouncementForm, MaintenanceTaskForm
)


class AdminRequiredMixin(UserPassesTestMixin):
    """Mixin to ensure only verified admin users can access views."""
    
    def test_func(self):
        return (
            self.request.user.is_authenticated and
            self.request.user.role == UserRole.ADMIN and
            self.request.user.is_verified
        )
    
    def handle_no_permission(self):
        messages.error(self.request, "Admin access required.")
        return redirect('core:landing')


class AdminHomeView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    Admin home page with beautiful interface and quick access to all functions.
    
    Provides a modern landing page for administrators with system overview,
    quick actions, and recent activity.
    """
    template_name = 'console/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get system health overview
        system_health = SystemMonitor.get_system_overview()
        context['system_health'] = system_health
        
        # Get quick statistics
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'pending_verifications': User.objects.filter(
                role__in=[UserRole.SERVICE_MANAGER, UserRole.COMMUNITY_MODERATOR],
                is_verified=False,
                verification_requested_at__isnull=False
            ).count(),
            'total_services': Service.objects.count(),
            'active_services': Service.objects.filter(is_active=True).count(),
            'pending_services': Service.objects.filter(is_verified=False).count(),
            'total_feedback': ServiceReview.objects.count(),
            'recent_feedback': ServiceReview.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
        context['stats'] = stats
        
        # Get recent audit logs (fewer for home page)
        recent_logs = AuditLog.objects.select_related('user').order_by('-created_at')[:5]
        context['recent_logs'] = recent_logs
        
        # Get active announcements
        active_announcements_qs = SystemAnnouncement.objects.filter(
            is_active=True,
            show_from__lte=timezone.now()
        ).filter(
            Q(show_until__isnull=True) | Q(show_until__gte=timezone.now())
        ).order_by('-is_urgent', '-created_at')
        
        # Get urgent announcements count first (before slicing)
        urgent_announcements = active_announcements_qs.filter(is_urgent=True)
        context['urgent_announcements'] = urgent_announcements
        
        # Then slice for display
        active_announcements = active_announcements_qs[:3]
        context['active_announcements'] = active_announcements
        
        # Get recent maintenance tasks
        recent_tasks = MaintenanceTask.objects.select_related('initiated_by').order_by('-created_at')[:3]
        context['recent_tasks'] = recent_tasks
        
        # Get failed tasks count
        failed_tasks = MaintenanceTask.objects.filter(
            status='failed',
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).count()
        context['failed_tasks'] = failed_tasks
        
        # Get emergency mode status
        settings_instance = SystemSettings.get_instance()
        context['emergency_mode'] = settings_instance.emergency_mode
        context['maintenance_mode'] = settings_instance.maintenance_mode
        
        return context


class AdminDashboardView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """
    Main admin dashboard showing system health, alerts, and quick statistics.
    
    Provides a comprehensive overview of system status and recent activity.
    """
    template_name = 'console/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get system health overview
        system_health = SystemMonitor.get_system_overview()
        context['system_health'] = system_health
        
        # Get quick statistics
        stats = {
            'total_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'pending_verifications': User.objects.filter(
                role__in=[UserRole.SERVICE_MANAGER, UserRole.COMMUNITY_MODERATOR],
                is_verified=False,
                verification_requested_at__isnull=False
            ).count(),
            'total_services': Service.objects.count(),
            'active_services': Service.objects.filter(is_active=True).count(),
            'pending_services': Service.objects.filter(is_verified=False).count(),
            'total_feedback': ServiceReview.objects.count(),
            'recent_feedback': ServiceReview.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
        context['stats'] = stats
        
        # Get recent audit logs
        recent_logs = AuditLog.objects.select_related('user').order_by('-created_at')[:10]
        context['recent_logs'] = recent_logs
        
        # Get active announcements
        active_announcements = SystemAnnouncement.objects.filter(
            is_active=True,
            show_from__lte=timezone.now()
        ).filter(
            Q(show_until__isnull=True) | Q(show_until__gte=timezone.now())
        ).order_by('-is_urgent', '-created_at')[:5]
        context['active_announcements'] = active_announcements
        
        # Get recent maintenance tasks
        recent_tasks = MaintenanceTask.objects.select_related('initiated_by').order_by('-created_at')[:5]
        context['recent_tasks'] = recent_tasks
        
        # Get system alerts
        alerts = []
        
        # Check for critical system health issues
        if system_health.get('overall_score', 0) < 50:
            alerts.append({
                'type': 'error',
                'title': 'Critical System Health',
                'message': 'System health score is critically low. Immediate attention required.',
                'action_url': reverse('console:system_health')
            })
        
        # Check for pending verifications
        if stats['pending_verifications'] > 0:
            alerts.append({
                'type': 'warning',
                'title': 'Pending Verifications',
                'message': f"{stats['pending_verifications']} users awaiting verification.",
                'action_url': reverse('console:pending_managers')
            })
        
        # Check for failed maintenance tasks
        failed_tasks = MaintenanceTask.objects.filter(
            status='failed',
            created_at__gte=timezone.now() - timezone.timedelta(days=1)
        ).count()
        if failed_tasks > 0:
            alerts.append({
                'type': 'error',
                'title': 'Failed Maintenance Tasks',
                'message': f"{failed_tasks} maintenance tasks failed in the last 24 hours.",
                'action_url': reverse('console:maintenance')
            })
        
        context['alerts'] = alerts
        
        # Get emergency mode status
        settings_instance = SystemSettings.get_instance()
        context['emergency_mode'] = settings_instance.emergency_mode
        context['maintenance_mode'] = settings_instance.maintenance_mode
        
        return context


class AdminProfileView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Admin profile management view."""
    model = User
    form_class = AdminProfileForm
    template_name = 'console/profile.html'
    success_url = reverse_lazy('console:profile')
    
    def get_object(self):
        return self.request.user
    
    def form_valid(self, form):
        messages.success(self.request, "Profile updated successfully.")
        return super().form_valid(form)


class UserManagementView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """
    Main user management interface with DataGrid functionality.
    
    Provides filtering, searching, and bulk operations for user management.
    """
    model = User
    template_name = 'console/users.html'
    context_object_name = 'users'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = User.objects.all().order_by('-created_at')
        
        # Apply filters
        role_filter = self.request.GET.get('role')
        if role_filter and role_filter != 'all':
            queryset = queryset.filter(role=role_filter)
        
        status_filter = self.request.GET.get('status')
        # Default to showing active users only unless explicitly requested otherwise
        if status_filter == 'active' or (status_filter is None and not self.request.GET.get('show_all')):
            queryset = queryset.filter(is_active=True)
        elif status_filter == 'inactive':
            queryset = queryset.filter(is_active=False)
        elif status_filter == 'verified':
            queryset = queryset.filter(is_verified=True)
        elif status_filter == 'unverified':
            queryset = queryset.filter(is_verified=False)
        elif status_filter == 'all':
            # Show all users including inactive ones
            pass
        
        # Apply search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(email__icontains=search_query) |
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(full_name__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add filter options
        context['role_choices'] = UserRole.choices
        context['current_role'] = self.request.GET.get('role', 'all')
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_search'] = self.request.GET.get('search', '')
        
        # Get the base queryset with current filters applied
        filtered_queryset = self.get_queryset()
        
        # Add user statistics based on filtered results
        context['total_users'] = filtered_queryset.count()
        context['role_stats'] = {}
        
        # Calculate role statistics from filtered queryset
        for role_code, role_display in UserRole.choices:
            context['role_stats'][role_code] = filtered_queryset.filter(role=role_code).count()
        
        # Add overall statistics for reference
        context['overall_stats'] = {
            'all_users': User.objects.count(),
            'active_users': User.objects.filter(is_active=True).count(),
            'inactive_users': User.objects.filter(is_active=False).count(),
            'verified_users': User.objects.filter(is_verified=True).count(),
            'unverified_users': User.objects.filter(is_verified=False).count(),
        }
        
        return context


class UserCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new user account with admin privileges."""
    model = User
    form_class = AdminUserCreationForm
    template_name = 'console/user_form.html'
    success_url = reverse_lazy('console:users')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['created_by'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        user = form.save()
        
        # Set the verified_by field if is_verified is True
        if user.is_verified:
            user.verified_by = self.request.user
            user.save(update_fields=['verified_by'])
        
        # Log the user creation
        AuditLog.objects.create(
            user=self.request.user,
            action='user_created',
            description=f"Created user account for {user.email} with role {user.role}",
            metadata={
                'target_user_id': str(user.id),
                'target_user_email': user.email,
                'target_user_role': user.role
            }
        )
        
        messages.success(
            self.request,
            f"User account created successfully for {user.email}."
        )
        
        # Send notification to the new user
        from .managers import NotificationDispatcher
        dispatcher = NotificationDispatcher()
        dispatcher.send_verification_notification(user, 'account')
        
        return super().form_valid(form)


class UserEditView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Edit existing user account."""
    model = User
    form_class = AdminUserEditForm
    template_name = 'console/user_form.html'
    context_object_name = 'target_user'
    pk_url_kwarg = 'user_id'
    
    def get_success_url(self):
        return reverse('console:users')
    
    def form_valid(self, form):
        user = form.save()
        
        # Log the user update
        AuditLog.objects.create(
            user=self.request.user,
            action='user_updated',
            description=f"Updated user account for {user.email}",
            metadata={
                'target_user_id': str(user.id),
                'target_user_email': user.email,
                'changes': form.changed_data
            }
        )
        
        messages.success(
            self.request,
            f"User account updated successfully for {user.email}."
        )
        
        return super().form_valid(form)


class UserDeleteView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Deactivate user account with confirmation."""
    template_name = 'console/user_confirm_delete.html'
    
    def get(self, request, user_id):
        """Display confirmation page."""
        user = get_object_or_404(User, id=user_id)
        return render(request, self.template_name, {'target_user': user})
    
    def post(self, request, user_id):
        """Deactivate the user account."""
        user = get_object_or_404(User, id=user_id)
        
        # Prevent admin from deactivating themselves
        if user == request.user:
            messages.error(request, "You cannot deactivate your own account.")
            return redirect('console:users')
        
        # Deactivate the account instead of deleting
        user.is_active = False
        user.save(update_fields=['is_active'])
        
        # Log the user deactivation
        AuditLog.objects.create(
            user=request.user,
            action='user_deactivated',
            description=f"Deactivated user account for {user.email}",
            metadata={
                'target_user_id': str(user.id),
                'target_user_email': user.email,
                'target_user_role': user.role,
                'previous_status': 'active'
            }
        )
        
        messages.success(
            request,
            f"User account deactivated successfully for {user.email}. "
            f"The user can no longer log in to CommuMap."
        )
        
        return redirect('console:users')


class UserReactivateView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Reactivate a deactivated user account."""
    
    def post(self, request, user_id):
        """Reactivate the user account."""
        user = get_object_or_404(User, id=user_id)
        
        if user.is_active:
            messages.warning(request, f"User account for {user.email} is already active.")
            return redirect('console:users')
        
        # Reactivate the account
        user.is_active = True
        user.save(update_fields=['is_active'])
        
        # Log the user reactivation
        AuditLog.objects.create(
            user=request.user,
            action='user_reactivated',
            description=f"Reactivated user account for {user.email}",
            metadata={
                'target_user_id': str(user.id),
                'target_user_email': user.email,
                'target_user_role': user.role,
                'previous_status': 'inactive'
            }
        )
        
        messages.success(
            request,
            f"User account reactivated successfully for {user.email}. "
            f"The user can now log in to CommuMap."
        )
        
        return redirect('console:users')


class PendingManagersView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """View and manage pending service manager verifications."""
    model = User
    template_name = 'console/pending_managers.html'
    context_object_name = 'pending_managers'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(
            role=UserRole.SERVICE_MANAGER,
            is_verified=False,
            verification_requested_at__isnull=False
        ).order_by('verification_requested_at')


class PendingModeratorsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """View and manage pending community moderator verifications."""
    model = User
    template_name = 'console/pending_moderators.html'
    context_object_name = 'pending_moderators'
    paginate_by = 20
    
    def get_queryset(self):
        return User.objects.filter(
            role=UserRole.COMMUNITY_MODERATOR,
            is_verified=False,
            verification_requested_at__isnull=False
        ).order_by('verification_requested_at')


class VerifyUserView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Verify a pending user account."""
    
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            notes = request.POST.get('notes', '')
            
            # Verify the user
            user.verify_user(request.user, notes)
            
            # Log the verification action
            AuditLog.objects.create(
                user=request.user,
                action='user_verified',
                description=f"Verified user {user.email} with role {user.role}",
                metadata={
                    'target_user_id': str(user.id),
                    'target_user_email': user.email,
                    'target_user_role': user.role,
                    'notes': notes
                }
            )
            
            messages.success(
                request,
                f"User {user.email} verified successfully."
            )
            
            # Try to send notification but don't let it block the process
            try:
                from .managers import NotificationDispatcher
                dispatcher = NotificationDispatcher()
                dispatcher.send_verification_notification(user, 'role_change')
            except Exception as e:
                # Log the error but don't fail the verification
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send verification notification: {e}")
                messages.warning(
                    request,
                    "User verified successfully, but notification email could not be sent."
                )
            
            # Redirect based on user role
            if user.role == UserRole.SERVICE_MANAGER:
                return redirect('console:pending_managers')
            elif user.role == UserRole.COMMUNITY_MODERATOR:
                return redirect('console:pending_moderators')
            else:
                return redirect('console:users')
                
        except Exception as e:
            messages.error(
                request,
                f"Error verifying user: {str(e)}"
            )
            return redirect('console:users')


class RejectUserView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Reject a pending user verification."""
    
    def post(self, request, user_id):
        try:
            user = get_object_or_404(User, id=user_id)
            notes = request.POST.get('notes', 'Verification rejected by admin.')
            
            # Reject the verification
            user.reject_verification(request.user, notes)
            
            # Log the rejection action
            AuditLog.objects.create(
                user=request.user,
                action='user_verification_rejected',
                description=f"Rejected verification for user {user.email} with role {user.role}",
                metadata={
                    'target_user_id': str(user.id),
                    'target_user_email': user.email,
                    'target_user_role': user.role,
                    'notes': notes
                }
            )
            
            messages.warning(
                request,
                f"User {user.email} verification rejected."
            )
            
            # Try to send notification but don't let it block the process
            try:
                from .managers import NotificationDispatcher
                dispatcher = NotificationDispatcher()
                dispatcher.send_verification_notification(user, 'rejection')
            except Exception as e:
                # Log the error but don't fail the rejection
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Failed to send rejection notification: {e}")
            
            # Redirect based on user role
            if user.role == UserRole.SERVICE_MANAGER:
                return redirect('console:pending_managers')
            elif user.role == UserRole.COMMUNITY_MODERATOR:
                return redirect('console:pending_moderators')
            else:
                return redirect('console:users')
                
        except Exception as e:
            messages.error(
                request,
                f"Error rejecting user verification: {str(e)}"
            )
            return redirect('console:users')


# Service Management Views

class ServiceManagementView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Enhanced admin service management interface with advanced filtering and bulk actions."""
    model = Service
    template_name = 'console/services.html'
    context_object_name = 'services'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = Service.objects.select_related('manager', 'category').order_by('-created_at')
        
        # Apply advanced filters from ServiceSearchForm
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search) |
                Q(short_description__icontains=search) |
                Q(manager__email__icontains=search) |
                Q(manager__first_name__icontains=search) |
                Q(manager__last_name__icontains=search) |
                Q(address__icontains=search)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status:
            queryset = queryset.filter(current_status=status)
        
        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        # Verification status filter
        verification_status = self.request.GET.get('verification_status')
        if verification_status == 'verified':
            queryset = queryset.filter(is_verified=True)
        elif verification_status == 'unverified':
            queryset = queryset.filter(is_verified=False)
        
        # Active status filter
        active_status = self.request.GET.get('active_status')
        if active_status == 'active':
            queryset = queryset.filter(is_active=True)
        elif active_status == 'inactive':
            queryset = queryset.filter(is_active=False)
        
        # Emergency services filter
        if self.request.GET.get('emergency_services'):
            queryset = queryset.filter(is_emergency_service=True)
        
        # Manager filter
        has_manager = self.request.GET.get('has_manager')
        if has_manager == 'yes':
            queryset = queryset.filter(manager__isnull=False)
        elif has_manager == 'no':
            queryset = queryset.filter(manager__isnull=True)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add search form
        from .forms import ServiceSearchForm, BulkServiceActionForm
        context['search_form'] = ServiceSearchForm(self.request.GET)
        context['bulk_action_form'] = BulkServiceActionForm()
        
        # Service statistics
        context['stats'] = {
            'total_services': Service.objects.count(),
            'active_services': Service.objects.filter(is_active=True).count(),
            'verified_services': Service.objects.filter(is_verified=True).count(),
            'pending_services': Service.objects.filter(is_verified=False).count(),
            'emergency_services': Service.objects.filter(is_emergency_service=True).count(),
            'unassigned_services': Service.objects.filter(manager__isnull=True).count(),
        }
        
        # Categories for quick filtering
        context['categories'] = ServiceCategory.objects.filter(is_active=True).order_by('name')
        
        return context


class AdminServiceEditView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Enhanced admin service editing interface with comprehensive content management."""
    model = Service
    template_name = 'console/service_edit.html'
    pk_url_kwarg = 'service_id'
    
    def get_form_class(self):
        from .forms import AdminServiceForm
        return AdminServiceForm
    
    def get_success_url(self):
        return reverse('console:services')
    
    def form_valid(self, form):
        service = form.save()
        
        # Log the service update
        AuditLog.objects.create(
            user=self.request.user,
            action='service_updated',
            description=f"Updated service: {service.name}",
            metadata={
                'service_id': str(service.id),
                'service_name': service.name,
                'changes': form.changed_data
            }
        )
        
        messages.success(self.request, f"Service '{service.name}' updated successfully.")
        return super().form_valid(form)


class EmergencyToggleView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Emergency toggle for services."""
    
    def post(self, request, service_id):
        service = get_object_or_404(Service, id=service_id)
        service.is_emergency_service = not service.is_emergency_service
        service.save()
        
        # Log the emergency toggle
        action = 'emergency_enabled' if service.is_emergency_service else 'emergency_disabled'
        AuditLog.objects.create(
            user=request.user,
            action=action,
            description=f"Emergency status toggled for service: {service.name}",
            metadata={
                'service_id': str(service.id),
                'service_name': service.name,
                'emergency_status': service.is_emergency_service
            }
        )
        
        status = "enabled" if service.is_emergency_service else "disabled"
        messages.success(request, f"Emergency status {status} for '{service.name}'.")
        
        return redirect('console:services')
    
    def get(self, request, service_id):
        """Handle GET requests by redirecting to services page."""
        messages.info(request, "Emergency toggle requires POST request.")
        return redirect('console:services')


class AdminServiceCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Admin service creation interface."""
    model = Service
    template_name = 'console/service_create.html'
    
    def get_form_class(self):
        from .forms import AdminServiceForm
        return AdminServiceForm
    
    def get_success_url(self):
        return reverse('console:services')
    
    def form_valid(self, form):
        service = form.save()
        
        # Log the service creation
        AuditLog.objects.create(
            user=self.request.user,
            action='service_created',
            description=f"Created service: {service.name}",
            metadata={
                'service_id': str(service.id),
                'service_name': service.name,
                'manager_id': str(service.manager.id) if service.manager else None
            }
        )
        
        messages.success(self.request, f"Service '{service.name}' created successfully.")
        return super().form_valid(form)


class AdminServiceDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Admin service deletion with confirmation."""
    model = Service
    template_name = 'console/service_confirm_delete.html'
    pk_url_kwarg = 'service_id'
    success_url = reverse_lazy('console:services')
    
    def delete(self, request, *args, **kwargs):
        service = self.get_object()
        
        # Log the service deletion
        AuditLog.objects.create(
            user=request.user,
            action='service_deleted',
            description=f"Deleted service: {service.name}",
            metadata={
                'service_id': str(service.id),
                'service_name': service.name,
                'manager_email': service.manager.email if service.manager else None
            }
        )
        
        messages.success(request, f"Service '{service.name}' deleted successfully.")
        return super().delete(request, *args, **kwargs)


class BulkServiceActionView(LoginRequiredMixin, AdminRequiredMixin, View):
    """Handle bulk actions on services."""
    
    def post(self, request):
        from .forms import BulkServiceActionForm
        form = BulkServiceActionForm(request.POST)
        
        if form.is_valid():
            action = form.cleaned_data['action']
            service_ids = form.cleaned_data['service_ids'].split(',')
            
            # Get services to process
            services = Service.objects.filter(id__in=service_ids)
            processed_count = services.count()
            
            if processed_count == 0:
                messages.error(request, "No services selected for bulk action.")
                return redirect('console:services')
            
            # Process bulk action
            if action == 'verify':
                services.update(is_verified=True, verified_by=request.user, verified_at=timezone.now())
                messages.success(request, f"Verified {processed_count} services.")
                
            elif action == 'unverify':
                services.update(is_verified=False, verified_by=None, verified_at=None)
                messages.success(request, f"Removed verification from {processed_count} services.")
                
            elif action == 'activate':
                services.update(is_active=True)
                messages.success(request, f"Activated {processed_count} services.")
                
            elif action == 'deactivate':
                services.update(is_active=False)
                messages.success(request, f"Deactivated {processed_count} services.")
                
            elif action == 'emergency_on':
                services.update(is_emergency_service=True)
                messages.success(request, f"Enabled emergency status for {processed_count} services.")
                
            elif action == 'emergency_off':
                services.update(is_emergency_service=False)
                messages.success(request, f"Disabled emergency status for {processed_count} services.")
                
            elif action == 'change_status':
                new_status = form.cleaned_data['new_status']
                services.update(current_status=new_status, status_updated_by=request.user)
                messages.success(request, f"Changed status to '{new_status}' for {processed_count} services.")
                
            elif action == 'change_category':
                new_category = form.cleaned_data['new_category']
                services.update(category=new_category)
                messages.success(request, f"Changed category to '{new_category}' for {processed_count} services.")
                
            elif action == 'delete':
                service_names = list(services.values_list('name', flat=True))
                services.delete()
                messages.success(request, f"Deleted {processed_count} services: {', '.join(service_names[:5])}")
            
            # Log bulk action
            AuditLog.objects.create(
                user=request.user,
                action=f'bulk_service_{action}',
                description=f"Bulk {action} on {processed_count} services",
                metadata={
                    'action': action,
                    'service_count': processed_count,
                    'service_ids': service_ids
                }
            )
        
        else:
            messages.error(request, "Invalid bulk action form.")
        
        return redirect('console:services')


# System Announcements

class AnnouncementView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """System announcements management."""
    model = SystemAnnouncement
    template_name = 'console/announcements.html'
    context_object_name = 'announcements'
    paginate_by = 20
    
    def get_queryset(self):
        return SystemAnnouncement.objects.select_related('created_by').order_by('-created_at')


class AnnouncementCreateView(LoginRequiredMixin, AdminRequiredMixin, CreateView):
    """Create new system announcement."""
    model = SystemAnnouncement
    form_class = SystemAnnouncementForm
    template_name = 'console/announcement_form.html'
    success_url = reverse_lazy('console:announcements')
    
    def form_valid(self, form):
        announcement = form.save(commit=False)
        announcement.created_by = self.request.user
        announcement.save()
        
        # Log the announcement creation
        AuditLog.objects.create(
            user=self.request.user,
            action='announcement_created',
            description=f"Created announcement: {announcement.title}",
            metadata={
                'announcement_id': str(announcement.id),
                'title': announcement.title,
                'type': announcement.announcement_type
            }
        )
        
        # Send notifications if urgent
        if announcement.is_urgent:
            dispatcher = NotificationDispatcher()
            dispatcher.send_system_announcement(announcement)
        
        messages.success(self.request, "Announcement created successfully.")
        return super().form_valid(form)


class AnnouncementEditView(LoginRequiredMixin, AdminRequiredMixin, UpdateView):
    """Edit system announcement."""
    model = SystemAnnouncement
    form_class = SystemAnnouncementForm
    template_name = 'console/announcement_form.html'
    pk_url_kwarg = 'announcement_id'
    success_url = reverse_lazy('console:announcements')
    
    def form_valid(self, form):
        announcement = form.save()
        
        # Log the announcement update
        AuditLog.objects.create(
            user=self.request.user,
            action='announcement_updated',
            description=f"Updated announcement: {announcement.title}",
            metadata={
                'announcement_id': str(announcement.id),
                'title': announcement.title,
                'changes': form.changed_data
            }
        )
        
        messages.success(self.request, "Announcement updated successfully.")
        return super().form_valid(form)


class AnnouncementDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete system announcement."""
    model = SystemAnnouncement
    template_name = 'console/announcement_confirm_delete.html'
    pk_url_kwarg = 'announcement_id'
    success_url = reverse_lazy('console:announcements')
    
    def delete(self, request, *args, **kwargs):
        announcement = self.get_object()
        
        # Log the announcement deletion
        AuditLog.objects.create(
            user=request.user,
            action='announcement_deleted',
            description=f"Deleted announcement: {announcement.title}",
            metadata={
                'announcement_id': str(announcement.id),
                'title': announcement.title
            }
        )
        
        messages.success(request, "Announcement deleted successfully.")
        return super().delete(request, *args, **kwargs)


# Maintenance Tools

class MaintenanceToolsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Maintenance tools dashboard."""
    template_name = 'console/maintenance.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Recent maintenance tasks
        context['recent_tasks'] = MaintenanceTask.objects.select_related(
            'initiated_by'
        ).order_by('-created_at')[:10]
        
        # Maintenance statistics
        context['stats'] = {
            'total_tasks': MaintenanceTask.objects.count(),
            'running_tasks': MaintenanceTask.objects.filter(status='running').count(),
            'completed_tasks': MaintenanceTask.objects.filter(status='completed').count(),
            'failed_tasks': MaintenanceTask.objects.filter(status='failed').count(),
        }
        
        return context


class BackupDatabaseView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Database backup operation."""
    
    def post(self, request):
        try:
            maintenance = MaintenanceOperations()
            task = maintenance.backup_database(request.user)
            
            messages.success(request, "Database backup initiated successfully.")
            
        except Exception as e:
            messages.error(request, f"Database backup failed: {str(e)}")
        
        return redirect('console:maintenance')


class ClearCacheView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Cache clearing operation."""
    
    def post(self, request):
        try:
            maintenance = MaintenanceOperations()
            task = maintenance.clear_cache(request.user)
            
            messages.success(request, "Cache cleared successfully.")
            
        except Exception as e:
            messages.error(request, f"Cache clearing failed: {str(e)}")
        
        return redirect('console:maintenance')


class LogRotationView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Log rotation operation."""
    
    def post(self, request):
        try:
            maintenance = MaintenanceOperations()
            task = maintenance.rotate_logs(request.user)
            
            messages.success(request, "Log rotation initiated successfully.")
            
        except Exception as e:
            messages.error(request, f"Log rotation failed: {str(e)}")
        
        return redirect('console:maintenance')


class FeatureToggleView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Feature toggle management."""
    template_name = 'console/feature_toggle.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        settings_loader = SettingsLoader()
        context['features'] = settings_loader.get_feature_flags()
        return context
    
    def post(self, request):
        feature_name = request.POST.get('feature_name')
        enabled = request.POST.get('enabled') == 'true'
        
        try:
            maintenance = MaintenanceOperations()
            task = maintenance.toggle_feature(request.user, feature_name, enabled)
            
            status = "enabled" if enabled else "disabled"
            messages.success(request, f"Feature '{feature_name}' {status} successfully.")
            
        except Exception as e:
            messages.error(request, f"Feature toggle failed: {str(e)}")
        
        return redirect('console:feature_toggle')


class DataCleanupView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Data cleanup operation."""
    
    def post(self, request):
        try:
            maintenance = MaintenanceOperations()
            task = maintenance.cleanup_old_data(request.user)
            
            messages.success(request, "Data cleanup initiated successfully.")
            
        except Exception as e:
            messages.error(request, f"Data cleanup failed: {str(e)}")
        
        return redirect('console:maintenance')


# Feedback Management

class AdminFeedbackView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin feedback management interface."""
    model = ServiceReview
    template_name = 'console/feedback.html'
    context_object_name = 'feedback_list'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = ServiceReview.objects.select_related('user', 'service').order_by('-created_at')
        
        # Apply filters
        status_filter = self.request.GET.get('status')
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        # Apply search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(content__icontains=search_query) |
                Q(service__name__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_status'] = self.request.GET.get('status', 'all')
        context['current_search'] = self.request.GET.get('search', '')
        return context


class FeedbackReplyView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Reply to feedback."""
    
    def post(self, request, feedback_id):
        feedback = get_object_or_404(ServiceReview, id=feedback_id)
        reply_content = request.POST.get('reply_content')
        
        if reply_content:
            # Create admin reply as a comment
            reply = ServiceComment.objects.create(
                service=feedback.service,
                user=request.user,
                content=f"Admin Response: {reply_content}",
                is_approved=True
            )
            
            # Log the reply
            AuditLog.objects.create(
                user=request.user,
                action='feedback_replied',
                description=f"Replied to review from {feedback.user.email}",
                metadata={
                    'review_id': str(feedback.id),
                    'service_name': feedback.service.name,
                    'reply_id': str(reply.id)
                }
            )
            
            # Send notification to user
            dispatcher = NotificationDispatcher()
            dispatcher.send_review_reply_notification(feedback, reply)
            
            messages.success(request, "Reply posted successfully.")
        else:
            messages.error(request, "Reply content is required.")
        
        return redirect('console:feedback')


class AdminCommentsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Admin comments management interface."""
    model = ServiceComment
    template_name = 'console/comments.html'
    context_object_name = 'comments'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = ServiceComment.objects.select_related('user', 'service').order_by('-created_at')
        
        # Apply search
        search_query = self.request.GET.get('search')
        if search_query:
            queryset = queryset.filter(
                Q(content__icontains=search_query) |
                Q(user__email__icontains=search_query)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['current_search'] = self.request.GET.get('search', '')
        return context


class CommentReplyView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Reply to comment."""
    
    def post(self, request, comment_id):
        comment = get_object_or_404(ServiceComment, id=comment_id)
        reply_content = request.POST.get('reply_content')
        
        if reply_content:
            # Create admin reply
            reply = ServiceComment.objects.create(
                service=comment.service,
                user=request.user,
                content=reply_content,
                parent=comment
            )
            
            # Log the reply
            AuditLog.objects.create(
                user=request.user,
                action='comment_replied',
                description=f"Replied to comment from {comment.user.email}",
                metadata={
                    'comment_id': str(comment.id),
                    'reply_id': str(reply.id)
                }
            )
            
            messages.success(request, "Reply posted successfully.")
        else:
            messages.error(request, "Reply content is required.")
        
        return redirect('console:comments')


class CommentDeleteView(LoginRequiredMixin, AdminRequiredMixin, DeleteView):
    """Delete comment."""
    model = ServiceComment
    template_name = 'console/comment_confirm_delete.html'
    pk_url_kwarg = 'comment_id'
    success_url = reverse_lazy('console:comments')
    
    def delete(self, request, *args, **kwargs):
        comment = self.get_object()
        
        # Log the comment deletion
        AuditLog.objects.create(
            user=request.user,
            action='comment_deleted',
            description=f"Deleted comment from {comment.user.email}",
            metadata={
                'comment_id': str(comment.id),
                'user_email': comment.user.email
            }
        )
        
        messages.success(request, "Comment deleted successfully.")
        return super().delete(request, *args, **kwargs)


# System Monitoring

class SystemHealthView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """System health monitoring dashboard."""
    template_name = 'console/system_health.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get comprehensive system health
        system_health = SystemMonitor.get_system_overview()
        context['system_health'] = system_health
        
        # Get detailed metrics
        context['detailed_metrics'] = {
            'database': SystemMonitor.check_database_health(),
            'cache': SystemMonitor.check_cache_health(),
            'disk': SystemMonitor.check_disk_usage(),
            'memory': SystemMonitor.check_memory_usage(),
            'application': SystemMonitor.get_application_metrics(),
        }
        
        # Recent system metrics
        context['recent_metrics'] = SystemMetrics.objects.order_by('-recorded_at')[:24]
        
        return context


class SystemMetricsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """System metrics API endpoint."""
    
    def get(self, request):
        metrics = SystemMonitor.get_system_overview()
        return JsonResponse(metrics)


class AuditLogsView(LoginRequiredMixin, AdminRequiredMixin, ListView):
    """Audit logs management."""
    model = AuditLog
    template_name = 'console/audit_logs.html'
    context_object_name = 'logs'
    paginate_by = 50
    
    def get_queryset(self):
        queryset = AuditLog.objects.select_related('user').order_by('-created_at')
        
        # Apply filters
        action_filter = self.request.GET.get('action')
        if action_filter:
            queryset = queryset.filter(action=action_filter)
        
        user_filter = self.request.GET.get('user')
        if user_filter:
            queryset = queryset.filter(user__email__icontains=user_filter)
        
        # Date range filter
        date_from = self.request.GET.get('date_from')
        date_to = self.request.GET.get('date_to')
        if date_from:
            queryset = queryset.filter(created_at__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__lte=date_to)
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Available actions for filtering
        context['available_actions'] = AuditLog.objects.values_list(
            'action', flat=True
        ).distinct().order_by('action')
        
        context['current_action'] = self.request.GET.get('action', '')
        context['current_user'] = self.request.GET.get('user', '')
        context['current_date_from'] = self.request.GET.get('date_from', '')
        context['current_date_to'] = self.request.GET.get('date_to', '')
        
        return context


# Emergency Mode

class EmergencyModeToggleView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    template_name = 'console/emergency_toggle.html'
    """Toggle emergency mode."""
    
    def post(self, request):
        settings_instance = SystemSettings.get_instance()
        settings_instance.emergency_mode = not settings_instance.emergency_mode
        settings_instance.save()
        
        # Log the emergency mode toggle
        action = 'emergency_mode_enabled' if settings_instance.emergency_mode else 'emergency_mode_disabled'
        AuditLog.objects.create(
            user=request.user,
            action=action,
            description=f"Emergency mode {'enabled' if settings_instance.emergency_mode else 'disabled'}",
            metadata={'emergency_mode': settings_instance.emergency_mode}
        )
        
        # Send urgent notification to all admins
        if settings_instance.emergency_mode:
            dispatcher = NotificationDispatcher()
            dispatcher.send_emergency_alert(
                "Emergency Mode Activated",
                f"Emergency mode has been activated by {request.user.get_display_name()}",
                request.user
            )
        
        status = "activated" if settings_instance.emergency_mode else "deactivated"
        messages.warning(request, f"Emergency mode {status}.")
        
        return redirect('console:dashboard')


# Settings Management

class SystemSettingsView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """System settings management."""
    template_name = 'console/settings.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        settings_loader = SettingsLoader()
        context['settings'] = settings_loader.get_all_settings()
        context['feature_flags'] = settings_loader.get_all_feature_flags()
        
        return context
    
    def post(self, request):
        settings_loader = SettingsLoader()
        
        # Update settings
        for key, value in request.POST.items():
            if key.startswith('setting_'):
                setting_name = key[8:]  # Remove 'setting_' prefix
                settings_loader.update_setting(setting_name, value)
        
        # Log settings update
        AuditLog.objects.create(
            user=request.user,
            action='settings_updated',
            description="System settings updated",
            metadata={'updated_settings': list(request.POST.keys())}
        )
        
        messages.success(request, "Settings updated successfully.")
        return redirect('console:settings')


class SettingsBackupView(LoginRequiredMixin, AdminRequiredMixin, TemplateView):
    """Settings backup and restore."""
    
    def post(self, request):
        action = request.POST.get('action')
        
        try:
            settings_loader = SettingsLoader()
            
            if action == 'backup':
                backup_data = settings_loader.backup_settings()
                
                # Create downloadable backup file
                response = HttpResponse(
                    json.dumps(backup_data, indent=2),
                    content_type='application/json'
                )
                response['Content-Disposition'] = f'attachment; filename="settings_backup_{timezone.now().strftime("%Y%m%d_%H%M%S")}.json"'
                
                # Log backup creation
                AuditLog.objects.create(
                    user=request.user,
                    action='settings_backup_created',
                    description="Settings backup created",
                    metadata={'backup_timestamp': timezone.now().isoformat()}
                )
                
                return response
                
            elif action == 'restore':
                backup_file = request.FILES.get('backup_file')
                if backup_file:
                    backup_data = json.loads(backup_file.read().decode('utf-8'))
                    settings_loader.restore_settings(backup_data)
                    
                    # Log restore
                    AuditLog.objects.create(
                        user=request.user,
                        action='settings_restored',
                        description="Settings restored from backup",
                        metadata={'backup_file': backup_file.name}
                    )
                    
                    messages.success(request, "Settings restored successfully.")
                else:
                    messages.error(request, "No backup file provided.")
                    
        except Exception as e:
            messages.error(request, f"Operation failed: {str(e)}")
        
        return redirect('console:settings')
