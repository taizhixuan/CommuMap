"""
Views for Community Moderator functionality.

Implements queue-based approval workflows, bulk operations,
and moderator dashboard following the requirements in the sitemap.
"""
import json
from typing import Dict, Any
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Prefetch
from django.http import JsonResponse, HttpRequest, HttpResponse
from django.urls import reverse_lazy, reverse
from django.utils import timezone
from django.views import View
from django.views.generic import (
    TemplateView, ListView, DetailView, CreateView, 
    UpdateView, DeleteView, FormView
)

from apps.core.models import User, UserRole
from apps.services.models import Service
from apps.feedback.models import ServiceReview, FlaggedContent, ServiceComment
from .models import OutreachPost, ModerationAction, ModeratorNotification
from .forms import (
    OutreachPostForm, ServiceModeratorEditForm, 
    CommentModerationForm, BulkActionForm, ModeratorProfileForm
)
from .mixins import ModeratorRequiredMixin


class ModeratorHomeView(ModeratorRequiredMixin, TemplateView):
    """
    Home page for Community Moderators - redirects to dashboard.
    """
    template_name = 'moderators/home.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        
        # Basic stats for home page
        context.update({
            'pending_services_count': Service.objects.filter(is_verified=False).count(),
            'pending_comments_count': ServiceComment.objects.filter(is_approved=False).count(),
            'flagged_content_count': FlaggedContent.objects.filter(is_resolved=False).count(),
        })
        
        return context


class ModeratorDashboardView(ModeratorRequiredMixin, TemplateView):
    """
    Main dashboard for community moderators showing pending items and quick actions.
    """
    template_name = 'moderators/dashboard.html'
    
    def get_context_data(self, **kwargs) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        moderator = self.request.user
        
        # Pending counts for dashboard widgets
        context.update({
            'pending_services_count': Service.objects.filter(is_verified=False).count(),
            'pending_comments_count': ServiceComment.objects.filter(is_approved=False).count(),
            'flagged_content_count': FlaggedContent.objects.filter(is_resolved=False).count(),
            'active_outreach_posts': OutreachPost.objects.filter(is_active=True).count(),
        })
        
        # Recent activity
        context['recent_actions'] = ModerationAction.objects.filter(
            moderator=moderator
        )[:10]
        
        # Pending services for quick preview
        context['pending_services'] = Service.objects.filter(
            is_verified=False
        ).select_related('category', 'manager')[:5]
        
        # Pending comments for quick preview
        context['pending_comments'] = ServiceComment.objects.filter(
            is_approved=False
        ).select_related('user', 'service')[:5]
        
        return context


class ModeratorProfileView(ModeratorRequiredMixin, UpdateView):
    """
    Moderator profile management view.
    """
    template_name = 'moderators/profile.html'
    model = User
    form_class = ModeratorProfileForm
    success_url = reverse_lazy('moderators:profile')
    
    def get_object(self):
        return self.request.user
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user
        
        # Calculate moderation statistics
        moderation_actions = user.moderation_actions.all()
        context['moderation_stats'] = {
            'services_approved': moderation_actions.filter(action_type='approve_service').count(),
            'comments_approved': moderation_actions.filter(action_type='approve_comment').count(),
            'outreach_posts': user.outreach_posts.count(),
            'total_actions': moderation_actions.count(),
        }
        
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


class ServiceApprovalQueueView(ModeratorRequiredMixin, ListView):
    """
    Service approval queue with bulk actions.
    """
    template_name = 'moderators/services_pending.html'
    model = Service
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Service.objects.filter(
            is_verified=False
        ).select_related('category', 'manager').order_by('-created_at')
        
        # Apply filters
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category_id=category)
        
        search = self.request.GET.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | 
                Q(description__icontains=search)
            )
        
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BulkActionForm()
        return context


class ServiceModeratorEditView(ModeratorRequiredMixin, UpdateView):
    """
    Light editing of services by moderators while keeping verified state.
    """
    template_name = 'moderators/service_edit.html'
    model = Service
    form_class = ServiceModeratorEditForm
    
    def get_success_url(self):
        return reverse('moderators:services_pending')
    
    def form_valid(self, form):
        # Log the edit action
        ModerationAction.log_action(
            moderator=self.request.user,
            action_type='edit_service',
            target_service=self.object,
            reason=f"Edited service details: {', '.join(form.changed_data)}"
        )
        messages.success(self.request, 'Service updated successfully!')
        return super().form_valid(form)


