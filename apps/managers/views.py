"""
Views for Service Manager functionality.

This module implements all the views for Service Manager dashboard,
service management, analytics, and real-time status updates.
"""
from typing import Dict, Any, List
import json
import random
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, 
    UpdateView, DeleteView, FormView, View
)
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
from django.urls import reverse_lazy, reverse
from django.core.paginator import Paginator
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal

from apps.core.models import User, UserRole
from apps.services.models import Service, ServiceCategory, ServiceAlert
from .forms import ServiceForm, ManagerProfileForm
from apps.feedback.models import ServiceReview, ServiceComment
from apps.managers.models import (
    ServiceAnalytics, ManagerNotification, ServiceStatusHistory
)
from apps.managers.strategies import ServiceSearchContext
from apps.managers.factories import ServiceFactory, ServiceAlertFactory, NotificationFactory


class RoleRequiredMixin:
    """Mixin to require specific user roles."""
    required_roles = [UserRole.SERVICE_MANAGER, UserRole.ADMIN]
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('core:login')
        
        if request.user.role not in self.required_roles:
            messages.error(request, "You don't have permission to access this page.")
            return redirect('core:landing')
        
        if not request.user.is_verified and request.user.role == UserRole.SERVICE_MANAGER:
            messages.warning(request, "Your account is pending verification.")
            return redirect('core:landing')
        
        return super().dispatch(request, *args, **kwargs)


class ManagerHomeView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Service Manager home page with overview and quick access to features.
    
    This is the landing page for Service Managers, showing statistics
    and providing easy access to key functionality.
    """
    template_name = 'managers/home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.request.user
        
        # Get manager's services
        services = Service.objects.filter(manager=manager)
        
        # Calculate statistics
        total_feedback = ServiceReview.objects.filter(service__manager=manager).count()
        avg_rating = services.aggregate(avg_rating=Avg('quality_score'))['avg_rating'] or 0
        
        context.update({
            'manager_stats': {
                'total_services': services.count(),
                'total_visits': sum(service.total_ratings for service in services),  # Approximation
                'avg_rating': avg_rating,
                'people_helped': total_feedback * 3,  # Estimation
            },
            'recent_services': services.order_by('-updated_at')[:3],
        })
        
        return context


class ManagerDashboardView(LoginRequiredMixin, RoleRequiredMixin, TemplateView):
    """
    Service Manager Dashboard with KPI tiles and service overview.
    
    Displays key metrics, notifications, and quick access to
    service management functions.
    """
    template_name = 'managers/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.request.user
        
        # Get manager's services
        services = Service.objects.filter(manager=manager)
        
        # Calculate KPIs
        context.update({
            'total_services': services.count(),
            'open_services': services.filter(current_status='open').count(),
            'services_near_capacity': services.filter(
                current_capacity__gte=80,
                max_capacity__gt=0
            ).count(),
            'avg_rating': services.aggregate(avg_rating=Avg('quality_score'))['avg_rating'] or 0,
            'total_feedback': ServiceReview.objects.filter(service__manager=manager).count(),
            'recent_services': services.order_by('-updated_at')[:5],
            'unread_notifications': ManagerNotification.objects.filter(
                manager=manager, is_read=False
            ).count(),
            'recent_notifications': ManagerNotification.objects.filter(
                manager=manager
            ).order_by('-created_at')[:5],
        })
        
        return context


class ManagerProfileView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Manager profile management view with form handling."""
    model = User
    form_class = ManagerProfileForm
    template_name = 'managers/profile.html'
    context_object_name = 'manager'
    
    def get_object(self):
        # Always get a fresh instance from the database to avoid any state issues
        return User.objects.get(pk=self.request.user.pk)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.get_object()
        
        # Get manager's services statistics
        services = Service.objects.filter(manager=manager)
        total_feedback = ServiceReview.objects.filter(service__manager=manager).count()
        
        context.update({
            'manager_stats': {
                'services_managed': services.count(),
                'total_feedback': total_feedback,
                'avg_rating': services.aggregate(avg_rating=Avg('quality_score'))['avg_rating'] or 0,
                'people_helped': total_feedback * 3,  # Estimation
            },
            'recent_services': services.order_by('-updated_at')[:3],
        })
        
        return context
    
    def form_valid(self, form):
        # Store original is_verified value to prevent accidental modification
        original_user = User.objects.get(pk=self.request.user.pk)
        original_is_verified = original_user.is_verified
        
        # Ensure form instance has correct is_verified value
        form.instance.is_verified = original_is_verified
        
        response = super().form_valid(form)
        
        # Double-check that is_verified wasn't changed
        self.object.refresh_from_db()
        if self.object.is_verified != original_is_verified:
            self.object.is_verified = original_is_verified
            self.object.save(update_fields=['is_verified'])
        
        messages.success(self.request, 'Profile updated successfully!')
        return response
    
    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def get_success_url(self):
        return reverse('manager:profile')


