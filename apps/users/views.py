"""
Enhanced user views for CommuMap.

This module contains comprehensive user-specific views including dashboard,
bookmarks, recommendations, and profile functionality.
"""
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Count, Avg, Q
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.generic import ListView, UpdateView, CreateView
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from typing import Dict, Any, List
import json
from datetime import timedelta

from apps.services.models import Service, ServiceCategory
from .models import ServiceBookmark, SearchHistory, UserPreferences, UserActivity
from apps.feedback.models import ServiceReview, ServiceComment
from apps.core.forms import ProfileUpdateForm


@login_required
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """
    Enhanced user dashboard with comprehensive statistics and quick actions.
    Redirects service managers to their appropriate dashboard.
    """
    user = request.user
    
    # Redirect service managers and moderators to their appropriate dashboards
    if hasattr(user, 'role'):
        if user.role == 'service_manager' and user.is_verified:
            return redirect('manager:dashboard')
        elif user.role == 'community_moderator' and user.is_verified:
            return redirect('moderators:dashboard')
        elif user.role == 'admin' and user.is_verified:
            return redirect('console:home')
    
    # Recent activity (last 30 days)
    recent_activity = UserActivity.objects.filter(
        user=user,
        created_at__gte=timezone.now() - timedelta(days=30)
    ).select_related('service').order_by('-created_at')[:10]
    
    # User statistics
    stats = {
        'bookmarks_count': ServiceBookmark.objects.filter(user=user).count(),
        'reviews_count': ServiceReview.objects.filter(user=user).count(),
        'comments_count': ServiceComment.objects.filter(user=user).count(),
        'searches_count': SearchHistory.objects.filter(user=user).count(),
    }
    
    # Recent bookmarks
    recent_bookmarks = ServiceBookmark.objects.filter(
        user=user
    ).select_related('service').order_by('-created_at')[:5]
    
    # Popular services near user (if location available)
    popular_services = []
    if user.preferred_location_lat and user.preferred_location_lng:
        # Simple distance calculation for demo (would use PostGIS in production)
        popular_services = Service.objects.filter(
            is_active=True,
            is_verified=True
        ).annotate(
            review_count=Count('reviews'),
            avg_rating=Avg('reviews__rating')
        ).filter(review_count__gt=0).order_by('-avg_rating', '-review_count')[:6]
    
    # Get user preferences
    try:
        preferences = user.preferences
    except UserPreferences.DoesNotExist:
        preferences = UserPreferences.objects.create(user=user)
    
    # Recommendations based on user activity
    recommendations = get_user_recommendations(user)
    
    context = {
        'user': user,
        'stats': stats,
        'recent_activity': recent_activity,
        'recent_bookmarks': recent_bookmarks,
        'popular_services': popular_services,
        'recommendations': recommendations,
        'preferences': preferences,
        'emergency_services': Service.objects.filter(
            is_emergency_service=True,
            is_active=True
        )[:3]
    }
    
    return render(request, 'users/dashboard.html', context)


@login_required
def bookmarks_view(request: HttpRequest) -> HttpResponse:
    """
    Enhanced bookmarks view with filtering, search, and organization.
    """
    user = request.user
    
    # Get filter parameters
    category_filter = request.GET.get('category')
    folder_filter = request.GET.get('folder')
    search_query = request.GET.get('q', '').strip()
    sort_by = request.GET.get('sort', 'created_at')  # created_at, name, last_accessed
    
    # Base queryset
    bookmarks = ServiceBookmark.objects.filter(
        user=user
    ).select_related('service', 'service__category')
    
    # Apply filters
    if category_filter:
        bookmarks = bookmarks.filter(service__category__slug=category_filter)
    
    if folder_filter:
        bookmarks = bookmarks.filter(folder_name=folder_filter)
    
    if search_query:
        bookmarks = bookmarks.filter(
            Q(service__name__icontains=search_query) |
            Q(service__description__icontains=search_query) |
            Q(notes__icontains=search_query)
        )
    
    # Apply sorting
    sort_options = {
        'created_at': '-created_at',
        'name': 'service__name',
        'last_accessed': '-last_accessed',
        'rating': '-service__quality_score'
    }
    bookmarks = bookmarks.order_by(sort_options.get(sort_by, '-created_at'))
    
    # Pagination
    paginator = Paginator(bookmarks, 12)
    page_number = request.GET.get('page')
    bookmarks_page = paginator.get_page(page_number)
    
    # Get available folders and categories
    folders = ServiceBookmark.objects.filter(
        user=user,
        folder_name__isnull=False
    ).exclude(folder_name='').values_list('folder_name', flat=True).distinct()
    
    categories = ServiceCategory.objects.filter(
        services__bookmarked_by__user=user
    ).distinct()
    
    context = {
        'bookmarks': bookmarks_page,
        'categories': categories,
        'folders': folders,
        'current_category': category_filter,
        'current_folder': folder_filter,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_bookmarks': bookmarks.count(),
    }
    
    return render(request, 'users/bookmarks.html', context)