class CommentApprovalQueueView(ModeratorRequiredMixin, ListView):
    """
    Comment approval queue with bulk actions.
    """
    template_name = 'moderators/comments_pending.html'
    model = ServiceComment
    context_object_name = 'comments'
    paginate_by = 20
    
    def get_queryset(self):
        return ServiceComment.objects.filter(
            is_approved=False
        ).select_related('user', 'service').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BulkActionForm()
        
        # Calculate today's statistics
        from django.utils import timezone
        today = timezone.now().date()
        
        context['approved_today_count'] = ModerationAction.objects.filter(
            action_type='approve_comment',
            created_at__date=today
        ).count()
        
        context['rejected_today_count'] = ModerationAction.objects.filter(
            action_type='reject_comment',
            created_at__date=today
        ).count()
        
        return context


class CommentThreadView(ModeratorRequiredMixin, DetailView):
    """
    Comment thread view for moderator replies.
    """
    template_name = 'moderators/comment_thread.html'
    model = ServiceComment
    context_object_name = 'comment'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all replies in the thread
        context['replies'] = self.object.replies.all().select_related('user')
        context['form'] = CommentModerationForm()
        
        return context


class OutreachView(ModeratorRequiredMixin, ListView):
    """
    Outreach posts management list view.
    """
    template_name = 'moderators/outreach.html'
    model = OutreachPost
    context_object_name = 'posts'
    paginate_by = 20
    
    def get_queryset(self):
        return OutreachPost.objects.filter(
            created_by=self.request.user
        ).prefetch_related('target_categories').order_by('-created_at')


class OutreachCreateView(ModeratorRequiredMixin, CreateView):
    """
    Create new outreach post.
    """
    template_name = 'moderators/outreach_form.html'
    model = OutreachPost
    form_class = OutreachPostForm
    success_url = reverse_lazy('moderators:outreach')
    
    def form_valid(self, form):
        form.instance.created_by = self.request.user
        response = super().form_valid(form)
        
        # Log the action
        ModerationAction.log_action(
            moderator=self.request.user,
            action_type='create_outreach',
            target_outreach=self.object,
            reason=f"Created outreach post: {self.object.title}"
        )
        
        messages.success(self.request, 'Outreach post created successfully!')
        return response


class OutreachDetailView(ModeratorRequiredMixin, DetailView):
    """
    Outreach post detail view.
    """
    template_name = 'moderators/outreach_detail.html'
    model = OutreachPost
    context_object_name = 'post'


class OutreachUpdateView(ModeratorRequiredMixin, UpdateView):
    """
    Update existing outreach post.
    """
    template_name = 'moderators/outreach_form.html'
    model = OutreachPost
    form_class = OutreachPostForm
    success_url = reverse_lazy('moderators:outreach')
    
    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)
    
    def form_valid(self, form):
        response = super().form_valid(form)
        
        # Log the action
        ModerationAction.log_action(
            moderator=self.request.user,
            action_type='edit_outreach',
            target_outreach=self.object,
            reason=f"Updated outreach post: {self.object.title}"
        )
        
        messages.success(self.request, 'Outreach post updated successfully!')
        return response


