from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
# from django.contrib.gis.geos import Point  # Commented out for now
# from django.contrib.gis.measure import Distance  # Commented out for now
from django.http import JsonResponse, Http404
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg, F, Case, When
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse_lazy, reverse
from django.utils.translation import gettext_lazy as _
from typing import Dict, Any, Optional, List
import json

from .models import Service, ServiceCategory, RealTimeStatusUpdate
# from .strategies import SearchStrategyFactory  # Commented out until PostGIS is available
from apps.users.models import ServiceBookmark, SearchHistory
from apps.core.utils import RoleRequiredMixin


class ServiceListView(ListView):
    """
    Display paginated list of active services with basic filtering.
    """
    model = Service
    template_name = 'services/service_list.html'
    context_object_name = 'services'
    paginate_by = 12
    
    def get_queryset(self):
        """Filter active services with category and search."""
        queryset = Service.objects.filter(is_active=True).select_related('category', 'manager')
        
        # Category filter
        category = self.request.GET.get('category')
        if category:
            queryset = queryset.filter(category__slug=category)
            
        # Enhanced search functionality
        search_query = self.request.GET.get('search')  # Check for 'search' parameter
        if not search_query:
            search_query = self.request.GET.get('q')  # Fallback to 'q' parameter
            
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(address__icontains=search_query) |
                Q(category__name__icontains=search_query)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status == 'emergency':
            queryset = queryset.filter(is_emergency_service=True)
        elif status == 'open':
            queryset = queryset.filter(current_status='open')
        elif status == 'available':
            queryset = queryset.filter(
                Q(current_status='open') & 
                Q(current_capacity__lt=F('max_capacity'))
            )
            
        # Distance filter with basic coordinate calculation
        distance = self.request.GET.get('distance')
        user_lat = self.request.GET.get('lat')
        user_lng = self.request.GET.get('lng')
        
        if distance and user_lat and user_lng:
            try:
                distance_km = float(distance)
                user_latitude = float(user_lat)
                user_longitude = float(user_lng)
                
                # Filter services within distance using Haversine formula approximation
                queryset = self._filter_by_distance(queryset, user_latitude, user_longitude, distance_km)
            except (ValueError, TypeError):
                # Invalid coordinates or distance, ignore filter
                pass
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'relevance')
        if sort_by == 'name':
            queryset = queryset.order_by('name')
        elif sort_by == 'category':
            queryset = queryset.order_by('category__name', 'name')
        elif sort_by == 'rating':
            # TODO: Add rating field to Service model
            queryset = queryset.order_by('-created_at')
        elif sort_by == 'distance' and user_lat and user_lng:
            # If distance sorting is requested and location is available, handle in template
            # The distance calculation is done during filtering, so we'll sort by calculated distance
            queryset = queryset.order_by('-created_at')  # Default ordering, will be handled in _filter_by_distance
        else:  # relevance (default)
            if search_query:
                # Prioritize exact name matches, then description matches
                queryset = queryset.extra(
                    select={
                        'name_match': "CASE WHEN LOWER(services_service.name) LIKE LOWER(%s) THEN 1 ELSE 0 END",
                    },
                    select_params=[f'%{search_query}%']
                ).order_by('-name_match', '-created_at')
            else:
                queryset = queryset.order_by('-created_at')
            
        return queryset
    
    def _filter_by_distance(self, queryset, user_lat, user_lng, max_distance_km):
        """
        Filter services within specified distance using Haversine formula.
        This is a basic implementation without PostGIS.
        """
        import math
        
        def haversine_distance(lat1, lon1, lat2, lon2):
            """Calculate distance between two points in kilometers using Haversine formula."""
            # Convert latitude and longitude from degrees to radians
            lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
            
            # Haversine formula
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
            c = 2 * math.asin(math.sqrt(a))
            r = 6371  # Radius of Earth in kilometers
            return c * r
        
        # Calculate distances and filter
        services_with_distance = []
        for service in queryset:
            try:
                distance = haversine_distance(
                    user_lat, user_lng, 
                    service.latitude, service.longitude
                )
                if distance <= max_distance_km:
                    # Add distance as an attribute for potential sorting and display
                    service.calculated_distance = round(distance, 2)
                    services_with_distance.append((service.id, distance))
            except (TypeError, AttributeError):
                # Service has invalid coordinates, skip
                continue
        
        # Check if distance sorting is requested
        sort_by = self.request.GET.get('sort')
        if sort_by == 'distance':
            # Sort by distance and extract IDs
            services_with_distance.sort(key=lambda x: x[1])
            filtered_service_ids = [service_id for service_id, _ in services_with_distance]
            
            # Return queryset maintaining the distance-sorted order
            preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(filtered_service_ids)])
            return queryset.filter(id__in=filtered_service_ids).order_by(preserved_order)
        else:
            # Return queryset filtered by IDs without distance sorting
            filtered_service_ids = [service_id for service_id, _ in services_with_distance]
            return queryset.filter(id__in=filtered_service_ids)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        context['current_category'] = self.request.GET.get('category')
        context['search_query'] = self.request.GET.get('search') or self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status')
        context['current_sort'] = self.request.GET.get('sort', 'relevance')
        context['current_distance'] = self.request.GET.get('distance')
        context['current_lat'] = self.request.GET.get('lat')
        context['current_lng'] = self.request.GET.get('lng')
        return context


