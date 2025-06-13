"""
Feedback views for CommuMap including reviews and comments.

This module provides views for user feedback system with reviews,
ratings, comments, and content moderation.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, View, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect, Http404
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.utils import timezone
from typing import Dict, Any, Optional
import json

from .models import (
    ServiceReview, ServiceComment, ReviewHelpfulVote, 
    CommentLike, FlaggedContent
)
from apps.services.models import Service
from apps.users.models import UserActivity


class ServiceReviewListView(ListView):
    """
    Display reviews for a specific service.
    """
    model = ServiceReview
    template_name = 'feedback/review_list.html'
    context_object_name = 'reviews'
    paginate_by = 10
    
    def get_queryset(self):
        self.service = get_object_or_404(Service, pk=self.kwargs['service_id'])
        return ServiceReview.objects.filter(
            service=self.service,
            is_verified=True
        ).select_related('user').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service'] = self.service
        
        # Calculate review statistics
        reviews = self.get_queryset()
        context['review_stats'] = {
            'total_count': reviews.count(),
            'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
            'rating_distribution': {
                i: reviews.filter(rating=i).count() 
                for i in range(1, 6)
            }
        }
        
        # Check if current user has reviewed
        if self.request.user.is_authenticated:
            context['user_review'] = reviews.filter(user=self.request.user).first()
        
        return context


class CreateReviewView(LoginRequiredMixin, CreateView):
    """
    Create a new review for a service.
    """
    model = ServiceReview
    template_name = 'feedback/create_review.html'
    fields = ['rating', 'title', 'content', 'tags', 'visit_date', 'is_anonymous']
    
    def dispatch(self, request, *args, **kwargs):
        self.service = get_object_or_404(Service, pk=kwargs['service_id'])
        
        # Check if user already reviewed this service
        if ServiceReview.objects.filter(
            service=self.service, 
            user=request.user
        ).exists():
            messages.warning(request, _('You have already reviewed this service.'))
            return redirect('services:detail', pk=self.service.pk)
        
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.service = self.service
        form.instance.user = self.request.user
        
        # Auto-approve reviews for now (can add moderation later)
        form.instance.is_verified = True
        
        response = super().form_valid(form)
        
        # Record user activity
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='write_review',
            service=self.service,
            metadata={'rating': form.instance.rating}
        )
        
        messages.success(self.request, _('Thank you for your review!'))
        return response
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.service.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service'] = self.service
        return context


class ReviewDetailView(DetailView):
    """
    Display detailed view of a review.
    """
    model = ServiceReview
    template_name = 'feedback/review_detail.html'
    context_object_name = 'review'
    
    def get_queryset(self):
        return ServiceReview.objects.filter(
            is_verified=True
        ).select_related('user', 'service')


class EditReviewView(LoginRequiredMixin, UpdateView):
    """
    Edit an existing review (only by the author).
    """
    model = ServiceReview
    template_name = 'feedback/edit_review.html'
    fields = ['rating', 'title', 'content', 'tags', 'visit_date', 'is_anonymous']
    
    def get_queryset(self):
        return ServiceReview.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.object.service.pk})


class ReviewVoteView(LoginRequiredMixin, View):
    """
    Handle helpful/unhelpful votes on reviews.
    """
    
    def post(self, request, *args, **kwargs):
        review = get_object_or_404(ServiceReview, pk=kwargs['pk'])
        is_helpful = request.POST.get('is_helpful') == 'true'
        
        # Prevent users from voting on their own reviews
        if review.user == request.user:
            return JsonResponse({'error': 'Cannot vote on your own review'}, status=400)
        
        vote, created = ReviewHelpfulVote.objects.get_or_create(
            review=review,
            user=request.user,
            defaults={'is_helpful': is_helpful}
        )
        
        if not created:
            # Update existing vote
            vote.is_helpful = is_helpful
            vote.save()
        
        # Update review vote counts
        helpful_count = review.votes.filter(is_helpful=True).count()
        unhelpful_count = review.votes.filter(is_helpful=False).count()
        
        review.helpful_count = helpful_count
        review.unhelpful_count = unhelpful_count
        review.save(update_fields=['helpful_count', 'unhelpful_count'])
        
        return JsonResponse({
            'helpful_count': helpful_count,
            'unhelpful_count': unhelpful_count,
            'user_vote': is_helpful
        })


class ServiceCommentListView(ListView):
    """
    Display comments for a specific service.
    """
    model = ServiceComment
    template_name = 'feedback/comment_list.html'
    context_object_name = 'comments'
    paginate_by = 20
    
    def get_queryset(self):
        self.service = get_object_or_404(Service, pk=self.kwargs['service_id'])
        return ServiceComment.objects.filter(
            service=self.service,
            is_approved=True,
            parent=None  # Only top-level comments, replies are loaded via template
        ).select_related('user').prefetch_related('replies').order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service'] = self.service
        return context


class CreateCommentView(LoginRequiredMixin, CreateView):
    """
    Create a new comment for a service.
    """
    model = ServiceComment
    template_name = 'feedback/create_comment.html'
    fields = ['content']
    
    def dispatch(self, request, *args, **kwargs):
        self.service = get_object_or_404(Service, pk=kwargs['service_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.service = self.service
        form.instance.user = self.request.user
        
        # Auto-approve comments for now
        form.instance.is_approved = True
        
        response = super().form_valid(form)
        
        # Record user activity
        UserActivity.objects.create(
            user=self.request.user,
            activity_type='write_comment',
            service=self.service
        )
        
        messages.success(self.request, _('Comment posted successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.service.pk}) + '#comments'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['service'] = self.service
        return context


class CreateCommentReplyView(LoginRequiredMixin, CreateView):
    """
    Create a reply to an existing comment.
    """
    model = ServiceComment
    template_name = 'feedback/create_reply.html'
    fields = ['content']
    
    def dispatch(self, request, *args, **kwargs):
        self.parent_comment = get_object_or_404(ServiceComment, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.service = self.parent_comment.service
        form.instance.user = self.request.user
        form.instance.parent = self.parent_comment
        form.instance.is_approved = True
        
        response = super().form_valid(form)
        
        messages.success(self.request, _('Reply posted successfully!'))
        return response
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.parent_comment.service.pk}) + f'#comment-{self.object.pk}'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['parent_comment'] = self.parent_comment
        return context


class CommentLikeView(LoginRequiredMixin, View):
    """
    Handle likes on comments.
    """
    
    def post(self, request, *args, **kwargs):
        comment = get_object_or_404(ServiceComment, pk=kwargs['pk'])
        
        # Prevent users from liking their own comments
        if comment.user == request.user:
            return JsonResponse({'error': 'Cannot like your own comment'}, status=400)
        
        like, created = CommentLike.objects.get_or_create(
            comment=comment,
            user=request.user
        )
        
        if not created:
            # Unlike if already liked
            like.delete()
            liked = False
        else:
            liked = True
        
        # Update comment like count
        like_count = comment.likes.count()
        comment.like_count = like_count
        comment.save(update_fields=['like_count'])
        
        return JsonResponse({
            'like_count': like_count,
            'liked': liked
        })


class FlagReviewView(LoginRequiredMixin, CreateView):
    """
    Flag a review for moderation.
    """
    model = FlaggedContent
    template_name = 'feedback/flag_content.html'
    fields = ['reason', 'description']
    
    def dispatch(self, request, *args, **kwargs):
        self.review = get_object_or_404(ServiceReview, pk=kwargs['review_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.flagged_by = self.request.user
        form.instance.review = self.review
        
        response = super().form_valid(form)
        
        # Mark review as flagged
        self.review.is_flagged = True
        self.review.save(update_fields=['is_flagged'])
        
        messages.success(self.request, _('Content has been flagged for review.'))
        return response
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.review.service.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = 'review'
        context['content'] = self.review
        return context


class FlagCommentView(LoginRequiredMixin, CreateView):
    """
    Flag a comment for moderation.
    """
    model = FlaggedContent
    template_name = 'feedback/flag_content.html'
    fields = ['reason', 'description']
    
    def dispatch(self, request, *args, **kwargs):
        self.comment = get_object_or_404(ServiceComment, pk=kwargs['comment_id'])
        return super().dispatch(request, *args, **kwargs)
    
    def form_valid(self, form):
        form.instance.flagged_by = self.request.user
        form.instance.comment = self.comment
        
        response = super().form_valid(form)
        
        # Mark comment as flagged
        self.comment.is_flagged = True
        self.comment.save(update_fields=['is_flagged'])
        
        messages.success(self.request, _('Content has been flagged for review.'))
        return response
    
    def get_success_url(self):
        return reverse('services:detail', kwargs={'pk': self.comment.service.pk})
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['content_type'] = 'comment'
        context['content'] = self.comment
        return context


class ReviewAPIView(View):
    """
    JSON API for reviews (AJAX requests).
    """
    
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get('service_id')
        if not service_id:
            return JsonResponse({'error': 'service_id required'}, status=400)
        
        try:
            service = Service.objects.get(pk=service_id)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=404)
        
        reviews = ServiceReview.objects.filter(
            service=service,
            is_verified=True
        ).select_related('user').order_by('-created_at')[:10]
        
        reviews_data = []
        for review in reviews:
            reviews_data.append({
                'id': str(review.pk),
                'rating': review.rating,
                'title': review.title,
                'content': review.content,
                'author': review.display_name,
                'created_at': review.created_at.isoformat(),
                'helpful_count': review.helpful_count,
                'unhelpful_count': review.unhelpful_count,
                'tags': review.tags
            })
        
        return JsonResponse({
            'reviews': reviews_data,
            'total_count': reviews.count()
        })


class CommentAPIView(View):
    """
    JSON API for comments (AJAX requests).
    """
    
    def get(self, request, *args, **kwargs):
        service_id = request.GET.get('service_id')
        if not service_id:
            return JsonResponse({'error': 'service_id required'}, status=400)
        
        try:
            service = Service.objects.get(pk=service_id)
        except Service.DoesNotExist:
            return JsonResponse({'error': 'Service not found'}, status=404)
        
        comments = ServiceComment.objects.filter(
            service=service,
            is_approved=True,
            parent=None
        ).select_related('user').prefetch_related('replies').order_by('-created_at')[:20]
        
        def serialize_comment(comment):
            return {
                'id': str(comment.pk),
                'content': comment.content,
                'author': comment.user.get_display_name(),
                'created_at': comment.created_at.isoformat(),
                'like_count': comment.like_count,
                'replies': [serialize_comment(reply) for reply in comment.replies.filter(is_approved=True)]
            }
        
        comments_data = [serialize_comment(comment) for comment in comments]
        
        return JsonResponse({
            'comments': comments_data,
            'total_count': comments.count()
        })


class CreateReviewAPIView(View):
    """
    AJAX API for creating reviews.
    """
    
    def post(self, request, *args, **kwargs):
        # Check authentication for AJAX requests
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Review API called by user: {request.user.id}")
            logger.info(f"Content type: {request.content_type}")
            logger.info(f"Request body: {request.body}")
            
            # Parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Fallback to form data
                data = {
                    'rating': request.POST.get('rating'),
                    'title': request.POST.get('title'),
                    'content': request.POST.get('content'),
                    'is_anonymous': request.POST.get('is_anonymous') == 'on'
                }
            
            logger.info(f"Parsed data: {data}")
            
            service_id = kwargs.get('service_id')
            service = get_object_or_404(Service, pk=service_id)
            
            # Check if user already reviewed this service
            if ServiceReview.objects.filter(service=service, user=request.user).exists():
                return JsonResponse({'error': 'You have already reviewed this service'}, status=400)
            
            # Validate required fields
            rating = data.get('rating')
            title = data.get('title', '').strip()
            content = data.get('content', '').strip()
            
            # Convert rating to int if it's a string
            if isinstance(rating, str):
                try:
                    rating = int(rating)
                except ValueError:
                    rating = None
            
            if not rating or not isinstance(rating, int) or rating < 1 or rating > 5:
                return JsonResponse({'error': 'Valid rating (1-5) is required'}, status=400)
            
            if not title or len(title) < 5:
                return JsonResponse({'error': 'Title must be at least 5 characters'}, status=400)
            
            if not content or len(content) < 20:
                return JsonResponse({'error': 'Review content must be at least 20 characters'}, status=400)
            
            # Create review
            review = ServiceReview.objects.create(
                service=service,
                user=request.user,
                rating=rating,
                title=title,
                content=content,
                is_anonymous=data.get('is_anonymous', False),
                is_verified=True  # Auto-approve for now
            )
            
            # Record user activity
            try:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='write_review',
                    service=service,
                    metadata={'rating': rating}
                )
            except Exception:
                # Don't fail if activity logging fails
                pass
            
            return JsonResponse({
                'success': True,
                'message': 'Review submitted successfully!',
                'review_id': str(review.pk)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class CreateCommentAPIView(View):
    """
    AJAX API for creating comments.
    """
    
    def post(self, request, *args, **kwargs):
        # Check authentication for AJAX requests
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            # Debug logging
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"Comment API called by user: {request.user.id}")
            logger.info(f"Content type: {request.content_type}")
            logger.info(f"Request body: {request.body}")
            
            # Parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                # Fallback to form data
                data = {
                    'content': request.POST.get('content')
                }
            
            logger.info(f"Parsed comment data: {data}")
            
            service_id = kwargs.get('service_id')
            service = get_object_or_404(Service, pk=service_id)
            
            # Validate required fields
            content = data.get('content', '').strip()
            
            if not content or len(content) < 20:
                return JsonResponse({'error': 'Comment must be at least 20 characters'}, status=400)
            
            # Create comment
            comment = ServiceComment.objects.create(
                service=service,
                user=request.user,
                content=content,
                is_approved=True  # Auto-approve for now
            )
            
            # Record user activity
            try:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='write_comment',
                    service=service
                )
            except Exception:
                # Don't fail if activity logging fails
                pass
            
            return JsonResponse({
                'success': True,
                'message': 'Comment posted successfully!',
                'comment_id': str(comment.pk)
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class CreateReplyAPIView(LoginRequiredMixin, View):
    """
    AJAX API for creating replies to reviews and comments.
    """
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            # Parse JSON data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                return JsonResponse({'error': 'JSON data required'}, status=400)
            
            content = data.get('content', '').strip()
            parent_type = data.get('parent_type')  # 'review' or 'comment'
            parent_id = data.get('parent_id')
            
            # Validate input
            if not content or len(content) < 10:
                return JsonResponse({'error': 'Reply must be at least 10 characters'}, status=400)
            
            if parent_type not in ['review', 'comment']:
                return JsonResponse({'error': 'Invalid parent type'}, status=400)
            
            if not parent_id:
                return JsonResponse({'error': 'Parent ID required'}, status=400)
            
            # Find parent and create reply
            if parent_type == 'review':
                parent_review = get_object_or_404(ServiceReview, pk=parent_id)
                # Create a comment as a reply to the review
                reply = ServiceComment.objects.create(
                    service=parent_review.service,
                    user=request.user,
                    content=content,
                    is_approved=True,
                    # We'll add a reference to the review in metadata or use a different approach
                )
                service = parent_review.service
            else:  # parent_type == 'comment'
                parent_comment = get_object_or_404(ServiceComment, pk=parent_id)
                # Create a nested comment reply
                reply = ServiceComment.objects.create(
                    service=parent_comment.service,
                    user=request.user,
                    content=content,
                    parent=parent_comment,
                    is_approved=True
                )
                service = parent_comment.service
            
            # Record user activity
            try:
                UserActivity.objects.create(
                    user=request.user,
                    activity_type='write_comment',
                    service=service
                )
            except Exception:
                pass
            
            # Generate reply HTML for insertion into DOM
            reply_html = f'''
            <div class="reply-item mb-4 last:mb-0 new-item">
                <div class="flex items-start space-x-3">
                    <div class="flex-shrink-0">
                        <div class="w-8 h-8 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full flex items-center justify-center text-white font-semibold text-xs">
                            {request.user.get_display_name()[0].upper()}
                        </div>
                    </div>
                    <div class="flex-1">
                        <div class="flex items-center space-x-2 mb-1">
                            <h5 class="font-medium text-gray-900 text-sm">{request.user.get_display_name()}</h5>
                            <span class="text-xs text-gray-500">just now</span>
                        </div>
                        <p class="text-sm text-gray-700">{content}</p>
                    </div>
                </div>
            </div>
            '''
            
            return JsonResponse({
                'success': True,
                'message': 'Reply posted successfully!',
                'reply_id': str(reply.pk),
                'reply_html': reply_html.strip()
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class ReviewHelpfulAPIView(LoginRequiredMixin, View):
    """
    AJAX API for marking reviews as helpful.
    """
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            review_id = kwargs.get('review_id')
            review = get_object_or_404(ServiceReview, pk=review_id)
            
            # Prevent users from voting on their own reviews
            if review.user == request.user:
                return JsonResponse({'error': 'Cannot vote on your own review'}, status=400)
            
            # Get or create vote
            vote, created = ReviewHelpfulVote.objects.get_or_create(
                review=review,
                user=request.user,
                defaults={'is_helpful': True}
            )
            
            user_action = None
            if not created:
                if vote.is_helpful:
                    # User already voted helpful, remove vote
                    vote.delete()
                    user_action = None
                else:
                    # User voted unhelpful before, change to helpful
                    vote.is_helpful = True
                    vote.save()
                    user_action = 'helpful'
            else:
                user_action = 'helpful'
            
            # Update review vote counts
            helpful_count = review.votes.filter(is_helpful=True).count()
            unhelpful_count = review.votes.filter(is_helpful=False).count()
            
            review.helpful_count = helpful_count
            review.unhelpful_count = unhelpful_count
            review.save(update_fields=['helpful_count', 'unhelpful_count'])
            
            return JsonResponse({
                'success': True,
                'count': helpful_count,
                'user_action': user_action,
                'message': 'Thank you for your feedback!' if user_action else 'Vote removed'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class ReviewUnhelpfulAPIView(LoginRequiredMixin, View):
    """
    AJAX API for marking reviews as unhelpful.
    """
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            review_id = kwargs.get('review_id')
            review = get_object_or_404(ServiceReview, pk=review_id)
            
            # Prevent users from voting on their own reviews
            if review.user == request.user:
                return JsonResponse({'error': 'Cannot vote on your own review'}, status=400)
            
            # Get or create vote
            vote, created = ReviewHelpfulVote.objects.get_or_create(
                review=review,
                user=request.user,
                defaults={'is_helpful': False}
            )
            
            user_action = None
            if not created:
                if not vote.is_helpful:
                    # User already voted unhelpful, remove vote
                    vote.delete()
                    user_action = None
                else:
                    # User voted helpful before, change to unhelpful
                    vote.is_helpful = False
                    vote.save()
                    user_action = 'unhelpful'
            else:
                user_action = 'unhelpful'
            
            # Update review vote counts
            helpful_count = review.votes.filter(is_helpful=True).count()
            unhelpful_count = review.votes.filter(is_helpful=False).count()
            
            review.helpful_count = helpful_count
            review.unhelpful_count = unhelpful_count
            review.save(update_fields=['helpful_count', 'unhelpful_count'])
            
            return JsonResponse({
                'success': True,
                'count': unhelpful_count,
                'user_action': user_action,
                'message': 'Thank you for your feedback!' if user_action else 'Vote removed'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


class CommentLikeAPIView(LoginRequiredMixin, View):
    """
    AJAX API for liking comments.
    """
    
    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'error': 'Authentication required'}, status=401)
            
        try:
            comment_id = kwargs.get('comment_id')
            comment = get_object_or_404(ServiceComment, pk=comment_id)
            
            # Get or create like
            like, created = CommentLike.objects.get_or_create(
                comment=comment,
                user=request.user
            )
            
            user_action = None
            if not created:
                # User already liked, remove like
                like.delete()
                user_action = None
            else:
                user_action = 'like'
            
            # Update comment like count
            like_count = comment.likes.count()
            comment.like_count = like_count
            comment.save(update_fields=['like_count'])
            
            return JsonResponse({
                'success': True,
                'count': like_count,
                'user_action': user_action,
                'message': 'Liked!' if user_action else 'Like removed'
            })
            
        except Exception as e:
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)


# --- DELETE VIEWS FOR COMMENTS AND FEEDBACK ---
from .models import ServiceReview, ServiceComment

class DeleteCommentView(LoginRequiredMixin, DeleteView):
    model = ServiceComment
    template_name = 'feedback/comment_confirm_delete.html'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_success_url(self):
        service_id = self.object.service.id
        return reverse_lazy('services:detail', kwargs={'pk': service_id}) + '#comments'

class DeleteFeedbackView(LoginRequiredMixin, DeleteView):
    model = ServiceReview
    template_name = 'feedback/feedback_confirm_delete.html'

    def get_queryset(self):
        return super().get_queryset().filter(user=self.request.user)

    def get_success_url(self):
        service_id = self.object.service.id
        return reverse_lazy('services:detail', kwargs={'pk': service_id}) + '#reviews'