class ManagerServicesView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    My Services view with filtering and search capabilities.
    
    Shows all services managed by the current user with
    status indicators and action buttons.
    """
    template_name = 'managers/services.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Service.objects.filter(manager=self.request.user).select_related('category')
        
        # Apply search and filters
        search_params = self.get_search_params()
        if search_params:
            search_context = ServiceSearchContext()
            queryset = search_context.search(queryset, search_params)
        
        return queryset.order_by('-updated_at')
    
    def get_search_params(self) -> Dict[str, Any]:
        """Extract search parameters from request."""
        params = {}
        
        # Text search
        if self.request.GET.get('q'):
            params['query'] = self.request.GET['q']
        
        # Status filter
        if self.request.GET.get('status'):
            params['status'] = self.request.GET['status']
        
        # Category filter
        if self.request.GET.get('category'):
            params['category'] = self.request.GET['category']
        
        # Approval status filter
        if self.request.GET.get('approval_status'):
            params['approval_status'] = self.request.GET['approval_status']
        
        # Special filters
        if self.request.GET.get('needs_attention'):
            params['needs_attention'] = True
        
        return params
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager = self.request.user
        
        # Get service counts by status
        all_services = Service.objects.filter(manager=manager)
        pending_services = all_services.filter(is_verified=False)
        verified_services = all_services.filter(is_verified=True)
        
        context.update({
            'categories': ServiceCategory.objects.filter(is_active=True),
            'search_params': self.get_search_params(),
            'service_counts': {
                'total': all_services.count(),
                'pending': pending_services.count(),
                'verified': verified_services.count(),
                'open': verified_services.filter(current_status='open').count(),
                'closed': verified_services.filter(current_status='closed').count(),
            },
            'pending_services': pending_services.order_by('-created_at')[:5],
        })
        return context


class ServiceCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """Service creation view with multi-step form."""
    model = Service
    form_class = ServiceForm
    template_name = 'managers/service_form.html'
    
    def form_valid(self, form):
        form.instance.manager = self.request.user
        form.instance.is_verified = False  # Requires moderator approval
        
        # Set default values for required fields if missing
        if not form.instance.country:
            form.instance.country = 'Malaysia'
        if not form.instance.current_capacity:
            form.instance.current_capacity = 0
        if not form.instance.quality_score:
            form.instance.quality_score = Decimal('0.00')
        if not form.instance.total_ratings:
            form.instance.total_ratings = 0
        
        # Set default coordinates if not provided (Cyberjaya, Malaysia)
        if not form.instance.latitude:
            form.instance.latitude = 2.9152
        if not form.instance.longitude:
            form.instance.longitude = 101.6515
        
        # Save the service first
        response = super().form_valid(form)
        
        # Create notifications for all active community moderators
        self._create_moderator_notifications(self.object)
            
        messages.success(self.request, 
            'Service created successfully! Your service is now pending approval by moderators and will be visible to the public once approved.')
        return response
    
    def form_invalid(self, form):
        """Handle form validation errors."""
        # Add each field error to messages for easier debugging
        for field, errors in form.errors.items():
            for error in errors:
                messages.error(self.request, f'{field}: {error}')
        
        # Add non-field errors
        for error in form.non_field_errors():
            messages.error(self.request, f'Form Error: {error}')
            
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)
    
    def _create_moderator_notifications(self, service):
        """Create notifications for all community moderators about new service."""
        from apps.core.models import UserRole
        from apps.moderators.models import ModeratorNotification
        
        # Get all active community moderators
        moderators = User.objects.filter(
            role=UserRole.COMMUNITY_MODERATOR,
            is_active=True,
            is_verified=True
        )
        
        # Create action URL for the service approval queue
        action_url = f"/moderators/services/pending/"
        
        # Create notification for each moderator
        notifications = []
        for moderator in moderators:
            notification = ModeratorNotification(
                moderator=moderator,
                notification_type='new_service_submitted',
                title=f'New Service Submitted: {service.name}',
                message=f'Service manager {service.manager.get_display_name()} has submitted a new service "{service.name}" for approval. Category: {service.category.name if service.category else "Not specified"}.',
                priority='normal',
                related_service=service,
                action_url=action_url
            )
            notifications.append(notification)
        
        # Bulk create notifications for efficiency
        if notifications:
            ModeratorNotification.objects.bulk_create(notifications)

    def get_success_url(self):
        return reverse('manager:services')


class ServiceUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """Service editing view."""
    model = Service
    form_class = ServiceForm
    template_name = 'managers/service_form.html'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, 'Service updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('manager:services')


class ServiceDeleteView(LoginRequiredMixin, RoleRequiredMixin, DeleteView):
    """Service deletion view."""
    model = Service
    template_name = 'managers/service_confirm_delete.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        service = self.get_object()
        service_name = service.name
        response = super().delete(request, *args, **kwargs)
        messages.success(request, f'Service "{service_name}" has been deleted successfully.')
        return response
    
    def get_success_url(self):
        return reverse('manager:services')


class ServiceStatusView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Real-time status management view."""
    model = Service
    template_name = 'managers/status_panel.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        context.update({
            'recent_status_history': ServiceStatusHistory.objects.filter(
                service=service
            ).order_by('-created_at')[:10],
            'active_alerts': ServiceAlert.objects.filter(
                service=service, is_active=True
            ).order_by('-priority', '-created_at'),
        })
        
        return context