class ServiceDetailView(DetailView):
    """
    Display detailed information about a specific service.
    """
    model = Service
    template_name = 'services/service_detail.html'
    context_object_name = 'service'
    
    def get_queryset(self):
        return Service.objects.filter(is_active=True).select_related(
            'category', 'manager'
        ).prefetch_related('status_updates')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check if user has bookmarked this service
        if self.request.user.is_authenticated:
            context['is_bookmarked'] = ServiceBookmark.objects.filter(
                user=self.request.user,
                service=self.object
            ).exists()
        
        # Get recent status updates
        context['recent_updates'] = self.object.status_updates.order_by('-created_at')[:5]
        
        # Add reviews and comments
        from apps.feedback.models import ServiceReview, ServiceComment
        context['reviews'] = ServiceReview.objects.filter(
            service=self.object,
            is_verified=True
        ).select_related('user').order_by('-created_at')[:5]
        
        context['comments'] = ServiceComment.objects.filter(
            service=self.object,
            is_approved=True,
            parent=None
        ).select_related('user').prefetch_related('replies').order_by('-created_at')[:5]
        
        # Review statistics
        from django.db.models import Avg, Count
        reviews = ServiceReview.objects.filter(service=self.object, is_verified=True)
        context['review_stats'] = {
            'total_count': reviews.count(),
            'average_rating': reviews.aggregate(avg=Avg('rating'))['avg'] or 0,
        }
        
        # Get nearby services - commented out until PostGIS is available
        # if self.object.location:
        #     nearby_services = Service.objects.filter(
        #         is_active=True,
        #         location__distance_lte=(self.object.location, Distance(km=5))
        #     ).exclude(pk=self.object.pk)[:5]
        #     context['nearby_services'] = nearby_services
            
        return context


