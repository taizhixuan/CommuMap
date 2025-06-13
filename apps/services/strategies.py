"""
Service search strategies implementing the Strategy pattern.

This module provides different search algorithms for service discovery,
allowing the system to choose the most appropriate search method
based on user context and requirements.
"""
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
# from django.contrib.gis.db.models import QuerySet  # Commented out for now
from django.db.models import QuerySet  # Using regular QuerySet for now
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from datetime import datetime, timedelta

from .models import Service, ServiceCategory


class SearchStrategy(ABC):
    """
    Abstract base class for service search strategies.
    
    Implements the Strategy pattern to allow different search algorithms
    to be used interchangeably based on user needs and context.
    """
    
    @abstractmethod
    def search(self, queryset: QuerySet, **kwargs) -> QuerySet:
        """
        Execute the search strategy on the given queryset.
        
        Args:
            queryset: Base Service queryset to filter
            **kwargs: Strategy-specific parameters
            
        Returns:
            Filtered and ordered queryset
        """
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        """Return the strategy name for logging/debugging."""
        pass
    
    def get_description(self) -> str:
        """Return a description of what this strategy does."""
        return self.__doc__ or "No description available."


class BasicTextSearchStrategy(SearchStrategy):
    """
    Basic text search across service name, description, and tags.
    
    Performs case-insensitive text matching across multiple fields
    with simple relevance scoring.
    """
    
    def search(self, queryset: QuerySet, query: str = '', **kwargs) -> QuerySet:
        """Search services using basic text matching."""
        if not query:
            return queryset.order_by('name')
        
        query_lower = query.lower().strip()
        
        # Use the pre-computed search vector for efficiency
        return queryset.filter(
            search_vector__icontains=query_lower
        ).order_by('name')
    
    def get_name(self) -> str:
        return "basic_text"


class GeographicSearchStrategy(SearchStrategy):
    """
    Geographic search based on distance from a central point.
    
    Orders results by distance from the user's location with optional
    distance filtering.
    """
    
    def search(self, queryset: QuerySet, 
              user_location: Point,
              max_distance_km: Optional[float] = None,
              **kwargs) -> QuerySet:
        """Search services by geographic proximity."""
        if not user_location:
            return queryset.order_by('name')
        
        # Filter by distance if specified
        if max_distance_km:
            queryset = queryset.filter(
                location__distance_lte=(user_location, Distance(km=max_distance_km))
            )
        
        # Order by distance
        return queryset.annotate(
            distance=F('location').distance(user_location)
        ).order_by('distance')
    
    def get_name(self) -> str:
        return "geographic"


class CategorySearchStrategy(SearchStrategy):
    """
    Category-based search with subcategory support.
    
    Filters services by primary category and orders by relevance
    within the category.
    """
    
    def search(self, queryset: QuerySet, 
              category_slug: str = '',
              category_type: str = '',
              **kwargs) -> QuerySet:
        """Search services by category."""
        
        # Filter by specific category slug
        if category_slug:
            queryset = queryset.filter(category__slug=category_slug)
        # Or filter by category type
        elif category_type:
            queryset = queryset.filter(category__category_type=category_type)
        
        # Order by quality score within category
        return queryset.order_by('-quality_score', 'name')
    
    def get_name(self) -> str:
        return "category"


class EmergencySearchStrategy(SearchStrategy):
    """
    Emergency-focused search for urgent service discovery.
    
    Prioritizes emergency services that are currently open and
    orders by distance from user location.
    """
    
    def search(self, queryset: QuerySet,
              user_location: Point,
              max_distance_km: float = 5,
              **kwargs) -> QuerySet:
        """Search for emergency services near user location."""
        
        # Filter to emergency services only
        queryset = queryset.filter(
            is_emergency_service=True,
            current_status__in=[ServiceStatus.OPEN, ServiceStatus.LIMITED, ServiceStatus.EMERGENCY_ONLY]
        )
        
        # Filter by distance
        if user_location:
            queryset = queryset.filter(
                location__distance_lte=(user_location, Distance(km=max_distance_km))
            )
            
            # Order by distance and priority
            queryset = queryset.annotate(
                distance=F('location').distance(user_location),
                # Emergency services get priority boost
                priority_score=Case(
                    When(current_status=ServiceStatus.EMERGENCY_ONLY, then=Value(3)),
                    When(current_status=ServiceStatus.OPEN, then=Value(2)),
                    When(current_status=ServiceStatus.LIMITED, then=Value(1)),
                    default=Value(0),
                    output_field=IntegerField(),
                )
            ).order_by('-priority_score', 'distance')
        else:
            queryset = queryset.order_by('-quality_score')
        
        return queryset
    
    def get_name(self) -> str:
        return "emergency"