@login_required
def recommendations_view(request: HttpRequest) -> HttpResponse:
    """
    AI-powered recommendations based on user behavior and preferences.
    """
    user = request.user
    
    # Get different types of recommendations
    recommendations = {
        'personalized': get_personalized_recommendations(user),
        'trending': get_trending_services(),
        'nearby': get_nearby_recommendations(user),
        'similar_users': get_similar_user_recommendations(user),
    }
    
    context = {
        'recommendations': recommendations,
        'user': user,
    }
    
    return render(request, 'users/recommendations.html', context)


@login_required
def profile_view(request: HttpRequest) -> HttpResponse:
    """
    Enhanced user profile view with comprehensive information.
    """
    user = request.user
    
    # Get or create user preferences
    try:
        preferences = user.preferences
    except UserPreferences.DoesNotExist:
        preferences = UserPreferences.objects.create(user=user)
    
    # User activity summary
    activity_summary = {
        'total_reviews': ServiceReview.objects.filter(user=user).count(),
        'total_comments': ServiceComment.objects.filter(user=user).count(),
        'total_bookmarks': ServiceBookmark.objects.filter(user=user).count(),
        'total_searches': SearchHistory.objects.filter(user=user).count(),
        'member_since': user.date_joined,
        'last_active': user.last_active,
    }
    
    # Recent reviews
    recent_reviews = ServiceReview.objects.filter(
        user=user
    ).select_related('service').order_by('-created_at')[:5]
    
    # Favorite categories (based on bookmarks)
    favorite_categories = ServiceCategory.objects.filter(
        services__bookmarked_by__user=user
    ).annotate(
        bookmark_count=Count('services__bookmarked_by')
    ).order_by('-bookmark_count')[:5]
    
    context = {
        'user': user,
        'preferences': preferences,
        'activity_summary': activity_summary,
        'recent_reviews': recent_reviews,
        'favorite_categories': favorite_categories,
    }
    
    return render(request, 'users/profile.html', context)


@login_required
@require_http_methods(["POST"])
def profile_edit_view(request: HttpRequest) -> JsonResponse:
    """
    Handle profile editing via AJAX.
    """
    try:
        user = request.user
        
        # Update user fields safely
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        full_name = request.POST.get('full_name', '').strip()
        phone = request.POST.get('phone', '').strip()
        
        # Validate required fields
        if not first_name or not last_name:
            return JsonResponse({
                'success': False,
                'message': 'First name and last name are required.'
            }, status=400)
        
        # Update fields one by one to avoid validation issues
        user.first_name = first_name
        user.last_name = last_name
        
        # Only update full_name if provided, otherwise use first + last
        if full_name:
            user.full_name = full_name
        else:
            user.full_name = f"{first_name} {last_name}"
        
        # Update phone if provided
        if phone:
            user.phone = phone
        
        # Handle avatar upload separately (if avatar field exists)
        avatar_url = None
        fields_to_update = ['first_name', 'last_name', 'full_name']
        
        if phone:
            fields_to_update.append('phone')
            
        if 'avatar' in request.FILES and request.FILES['avatar']:
            avatar_file = request.FILES['avatar']
            
            # Basic file validation
            if avatar_file.size > 2 * 1024 * 1024:  # 2MB limit
                return JsonResponse({
                    'success': False,
                    'message': 'Avatar file size must be less than 2MB.'
                }, status=400)
            
            if not avatar_file.content_type.startswith('image/'):
                return JsonResponse({
                    'success': False,
                    'message': 'Avatar must be an image file.'
                }, status=400)
            
            # Check if user model has avatar field
            if hasattr(user, 'avatar'):
                user.avatar = avatar_file
                avatar_url = user.avatar.url
                fields_to_update.append('avatar')
            else:
                # Avatar field doesn't exist in model, skip this functionality
                return JsonResponse({
                    'success': False,
                    'message': 'Avatar upload not supported yet. Please update your name and phone instead.'
                }, status=400)
        
        # Save the user with only specific fields to avoid boolean validation issues
        user.save(update_fields=fields_to_update)
        
        return JsonResponse({
            'success': True,
            'message': 'Profile updated successfully!',
            'data': {
                'display_name': user.get_display_name(),
                'first_name': user.first_name,
                'last_name': user.last_name,
                'full_name': user.full_name,
                'phone': user.phone or '',
                'avatar_url': avatar_url or (user.avatar.url if hasattr(user, 'avatar') and user.avatar else None),
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()  # For debugging
        return JsonResponse({
            'success': False,
            'message': f'Error updating profile: {str(e)}'
        }, status=400)


@login_required
@require_http_methods(["POST"])
def password_change_view(request: HttpRequest) -> JsonResponse:
    """
    Handle password change via AJAX.
    """
    try:
        form = PasswordChangeForm(user=request.user, data=request.POST)
        
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep user logged in
            
            return JsonResponse({
                'success': True,
                'message': 'Password changed successfully!'
            })
        else:
            errors = []
            for field, field_errors in form.errors.items():
                for error in field_errors:
                    errors.append(f"{field}: {error}")
            
            return JsonResponse({
                'success': False,
                'message': 'Please correct the following errors: ' + ', '.join(errors)
            }, status=400)
            
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error changing password: {str(e)}'
        }, status=400)


@login_required
@require_http_methods(["POST"])
def preferences_update_view(request: HttpRequest) -> JsonResponse:
    """
    Handle preferences update via AJAX.
    """
    try:
        user = request.user
        
        # Get or create user preferences
        try:
            preferences = user.preferences
        except UserPreferences.DoesNotExist:
            preferences = UserPreferences.objects.create(user=user)
        
        # Update preferences
        preferences.default_search_radius_km = int(request.POST.get('search_radius', 10))
        preferences.theme = request.POST.get('theme', 'light')
        preferences.language = request.POST.get('language', 'en')
        preferences.email_notifications = request.POST.get('email_notifications') == 'on'
        preferences.emergency_alerts = request.POST.get('emergency_alerts') == 'on'
        preferences.service_updates = request.POST.get('service_updates') == 'on'
        preferences.profile_public = request.POST.get('profile_public') == 'on'
        preferences.location_sharing = request.POST.get('location_sharing') == 'on'
        
        preferences.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Preferences saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error saving preferences: {str(e)}'
        }, status=400)