class ServiceSearchView(ListView):
    """
    Advanced service search with geographic and semantic filtering.
    """
    model = Service
    template_name = 'services/service_search.html'
    context_object_name = 'services'
    paginate_by = 20
    
    def get_queryset(self):
        """Use search strategies for advanced filtering."""
        query = self.request.GET.get('q', '')
        lat = self.request.GET.get('lat')
        lng = self.request.GET.get('lng')
        radius = self.request.GET.get('radius', '10')
        category = self.request.GET.get('category')
        
        # Create search context
        search_context = {
            'query': query,
            'category': category,
            'emergency_only': self.request.GET.get('emergency') == 'true'
        }
        
        if lat and lng:
            try:
                # search_context['location'] = Point(float(lng), float(lat))  # Commented out for now
                search_context['radius_km'] = float(radius)
            except (ValueError, TypeError):
                pass
        
        # Use appropriate search strategy - simplified for now
        # TODO: Re-enable when PostGIS is available
        # if search_context.get('emergency_only'):
        #     strategy = SearchStrategyFactory.create_strategy('emergency')
        # elif search_context.get('location'):
        #     strategy = SearchStrategyFactory.create_strategy('geographic')
        # elif query:
        #     strategy = SearchStrategyFactory.create_strategy('smart')
        # else:
        #     strategy = SearchStrategyFactory.create_strategy('basic')
        # 
        # results = strategy.search(search_context)
        
        # Simple fallback search for now
        results = Service.objects.filter(is_active=True)
        if query:
            results = results.filter(
                Q(name__icontains=query) | 
                Q(description__icontains=query)
            )
        if category:
            results = results.filter(category__slug=category)
        if search_context.get('emergency_only'):
            results = results.filter(is_emergency_service=True)
        
        results = results.order_by('-created_at')
        
        # Record search history
        if query or search_context.get('location'):
            self._record_search_history(search_context, len(results))
            
        return results
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        context['search_form_data'] = {
            'q': self.request.GET.get('q', ''),
            'lat': self.request.GET.get('lat', ''),
            'lng': self.request.GET.get('lng', ''),
            'radius': self.request.GET.get('radius', '10'),
            'category': self.request.GET.get('category', ''),
            'emergency': self.request.GET.get('emergency', 'false')
        }
        return context
    
    def _record_search_history(self, search_context: Dict, results_count: int):
        """Record search for analytics and recommendations."""
        SearchHistory.objects.create(
            user=self.request.user if self.request.user.is_authenticated else None,
            query=search_context.get('query', ''),
            search_location=search_context.get('location', ''),  # Default to empty string instead of None
            search_radius_km=search_context.get('radius_km'),
            category_filter=search_context.get('category', ''),
            results_count=results_count,
            session_id=self.request.session.session_key or '',
            ip_address=self.request.META.get('REMOTE_ADDR')
        )


class ServiceMapView(ListView):
    """
    Map view showing services as markers.
    """
    model = Service
    template_name = 'services/service_map.html'
    context_object_name = 'services'
    
    def get_queryset(self):
        return Service.objects.filter(
            is_active=True,
            # location__isnull=False  # Commented out until PostGIS is available
        ).select_related('category')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = ServiceCategory.objects.filter(is_active=True)
        return context


class CategoryDetailView(DetailView):
    """
    Display services within a specific category.
    """
    model = ServiceCategory
    template_name = 'services/category_detail.html'
    context_object_name = 'category'
    slug_field = 'slug'
    slug_url_kwarg = 'category_slug'
    paginate_by = 12
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get services in this category with filtering
        services = Service.objects.filter(
            category=self.object,
            is_active=True
        ).select_related('category', 'manager')
        
        # Apply search filters
        search_query = self.request.GET.get('q')
        if search_query:
            services = services.filter(
                Q(name__icontains=search_query) | 
                Q(description__icontains=search_query) |
                Q(address__icontains=search_query)
            )
        
        # Status filter
        status = self.request.GET.get('status')
        if status == 'emergency':
            services = services.filter(is_emergency_service=True)
        elif status == 'open':
            services = services.filter(current_status='open')
        elif status == 'available':
            services = services.filter(
                Q(current_status='open') & 
                Q(current_capacity__lt=F('max_capacity'))
            )
        
        # Sorting
        sort_by = self.request.GET.get('sort', 'name')
        if sort_by == 'name':
            services = services.order_by('name')
        elif sort_by == 'rating':
            # TODO: Add proper rating sorting
            services = services.order_by('-created_at')
        elif sort_by == 'recent':
            services = services.order_by('-created_at')
        else:
            services = services.order_by('name')
        
        # Paginate services
        paginator = Paginator(services, self.paginate_by)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        
        context['services'] = page_obj
        context['is_paginated'] = page_obj.has_other_pages()
        context['page_obj'] = page_obj
        
        # Category statistics
        all_services = Service.objects.filter(category=self.object, is_active=True)
        context['total_services'] = all_services.count()
        context['open_services'] = all_services.filter(current_status='open').count()
        context['emergency_services'] = all_services.filter(is_emergency_service=True).count()
        context['free_services'] = all_services.filter(is_free=True).count()
        
        # Related categories (other active categories)
        context['related_categories'] = ServiceCategory.objects.filter(
            is_active=True
        ).exclude(pk=self.object.pk)[:4]
        
        return context