class OutreachDeleteView(ModeratorRequiredMixin, DeleteView):
    """
    Delete outreach post.
    """
    template_name = 'moderators/outreach_confirm_delete.html'
    model = OutreachPost
    success_url = reverse_lazy('moderators:outreach')
    
    def get_queryset(self):
        return super().get_queryset().filter(created_by=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        outreach_title = self.get_object().title
        response = super().delete(request, *args, **kwargs)
        
        # Log the action
        ModerationAction.log_action(
            moderator=request.user,
            action_type='delete_outreach',
            reason=f"Deleted outreach post: {outreach_title}"
        )
        
        messages.success(request, 'Outreach post deleted successfully!')
        return response


class FeedbackModerationView(ModeratorRequiredMixin, ListView):
    """
    Feedback moderation view.
    """
    template_name = 'moderators/feedback.html'
    model = ServiceReview
    context_object_name = 'flagged_reviews'
    paginate_by = 20
    
    def get_queryset(self):
        return ServiceReview.objects.filter(
            is_flagged=True
        ).select_related('user', 'service').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Calculate statistics
        from django.utils import timezone
        today = timezone.now().date()
        
        context['pending_actions_count'] = FlaggedContent.objects.filter(
            is_resolved=False
        ).count()
        
        context['resolved_today_count'] = ModerationAction.objects.filter(
            action_type='resolve_flag',
            created_at__date=today
        ).count()
        
        return context


class ModerationActionsView(ModeratorRequiredMixin, ListView):
    """
    View moderation action history.
    """
    template_name = 'moderators/actions.html'
    model = ModerationAction
    context_object_name = 'actions'
    paginate_by = 50
    
    def get_queryset(self):
        return ModerationAction.objects.filter(
            moderator=self.request.user
        ).select_related('target_service', 'target_comment', 'target_outreach')


class ModerationActionDetailView(ModeratorRequiredMixin, DetailView):
    """
    Detailed view of a specific moderation action.
    """
    template_name = 'moderators/action_detail.html'
    model = ModerationAction
    context_object_name = 'action'


# API Views for AJAX operations

class ApproveServiceAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to approve a service.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            service = get_object_or_404(Service, pk=pk, is_verified=False)
            reason = request.POST.get('reason', '')
            
            # Approve the service
            service.is_verified = True
            service.verified_by = request.user
            service.verified_at = timezone.now()
            service.save()
            
            # Log the action
            ModerationAction.log_action(
                moderator=request.user,
                action_type='approve_service',
                target_service=service,
                reason=reason
            )
            
            # Create notification for the service manager
            from apps.managers.models import ManagerNotification
            if service.manager:
                message = f'Your service "{service.name}" has been approved by community moderator {request.user.get_display_name()} and is now visible to the public.'
                if reason:
                    message += f' Moderator notes: {reason}'
                
                ManagerNotification.objects.create(
                    manager=service.manager,
                    notification_type='service_approved',
                    title=f'Service Approved: {service.name}',
                    message=message,
                    priority='normal',
                    related_service=service,
                    action_url='/manager/services/'
                )
            
            return JsonResponse({
                'success': True,
                'message': f'Service "{service.name}" approved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error approving service: {str(e)}'
            }, status=400)
    



class RejectServiceAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to reject a service.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            service = get_object_or_404(Service, pk=pk, is_verified=False)
            reason = request.POST.get('reason', 'No reason provided')
            
            # Create notification for the service manager before deletion
            from apps.managers.models import ManagerNotification
            if service.manager:
                message = f'Your service "{service.name}" has been rejected by community moderator {request.user.get_display_name()}.'
                if reason and reason != 'No reason provided':
                    message += f' Reason: {reason}'
                message += ' You can contact support if you believe this was an error.'
                
                ManagerNotification.objects.create(
                    manager=service.manager,
                    notification_type='service_rejected',
                    title=f'Service Rejected: {service.name}',
                    message=message,
                    priority='high',
                    action_url='/manager/services/'
                )
            
            # Log the action before deletion
            ModerationAction.log_action(
                moderator=request.user,
                action_type='reject_service',
                reason=reason,
                metadata={'service_name': service.name, 'service_id': str(service.pk)}
            )
            
            service_name = service.name
            service.delete()
            
            return JsonResponse({
                'success': True,
                'message': f'Service "{service_name}" rejected and removed!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error rejecting service: {str(e)}'
            }, status=400)


class BulkApproveServicesAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint for bulk service approval.
    """
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            service_ids = data.get('service_ids', [])
            reason = data.get('reason', '')
            
            services = Service.objects.filter(pk__in=service_ids, is_verified=False)
            approved_count = 0
            
            for service in services:
                service.is_verified = True
                service.verified_by = request.user
                service.verified_at = timezone.now()
                service.save()
                

                
                ModerationAction.log_action(
                    moderator=request.user,
                    action_type='approve_service',
                    target_service=service,
                    reason=reason
                )
                approved_count += 1
            
            # Also log bulk action
            ModerationAction.log_action(
                moderator=request.user,
                action_type='bulk_approve_services',
                reason=f'Bulk approved {approved_count} services',
                metadata={'service_count': approved_count}
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully approved {approved_count} services!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error in bulk approval: {str(e)}'
            }, status=400)


class BulkRejectServicesAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint for bulk service rejection.
    """
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            service_ids = data.get('service_ids', [])
            reason = data.get('reason', 'No reason provided')
            
            services = Service.objects.filter(pk__in=service_ids, is_verified=False)
            rejected_count = 0
            
            for service in services:
                ModerationAction.log_action(
                    moderator=request.user,
                    action_type='reject_service',
                    reason=reason,
                    metadata={'service_name': service.name, 'service_id': str(service.pk)}
                )
                service.delete()
                rejected_count += 1
            
            # Also log bulk action
            ModerationAction.log_action(
                moderator=request.user,
                action_type='bulk_reject_services',
                reason=f'Bulk rejected {rejected_count} services',
                metadata={'service_count': rejected_count}
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully rejected {rejected_count} services!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error in bulk rejection: {str(e)}'
            }, status=400)


class ApproveCommentAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to approve a comment.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            comment = get_object_or_404(ServiceComment, pk=pk, is_approved=False)
            reason = request.POST.get('reason', '')
            
            comment.is_approved = True
            comment.approved_by = request.user
            comment.approved_at = timezone.now()
            comment.save()
            
            ModerationAction.log_action(
                moderator=request.user,
                action_type='approve_comment',
                target_comment=comment,
                reason=reason
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Comment approved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error approving comment: {str(e)}'
            }, status=400)


class RejectCommentAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to reject a comment.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            comment = get_object_or_404(ServiceComment, pk=pk, is_approved=False)
            reason = request.POST.get('reason', 'No reason provided')
            
            ModerationAction.log_action(
                moderator=request.user,
                action_type='reject_comment',
                reason=reason,
                metadata={
                    'comment_content': comment.content[:100],
                    'comment_id': str(comment.pk)
                }
            )
            
            comment.delete()
            
            return JsonResponse({
                'success': True,
                'message': 'Comment rejected and removed!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error rejecting comment: {str(e)}'
            }, status=400)


class BulkApproveCommentsAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint for bulk comment approval.
    """
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            comment_ids = data.get('comment_ids', [])
            reason = data.get('reason', '')
            
            comments = ServiceComment.objects.filter(pk__in=comment_ids, is_approved=False)
            approved_count = 0
            
            for comment in comments:
                comment.is_approved = True
                comment.approved_by = request.user
                comment.approved_at = timezone.now()
                comment.save()
                
                ModerationAction.log_action(
                    moderator=request.user,
                    action_type='approve_comment',
                    target_comment=comment,
                    reason=reason
                )
                approved_count += 1
            
            ModerationAction.log_action(
                moderator=request.user,
                action_type='bulk_approve_comments',
                reason=f'Bulk approved {approved_count} comments',
                metadata={'comment_count': approved_count}
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully approved {approved_count} comments!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error in bulk approval: {str(e)}'
            }, status=400)


class BulkRejectCommentsAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint for bulk comment rejection.
    """
    def post(self, request: HttpRequest) -> JsonResponse:
        try:
            data = json.loads(request.body)
            comment_ids = data.get('comment_ids', [])
            reason = data.get('reason', 'No reason provided')
            
            comments = ServiceComment.objects.filter(pk__in=comment_ids, is_approved=False)
            rejected_count = 0
            
            for comment in comments:
                ModerationAction.log_action(
                    moderator=request.user,
                    action_type='reject_comment',
                    reason=reason,
                    metadata={
                        'comment_content': comment.content[:100],
                        'comment_id': str(comment.pk)
                    }
                )
                comment.delete()
                rejected_count += 1
            
            ModerationAction.log_action(
                moderator=request.user,
                action_type='bulk_reject_comments',
                reason=f'Bulk rejected {rejected_count} comments',
                metadata={'comment_count': rejected_count}
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Successfully rejected {rejected_count} comments!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error in bulk rejection: {str(e)}'
            }, status=400)


class ResolveFlagAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to resolve a flagged content item.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            flag = get_object_or_404(FlaggedContent, pk=pk, is_resolved=False)
            resolution_notes = request.POST.get('resolution_notes', '')
            action_taken = request.POST.get('action_taken', 'no_action')
            
            # Resolve the flag
            flag.is_resolved = True
            flag.resolved_by = request.user
            flag.resolved_at = timezone.now()
            flag.resolution_notes = resolution_notes
            flag.action_taken = action_taken
            flag.save()
            
            # Log the action
            ModerationAction.log_action(
                moderator=request.user,
                action_type='resolve_flag',
                reason=f"Resolved flag with action: {action_taken}. Notes: {resolution_notes}"
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Flag resolved successfully!'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error resolving flag: {str(e)}'
            }, status=400)


class MarkModeratorNotificationReadAPIView(ModeratorRequiredMixin, View):
    """
    API endpoint to mark a moderator notification as read.
    """
    def post(self, request: HttpRequest, pk: str) -> JsonResponse:
        try:
            notification = get_object_or_404(
                ModeratorNotification, 
                pk=pk, 
                moderator=request.user
            )
            
            notification.mark_as_read()
            
            return JsonResponse({
                'success': True,
                'message': 'Notification marked as read'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error marking notification as read: {str(e)}'
            }, status=400) 