class ServiceAnalyticsView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Service analytics view with charts and reports."""
    model = Service
    template_name = 'managers/analytics.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        # Get date range from request
        days = int(self.request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get analytics data
        analytics = ServiceAnalytics.objects.filter(
            service=service,
            date__range=[start_date, end_date]
        ).order_by('date')
        
        # Get feedback statistics
        feedback_stats = ServiceReview.objects.filter(
            service=service,
            created_at__range=[start_date, timezone.now()]
        ).aggregate(
            total_feedback=Count('id'),
            avg_rating=Avg('rating')
        )
        
        context.update({
            'analytics_data': analytics,
            'feedback_stats': feedback_stats,
            'date_range': {
                'start': start_date,
                'end': end_date,
                'days': days
            }
        })
        
        return context


class GenerateReportView(LoginRequiredMixin, RoleRequiredMixin, View):
    """Generate CSV/PDF reports for service analytics."""
    
    def get(self, request, pk):
        service = get_object_or_404(Service, pk=pk, manager=request.user)
        
        # Get parameters
        format_type = request.GET.get('format', 'csv')
        period = request.GET.get('period', '7')
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        
        try:
            period_days = int(period)
        except (ValueError, TypeError):
            period_days = 7
        
        # Calculate date range
        if from_date and to_date:
            try:
                start_date = datetime.strptime(from_date, '%Y-%m-%d').date()
                end_date = datetime.strptime(to_date, '%Y-%m-%d').date()
            except ValueError:
                end_date = timezone.now().date()
                start_date = end_date - timedelta(days=period_days)
        else:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=period_days)
        
        # Generate mock analytics data for the date range
        analytics_data = []
        current_date = start_date
        while current_date <= end_date:
            analytics_data.append({
                'date': current_date,
                'visits': random.randint(10, 100),
                'new_reviews': random.randint(0, 10),
                'avg_rating': round(random.uniform(3.5, 5.0), 1),
                'peak_capacity': random.randint(40, 100),
                'status_changes': random.randint(0, 5),
            })
            current_date += timedelta(days=1)
        
        if format_type == 'csv':
            return self.generate_csv_report(service, analytics_data)
        elif format_type == 'pdf':
            return self.generate_pdf_report(service, analytics_data)
        else:
            return JsonResponse({'error': 'Invalid format'}, status=400)
    
    def generate_csv_report(self, service, analytics_data):
        """Generate CSV report."""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{service.slug}_analytics_report.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Date', 'Visits', 'New Reviews', 'Avg Rating', 'Peak Capacity %', 'Status Changes'])
        
        for data in analytics_data:
            writer.writerow([
                data['date'].strftime('%Y-%m-%d'),
                data['visits'],
                data['new_reviews'],
                data['avg_rating'],
                data['peak_capacity'],
                data['status_changes']
            ])
        
        return response
    
    def generate_pdf_report(self, service, analytics_data):
        """Generate PDF report."""
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        
        # For now, return a simple text-based PDF response
        # In production, you'd use libraries like ReportLab or WeasyPrint
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{service.slug}_analytics_report.pdf"'
        
        # Simple text-based PDF content (replace with actual PDF generation)
        pdf_content = f"""
Service Analytics Report

Service: {service.name}
Address: {service.address}
Manager: {service.manager.full_name or service.manager.email}
Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

Analytics Data:
Date       | Visits | Reviews | Rating | Capacity | Changes
-----------|--------|---------|--------|----------|--------
"""
        
        for data in analytics_data:
            pdf_content += f"{data['date'].strftime('%Y-%m-%d')} | {data['visits']:6} | {data['new_reviews']:7} | {data['avg_rating']:6} | {data['peak_capacity']:8}% | {data['status_changes']:7}\n"
        
        pdf_content += f"""