# API Views
class ServiceSearchAPIView(ListView):
    """
    JSON API for service search - used by AJAX requests.
    """
    model = Service
    
    def get(self, request, *args, **kwargs):
        # Similar logic to ServiceSearchView but return JSON
        pass  # Implementation would mirror ServiceSearchView


class ServiceCategoryAPIView(ListView):
    """
    JSON API for service categories.
    """
    model = ServiceCategory
    
    def get(self, request, *args, **kwargs):
        categories = ServiceCategory.objects.filter(is_active=True).values(
            'id', 'name', 'slug', 'icon_class'
        )
        return JsonResponse({'categories': list(categories)})


class BookmarkToggleAPIView(LoginRequiredMixin, ListView):
    """
    AJAX endpoint for toggling service bookmarks.
    """
    
    def post(self, request, *args, **kwargs):
        service_id = kwargs.get('service_id')
        service = get_object_or_404(Service, id=service_id, is_active=True)
        
        bookmark, created = ServiceBookmark.objects.get_or_create(
            user=request.user,
            service=service
        )
        
        if not created:
            bookmark.delete()
            bookmarked = False
        else:
            bookmarked = True
            
        return JsonResponse({
            'success': True,
            'bookmarked': bookmarked,
            'bookmark_count': service.bookmarked_by.count()
        })


class MapDataAPIView(ListView):
    """
    JSON API for map markers data.
    """
    model = Service
    
    def get(self, request, *args, **kwargs):
        services = Service.objects.filter(
            is_active=True,
            location__isnull=False
        ).select_related('category')
        
        markers = []
        for service in services:
            markers.append({
                'id': str(service.id),
                'name': service.name,
                'lat': service.location.y,
                'lng': service.location.x,
                'category': service.category.name,
                'category_icon': service.category.icon_class,
                'is_emergency': service.is_emergency_service,
                'url': reverse('services:detail', kwargs={'pk': service.pk})
            })
            
        return JsonResponse({'markers': markers})


# Management Views (for Service Managers)
class ServiceManagementView(LoginRequiredMixin, RoleRequiredMixin, ListView):
    """
    Dashboard for service managers to view their services.
    """
    model = Service
    template_name = 'services/manage/dashboard.html'
    context_object_name = 'services'
    required_roles = ['service_manager', 'admin']
    
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Service.objects.all()
        return Service.objects.filter(manager=self.request.user)


class ServiceCreateView(LoginRequiredMixin, RoleRequiredMixin, CreateView):
    """
    Create new service listing.
    """
    model = Service
    template_name = 'services/manage/service_form.html'
    fields = ['name', 'description', 'category', 'address', 'phone', 'email', 'website']
    required_roles = ['service_manager', 'admin']
    
    def form_valid(self, form):
        form.instance.manager = self.request.user
        messages.success(self.request, _('Service created successfully!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('services:manage')


class ServiceUpdateView(LoginRequiredMixin, RoleRequiredMixin, UpdateView):
    """
    Edit existing service listing.
    """
    model = Service
    template_name = 'services/manage/service_form.html'
    fields = ['name', 'description', 'category', 'address', 'phone', 'email', 'website']
    required_roles = ['service_manager', 'admin']
    
    def get_queryset(self):
        if self.request.user.role == 'admin':
            return Service.objects.all()
        return Service.objects.filter(manager=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, _('Service updated successfully!'))
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('services:manage') 