class AvailabilitySearchStrategy(SearchStrategy):
    """
    Availability-focused search prioritizing open services with capacity.
    
    Orders results by availability, capacity status, and quality.
    """
    
    def search(self, queryset: QuerySet, 
              include_full: bool = False,
              **kwargs) -> QuerySet:
        """Search services prioritizing availability."""
        
        # Filter out closed services
        queryset = queryset.exclude(
            current_status__in=[ServiceStatus.CLOSED, ServiceStatus.TEMPORARILY_CLOSED]
        )
        
        # Optionally exclude full services
        if not include_full:
            queryset = queryset.exclude(current_status=ServiceStatus.FULL)
        
        # Create availability score
        queryset = queryset.annotate(
            availability_score=Case(
                When(current_status=ServiceStatus.OPEN, then=Value(4)),
                When(current_status=ServiceStatus.LIMITED, then=Value(3)),
                When(current_status=ServiceStatus.EMERGENCY_ONLY, then=Value(2)),
                When(current_status=ServiceStatus.FULL, then=Value(1)),
                default=Value(0),
                output_field=IntegerField(),
            ),
            # Capacity score (prefer services with more available space)
            capacity_score=Case(
                When(max_capacity__isnull=True, then=Value(2)),  # Unknown capacity gets middle score
                When(current_capacity__lt=F('max_capacity') * 0.5, then=Value(4)),  # < 50% full
                When(current_capacity__lt=F('max_capacity') * 0.8, then=Value(3)),  # < 80% full
                When(current_capacity__lt=F('max_capacity'), then=Value(2)),  # < 100% full
                default=Value(1),  # Full or over capacity
                output_field=IntegerField(),
            )
        ).order_by('-availability_score', '-capacity_score', '-quality_score')
        
        return queryset
    
    def get_name(self) -> str:
        return "availability"


class SmartSearchStrategy(SearchStrategy):
    """
    Intelligent search combining multiple factors for optimal results.
    
    Uses a weighted scoring system considering text relevance, distance,
    availability, quality, and user preferences.
    """
    
    def search(self, queryset: QuerySet,
              query: str = '',
              user_location: Optional[Point] = None,
              category_preference: Optional[str] = None,
              max_distance_km: Optional[float] = None,
              emergency_mode: bool = False,
              **kwargs) -> QuerySet:
        """Execute smart search with weighted scoring."""
        
        # Start with base queryset
        result_qs = queryset
        
        # Text search component
        if query:
            query_lower = query.lower().strip()
            result_qs = result_qs.filter(search_vector__icontains=query_lower)
        
        # Geographic filtering
        if user_location and max_distance_km:
            result_qs = result_qs.filter(
                location__distance_lte=(user_location, Distance(km=max_distance_km))
            )
        
        # Emergency mode override
        if emergency_mode:
            result_qs = result_qs.filter(is_emergency_service=True)
        
        # Category preference
        if category_preference:
            result_qs = result_qs.filter(category__category_type=category_preference)
        
        # Calculate composite score
        annotations = {}
        
        # Text relevance score (simplified - could use full-text search weights)
        if query:
            # This is a simplified relevance score
            # In production, you might use PostgreSQL's full-text search ranking
            annotations['text_score'] = Value(2, output_field=IntegerField())
        else:
            annotations['text_score'] = Value(1, output_field=IntegerField())
        
        # Distance score
        if user_location:
            annotations['distance'] = F('location').distance(user_location)
            # Convert distance to score (closer = higher score)
            annotations['distance_score'] = Case(
                When(distance__lte=Distance(km=1), then=Value(5)),
                When(distance__lte=Distance(km=3), then=Value(4)),
                When(distance__lte=Distance(km=5), then=Value(3)),
                When(distance__lte=Distance(km=10), then=Value(2)),
                default=Value(1),
                output_field=IntegerField(),
            )
        else:
            annotations['distance_score'] = Value(3, output_field=IntegerField())
        
        # Availability score
        annotations['availability_score'] = Case(
            When(current_status=ServiceStatus.OPEN, then=Value(5)),
            When(current_status=ServiceStatus.LIMITED, then=Value(4)),
            When(current_status=ServiceStatus.EMERGENCY_ONLY, then=Value(3)),
            When(current_status=ServiceStatus.FULL, then=Value(2)),
            default=Value(1),
            output_field=IntegerField(),
        )
        
        # Quality score (convert 0-5 rating to 1-5 integer)
        annotations['quality_score_int'] = Case(
            When(quality_score__gte=4.5, then=Value(5)),
            When(quality_score__gte=3.5, then=Value(4)),
            When(quality_score__gte=2.5, then=Value(3)),
            When(quality_score__gte=1.5, then=Value(2)),
            default=Value(1),
            output_field=IntegerField(),
        )
        
        # Emergency boost
        if emergency_mode:
            annotations['emergency_boost'] = Case(
                When(is_emergency_service=True, then=Value(3)),
                default=Value(0),
                output_field=IntegerField(),
            )
        else:
            annotations['emergency_boost'] = Value(0, output_field=IntegerField())
        
        # Apply annotations
        result_qs = result_qs.annotate(**annotations)
        
        # Calculate weighted composite score
        # Weights: text(20%), distance(25%), availability(25%), quality(20%), emergency(10%)
        result_qs = result_qs.annotate(
            composite_score=(
                F('text_score') * 0.2 +
                F('distance_score') * 0.25 +
                F('availability_score') * 0.25 +
                F('quality_score_int') * 0.2 +
                F('emergency_boost') * 0.1
            )
        )
        
        # Order by composite score
        return result_qs.order_by('-composite_score', 'name')
    
    def get_name(self) -> str:
        return "smart"