Summary:
- Total Visits: {sum(data['visits'] for data in analytics_data)}
- Average Rating: {sum(data['avg_rating'] for data in analytics_data) / len(analytics_data):.1f}
- Total Reviews: {sum(data['new_reviews'] for data in analytics_data)}
- Average Capacity: {sum(data['peak_capacity'] for data in analytics_data) / len(analytics_data):.1f}%

Note: This is a simplified PDF. For production use, implement proper PDF generation.
"""
        
        response.write(pdf_content.encode('utf-8'))
        return response


class ServiceFeedbackView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Service feedback management view."""
    model = Service
    template_name = 'managers/feedback.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        # Get paginated feedback
        feedback_list = ServiceReview.objects.filter(
            service=service
        ).order_by('-created_at')
        
        paginator = Paginator(feedback_list, 20)
        page = self.request.GET.get('page')
        feedback = paginator.get_page(page)
        
        context['feedback'] = feedback
        return context


class ServiceCommentsView(LoginRequiredMixin, RoleRequiredMixin, DetailView):
    """Service comments management view."""
    model = Service
    template_name = 'managers/comments.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(manager=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        service = self.get_object()
        
        # Get paginated comments
        comments_list = ServiceComment.objects.filter(
            service=service
        ).order_by('-created_at')
        
        paginator = Paginator(comments_list, 20)
        page = self.request.GET.get('page')
        comments = paginator.get_page(page)
        
        context['comments'] = comments
        return context


# API Views for AJAX operations

class UpdateServiceStatusAPIView(LoginRequiredMixin, RoleRequiredMixin, APIView):
    """API endpoint for updating service status via AJAX."""
    
    def post(self, request, pk):
        try:
            service = Service.objects.get(pk=pk, manager=request.user)
            new_status = request.data.get('status')
            
            if new_status not in ['open', 'closed', 'temp_closed', 'full', 'limited', 'emergency']:
                return Response(
                    {'error': 'Invalid status'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            old_status = service.current_status
            service.current_status = new_status
            service.save()
            
            # Create status history
            ServiceStatusHistory.objects.create(
                service=service,
                manager=request.user,
                change_type='status',
                old_value=old_status,
                new_value=new_status,
                description=f"Status changed from {old_status} to {new_status}"
            )
            
            return Response({
                'status': 'success',
                'new_status': new_status,
                'message': f'Service status updated to {new_status}'
            })
            
        except Service.DoesNotExist:
            return Response(
                {'error': 'Service not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class UpdateCapacityAPIView(LoginRequiredMixin, RoleRequiredMixin, APIView):
    """API endpoint for updating service capacity via AJAX."""
    
    def post(self, request, pk):
        try:
            service = Service.objects.get(pk=pk, manager=request.user)
            new_capacity = int(request.data.get('capacity', 0))
            
            if new_capacity < 0:
                return Response(
                    {'error': 'Capacity cannot be negative'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            old_capacity = service.current_capacity
            service.current_capacity = new_capacity
            service.save()
            
            # Create status history
            ServiceStatusHistory.objects.create(
                service=service,
                manager=request.user,
                change_type='capacity',
                old_value=str(old_capacity),
                new_value=str(new_capacity),
                description=f"Capacity updated from {old_capacity} to {new_capacity}"
            )
            
            # Check if capacity warning is needed
            if service.max_capacity and new_capacity >= service.max_capacity * 0.8:
                capacity_percentage = (new_capacity / service.max_capacity) * 100
                NotificationFactory.create_capacity_warning(
                    request.user, service, capacity_percentage
                )
            
            return Response({
                'status': 'success',
                'new_capacity': new_capacity,
                'capacity_percentage': service.capacity_percentage,
                'message': 'Capacity updated successfully'
            })
            
        except Service.DoesNotExist:
            return Response(
                {'error': 'Service not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except ValueError:
            return Response(
                {'error': 'Invalid capacity value'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MarkNotificationReadAPIView(LoginRequiredMixin, RoleRequiredMixin, APIView):
    """API endpoint for marking notifications as read."""
    
    def post(self, request, pk):
        try:
            notification = ManagerNotification.objects.get(
                pk=pk, manager=request.user
            )
            notification.mark_as_read()
            
            return Response({
                'status': 'success',
                'message': 'Notification marked as read'
            })
            
        except ManagerNotification.DoesNotExist:
            return Response(
                {'error': 'Notification not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': str(e)}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