@login_required
def notifications_view(request: HttpRequest) -> HttpResponse:
    """
    User notifications and alerts.
    """
    user = request.user
    
    # For now, we'll simulate notifications based on user activity
    # In a real app, you'd have a proper notification system
    
    notifications = []
    
    # Service updates for bookmarked services
    bookmarked_services = ServiceBookmark.objects.filter(
        user=user
    ).select_related('service')
    
    for bookmark in bookmarked_services:
        service = bookmark.service
        # Check if service has recent updates
        recent_updates = service.status_updates.filter(
            created_at__gte=bookmark.last_accessed
        ).order_by('-created_at')[:3]
        
        for update in recent_updates:
            notifications.append({
                'type': 'service_update',
                'title': f"Update for {service.name}",
                'message': update.message or f"Status changed to {update.new_status}",
                'service': service,
                'timestamp': update.created_at,
                'unread': True,
            })
    
    # Sort notifications by timestamp
    notifications.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'notifications': notifications[:20],  # Limit to 20 most recent
        'unread_count': len([n for n in notifications if n.get('unread', False)]),
    }
    
    return render(request, 'users/notifications.html', context)


class UserPreferencesUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update user preferences and settings.
    """
    model = UserPreferences
    template_name = 'users/preferences.html'
    fields = [
        'theme', 'language', 'default_map_zoom', 'show_user_location',
        'default_search_radius_km', 'preferred_categories',
        'email_notifications', 'sms_notifications', 'emergency_alerts',
        'service_updates', 'profile_public', 'reviews_anonymous',
        'location_sharing'
    ]
    
    def get_object(self):
        """Get or create preferences for current user."""
        try:
            return self.request.user.preferences
        except UserPreferences.DoesNotExist:
            return UserPreferences.objects.create(user=self.request.user)
    
    def get_success_url(self):
        messages.success(self.request, _('Preferences updated successfully!'))
        return reverse('users:profile')


@login_required
def bookmark_toggle_view(request: HttpRequest) -> JsonResponse:
    """
    AJAX view to toggle service bookmarks.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)
    
    try:
        data = json.loads(request.body)
        service_id = data.get('service_id')
        folder_name = data.get('folder_name', '')
        
        service = get_object_or_404(Service, pk=service_id)
        
        bookmark, created = ServiceBookmark.objects.get_or_create(
            user=request.user,
            service=service,
            defaults={'folder_name': folder_name}
        )
        
        if not created:
            # Remove bookmark
            bookmark.delete()
            bookmarked = False
            
            # Record activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='remove_bookmark',
                service=service
            )
        else:
            bookmarked = True
            
            # Record activity
            UserActivity.objects.create(
                user=request.user,
                activity_type='bookmark_service',
                service=service,
                metadata={'folder': folder_name}
            )
        
        return JsonResponse({
            'bookmarked': bookmarked,
            'bookmark_count': ServiceBookmark.objects.filter(user=request.user).count()
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
def search_history_view(request: HttpRequest) -> HttpResponse:
    """
    View user's search history with analytics.
    """
    user = request.user
    
    # Get search history
    searches = SearchHistory.objects.filter(
        user=user
    ).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(searches, 20)
    page_number = request.GET.get('page')
    searches_page = paginator.get_page(page_number)
    
    # Search analytics
    analytics = {
        'total_searches': searches.count(),
        'unique_queries': searches.values('query').distinct().count(),
        'top_categories': searches.exclude(
            category_filter=''
        ).values('category_filter').annotate(
            count=Count('category_filter')
        ).order_by('-count')[:5],
        'avg_results': searches.aggregate(avg=Avg('results_count'))['avg'] or 0,
    }
    
    context = {
        'searches': searches_page,
        'analytics': analytics,
    }
    
    return render(request, 'users/search_history.html', context)


# Helper functions for recommendations

def get_user_recommendations(user) -> List[Service]:
    """
    Get personalized recommendations for a user.
    """
    # Simple recommendation based on bookmarked service categories
    bookmarked_categories = ServiceCategory.objects.filter(
        services__bookmarked_by__user=user
    ).distinct()
    
    if bookmarked_categories.exists():
        recommended = Service.objects.filter(
            category__in=bookmarked_categories,
            is_active=True,
            is_verified=True
        ).exclude(
            bookmarked_by__user=user  # Exclude already bookmarked
        ).annotate(
            avg_rating=Avg('reviews__rating')
        ).order_by('-avg_rating')[:6]
    else:
        # For new users, show highly rated services
        recommended = Service.objects.filter(
            is_active=True,
            is_verified=True
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).filter(review_count__gte=5).order_by('-avg_rating')[:6]
    
    return recommended


def get_personalized_recommendations(user) -> List[Service]:
    """
    Advanced personalized recommendations.
    """
    return get_user_recommendations(user)


def get_trending_services() -> List[Service]:
    """
    Get currently trending services.
    """
    # Services with recent activity
    week_ago = timezone.now() - timedelta(days=7)
    
    trending = Service.objects.filter(
        is_active=True,
        is_verified=True,
        reviews__created_at__gte=week_ago
    ).annotate(
        recent_reviews=Count('reviews__created_at')
    ).order_by('-recent_reviews')[:6]
    
    return trending


def get_nearby_recommendations(user) -> List[Service]:
    """
    Get services near user's location.
    """
    if not (user.preferred_location_lat and user.preferred_location_lng):
        return []
    
    # Simple proximity recommendation (would use PostGIS distance in production)
    nearby = Service.objects.filter(
        is_active=True,
        is_verified=True
    ).exclude(
        bookmarked_by__user=user
    ).order_by('?')[:6]  # Random for now, would be distance-based
    
    return nearby


def get_similar_user_recommendations(user) -> List[Service]:
    """
    Recommendations based on similar users' bookmarks.
    """
    # Find users with similar bookmark patterns
    user_categories = set(ServiceCategory.objects.filter(
        services__bookmarked_by__user=user
    ).values_list('pk', flat=True))
    
    if not user_categories:
        return []
    
    # Find similar users (simplified collaborative filtering)
    similar_users = []
    for other_user in ServiceBookmark.objects.exclude(
        user=user
    ).values('user').distinct()[:50]:  # Limit for performance
        
        other_user_id = other_user['user']
        other_categories = set(ServiceCategory.objects.filter(
            services__bookmarked_by__user_id=other_user_id
        ).values_list('pk', flat=True))
        
        # Calculate similarity (Jaccard index)
        if other_categories:
            similarity = len(user_categories & other_categories) / len(user_categories | other_categories)
            if similarity > 0.3:  # Threshold for similarity
                similar_users.append(other_user_id)
    
    if similar_users:
        # Get services bookmarked by similar users but not by current user
        recommendations = Service.objects.filter(
            bookmarked_by__user_id__in=similar_users,
            is_active=True,
            is_verified=True
        ).exclude(
            bookmarked_by__user=user
        ).annotate(
            bookmark_count=Count('bookmarked_by')
        ).order_by('-bookmark_count')[:6]
        
        return recommendations
    
    return [] 