class SearchStrategyFactory:
    """
    Factory class for creating search strategy instances.
    
    Implements the Factory Method pattern to centralize strategy
    creation and management.
    """
    
    _strategies = {
        'basic': BasicTextSearchStrategy,
        'geographic': GeographicSearchStrategy,
        'category': CategorySearchStrategy,
        'emergency': EmergencySearchStrategy,
        'availability': AvailabilitySearchStrategy,
        'smart': SmartSearchStrategy,
    }
    
    @classmethod
    def create_strategy(cls, strategy_name: str) -> SearchStrategy:
        """
        Create a search strategy instance by name.
        
        Args:
            strategy_name: Name of the strategy to create
            
        Returns:
            SearchStrategy instance
            
        Raises:
            ValueError: If strategy name is not recognized
        """
        if strategy_name not in cls._strategies:
            available = ', '.join(cls._strategies.keys())
            raise ValueError(f"Unknown strategy '{strategy_name}'. Available: {available}")
        
        strategy_class = cls._strategies[strategy_name]
        return strategy_class()
    
    @classmethod
    def get_available_strategies(cls) -> List[str]:
        """Get list of available strategy names."""
        return list(cls._strategies.keys())
    
    @classmethod
    def register_strategy(cls, name: str, strategy_class: type) -> None:
        """
        Register a new search strategy.
        
        Args:
            name: Strategy name
            strategy_class: Strategy class (must inherit from SearchStrategy)
        """
        if not issubclass(strategy_class, SearchStrategy):
            raise ValueError("Strategy class must inherit from SearchStrategy")
        
        cls._strategies[name] = strategy_class


class SearchContext:
    """
    Context class for the Strategy pattern.
    
    Manages strategy selection and execution, providing a clean
    interface for service search operations.
    """
    
    def __init__(self, strategy_name: str = 'smart'):
        """
        Initialize search context with a strategy.
        
        Args:
            strategy_name: Name of the search strategy to use
        """
        self._strategy = SearchStrategyFactory.create_strategy(strategy_name)
        self._strategy_name = strategy_name
    
    def set_strategy(self, strategy_name: str) -> None:
        """Change the search strategy."""
        self._strategy = SearchStrategyFactory.create_strategy(strategy_name)
        self._strategy_name = strategy_name
    
    def search(self, queryset: QuerySet = None, **kwargs) -> QuerySet:
        """
        Execute search using the current strategy.
        
        Args:
            queryset: Base queryset (defaults to all public services)
            **kwargs: Strategy-specific parameters
            
        Returns:
            Filtered and ordered queryset
        """
        if queryset is None:
            from .models import Service
            queryset = Service.objects.public()
        
        return self._strategy.search(queryset, **kwargs)
    
    @property
    def strategy_name(self) -> str:
        """Get current strategy name."""
        return self._strategy_name
    
    @property
    def strategy_description(self) -> str:
        """Get current strategy description."""
        return self._strategy.get_description()


# Convenience function for one-off searches
def search_services(strategy: str = 'smart', **kwargs) -> QuerySet:
    """
    Convenience function for searching services.
    
    Args:
        strategy: Search strategy name
        **kwargs: Search parameters
        
    Returns:
        QuerySet of matching services
    """
    context = SearchContext(strategy)
    return context.search(**kwargs) 