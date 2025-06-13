"""
Strategy Pattern implementation for service search algorithms.

This module implements different search strategies for Service Managers
to find and filter their services efficiently.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from django.db.models import QuerySet, Q, F
from django.utils import timezone
from datetime import datetime, timedelta


class ServiceSearchStrategy(ABC):
    """
    Abstract base class for service search strategies.
    
    Implements the Strategy pattern for different search algorithms
    that managers can use to find and filter their services.
    """
    
    @abstractmethod
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Execute the search strategy.
        
        Args:
            queryset: Base queryset to search within
            params: Search parameters dictionary
            
        Returns:
            Filtered queryset
        """
        pass


class CategorySearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by category.
    
    Allows managers to find services within specific categories
    or multiple categories.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by category.
        
        Expected params:
        - category: Single category slug
        - categories: List of category slugs
        """
        if 'category' in params and params['category']:
            return queryset.filter(category__slug=params['category'])
        
        if 'categories' in params and params['categories']:
            return queryset.filter(category__slug__in=params['categories'])
        
        return queryset


class StatusSearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by operational status.
    
    Helps managers quickly find services that need attention
    based on their current status.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by status.
        
        Expected params:
        - status: Single status value
        - statuses: List of status values
        - needs_attention: Boolean for services requiring updates
        """
        if 'status' in params and params['status']:
            queryset = queryset.filter(current_status=params['status'])
        
        if 'statuses' in params and params['statuses']:
            queryset = queryset.filter(current_status__in=params['statuses'])
        
        if params.get('needs_attention'):
            # Services that haven't been updated in 24 hours
            cutoff = timezone.now() - timedelta(hours=24)
            queryset = queryset.filter(
                Q(capacity_last_updated__lt=cutoff) |
                Q(current_status='closed') |
                Q(current_capacity__gte=90)  # Near capacity
            )
        
        return queryset


class CapacitySearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by capacity status.
    
    Allows managers to find services based on their current
    capacity levels and availability.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by capacity.
        
        Expected params:
        - capacity_min: Minimum capacity percentage
        - capacity_max: Maximum capacity percentage
        - near_capacity: Boolean for services near capacity (>80%)
        - at_capacity: Boolean for services at full capacity
        """
        if 'capacity_min' in params and params['capacity_min'] is not None:
            # Calculate capacity percentage
            queryset = queryset.extra(
                where=["(current_capacity * 100.0 / NULLIF(max_capacity, 0)) >= %s"],
                params=[params['capacity_min']]
            )
        
        if 'capacity_max' in params and params['capacity_max'] is not None:
            queryset = queryset.extra(
                where=["(current_capacity * 100.0 / NULLIF(max_capacity, 0)) <= %s"],
                params=[params['capacity_max']]
            )
        
        if params.get('near_capacity'):
            # Services at 80% or higher capacity
            queryset = queryset.extra(
                where=["(current_capacity * 100.0 / NULLIF(max_capacity, 0)) >= 80"]
            )
        
        if params.get('at_capacity'):
            # Services at 100% capacity
            queryset = queryset.filter(current_capacity__gte=F('max_capacity'))
        
        return queryset


class AnalyticsSearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by analytics metrics.
    
    Helps managers find services based on performance metrics
    like ratings, visit counts, and feedback.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by analytics data.
        
        Expected params:
        - min_rating: Minimum average rating
        - max_rating: Maximum average rating
        - min_visits: Minimum visit count
        - recent_feedback: Boolean for services with recent feedback
        - low_rating: Boolean for services with low ratings (<3.0)
        """
        if 'min_rating' in params and params['min_rating'] is not None:
            queryset = queryset.filter(quality_score__gte=params['min_rating'])
        
        if 'max_rating' in params and params['max_rating'] is not None:
            queryset = queryset.filter(quality_score__lte=params['max_rating'])
        
        if 'min_visits' in params and params['min_visits'] is not None:
            # This would need to join with analytics data
            # For now, we'll use a placeholder approach
            queryset = queryset.filter(total_ratings__gte=params['min_visits'])
        
        if params.get('recent_feedback'):
            # Services with feedback in the last 7 days
            cutoff = timezone.now() - timedelta(days=7)
            queryset = queryset.filter(reviews__created_at__gte=cutoff).distinct()
        
        if params.get('low_rating'):
            # Services with ratings below 3.0
            queryset = queryset.filter(quality_score__lt=3.0)
        
        return queryset


class ApprovalStatusSearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by approval status.
    
    Allows managers to filter between verified and pending services.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by approval status.
        
        Expected params:
        - approval_status: 'pending' or 'verified'
        """
        approval_status = params.get('approval_status')
        
        if approval_status == 'pending':
            return queryset.filter(is_verified=False)
        elif approval_status == 'verified':
            return queryset.filter(is_verified=True)
        
        return queryset


class TextSearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for text-based searching.
    
    Implements full-text search across service names,
    descriptions, and tags.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Perform text search across service fields.
        
        Expected params:
        - query: Text query string
        - search_fields: List of fields to search in
        """
        query = params.get('query', '').strip()
        if not query:
            return queryset
        
        search_fields = params.get('search_fields', ['name', 'description', 'short_description'])
        
        # Build Q objects for each search field
        q_objects = Q()
        for field in search_fields:
            if field == 'name':
                q_objects |= Q(name__icontains=query)
            elif field == 'description':
                q_objects |= Q(description__icontains=query)
            elif field == 'short_description':
                q_objects |= Q(short_description__icontains=query)
            elif field == 'address':
                q_objects |= Q(address__icontains=query)
            elif field == 'tags':
                q_objects |= Q(tags__icontains=query)
        
        return queryset.filter(q_objects)


class DateRangeSearchStrategy(ServiceSearchStrategy):
    """
    Search strategy for filtering services by date ranges.
    
    Useful for finding services created, updated, or modified
    within specific time periods.
    """
    
    def search(self, queryset: QuerySet, params: Dict[str, Any]) -> QuerySet:
        """
        Filter services by date ranges.
        
        Expected params:
        - created_after: Filter services created after this date
        - created_before: Filter services created before this date
        - updated_after: Filter services updated after this date
        - updated_before: Filter services updated before this date
        """
        if 'created_after' in params and params['created_after']:
            queryset = queryset.filter(created_at__gte=params['created_after'])
        
        if 'created_before' in params and params['created_before']:
            queryset = queryset.filter(created_at__lte=params['created_before'])
        
        if 'updated_after' in params and params['updated_after']:
            queryset = queryset.filter(updated_at__gte=params['updated_after'])
        
        if 'updated_before' in params and params['updated_before']:
            queryset = queryset.filter(updated_at__lte=params['updated_before'])
        
        return queryset


class ServiceSearchContext:
    """
    Context class for executing service search strategies.
    
    Manages multiple search strategies and combines their results
    to provide comprehensive search functionality for service managers.
    """
    
    def __init__(self):
        self.strategies = {
            'category': CategorySearchStrategy(),
            'status': StatusSearchStrategy(),
            'capacity': CapacitySearchStrategy(),
            'analytics': AnalyticsSearchStrategy(),
            'approval': ApprovalStatusSearchStrategy(),
            'text': TextSearchStrategy(),
            'date_range': DateRangeSearchStrategy(),
        }
    
    def search(self, queryset: QuerySet, search_params: Dict[str, Any]) -> QuerySet:
        """
        Execute multiple search strategies based on provided parameters.
        
        Args:
            queryset: Base queryset to search within
            search_params: Dictionary of search parameters
            
        Returns:
            Filtered queryset with all applicable strategies applied
        """
        result_queryset = queryset
        
        # Apply each strategy if relevant parameters are present
        for strategy_name, strategy in self.strategies.items():
            # Filter params relevant to this strategy
            strategy_params = self._get_strategy_params(strategy_name, search_params)
            if strategy_params:
                result_queryset = strategy.search(result_queryset, strategy_params)
        
        return result_queryset.distinct()
    
    def _get_strategy_params(self, strategy_name: str, all_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract parameters relevant to a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            all_params: All search parameters
            
        Returns:
            Parameters relevant to the specified strategy
        """
        strategy_param_mapping = {
            'category': ['category', 'categories'],
            'status': ['status', 'statuses', 'needs_attention'],
            'capacity': ['capacity_min', 'capacity_max', 'near_capacity', 'at_capacity'],
            'analytics': ['min_rating', 'max_rating', 'min_visits', 'recent_feedback', 'low_rating'],
            'approval': ['approval_status'],
            'text': ['query', 'search_fields'],
            'date_range': ['created_after', 'created_before', 'updated_after', 'updated_before'],
        }
        
        relevant_keys = strategy_param_mapping.get(strategy_name, [])
        return {key: all_params[key] for key in relevant_keys if key in all_params} 