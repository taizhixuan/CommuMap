"""
Adapter pattern implementations for CommuMap external integrations.

This module implements the Adapter pattern to provide unified interfaces
for different map providers and external data sources.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
import json
import requests
from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class MapProvider(ABC):
    """
    Abstract base class for map provider adapters.
    
    Implements the Adapter pattern to provide a unified interface
    for different mapping services (Leaflet, Google Maps, etc.).
    """
    
    @abstractmethod
    def get_map_config(self) -> Dict[str, Any]:
        """Get map configuration for frontend initialization."""
        pass
    
    @abstractmethod
    def get_tile_url(self) -> str:
        """Get tile URL template for map rendering."""
        pass
    
    @abstractmethod
    def get_attribution(self) -> str:
        """Get attribution text for the map provider."""
        pass
    
    @abstractmethod
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Convert coordinates to address information."""
        pass
    
    @abstractmethod
    def forward_geocode(self, address: str) -> Optional[Point]:
        """Convert address to coordinates."""
        pass
    
    def get_provider_name(self) -> str:
        """Get the provider name."""
        return self.__class__.__name__.replace('Adapter', '').lower()


class LeafletOpenStreetMapAdapter(MapProvider):
    """
    Adapter for Leaflet with OpenStreetMap tiles.
    
    Provides free, open-source mapping without API keys.
    Suitable for development and basic production use.
    """
    
    def get_map_config(self) -> Dict[str, Any]:
        """Get Leaflet map configuration."""
        return {
            'provider': 'leaflet',
            'tile_url': self.get_tile_url(),
            'attribution': self.get_attribution(),
            'max_zoom': 19,
            'min_zoom': 1,
            'default_zoom': getattr(settings, 'DEFAULT_MAP_ZOOM', 12),
            'center': {
                'lat': getattr(settings, 'DEFAULT_MAP_CENTER_LAT', 40.7128),
                'lng': getattr(settings, 'DEFAULT_MAP_CENTER_LNG', -74.0060),
            },
            'options': {
                'scrollWheelZoom': True,
                'touchZoom': True,
                'doubleClickZoom': True,
                'boxZoom': True,
                'keyboard': True,
                'dragging': True,
            }
        }
    
    def get_tile_url(self) -> str:
        """Get OpenStreetMap tile URL template."""
        return 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
    
    def get_attribution(self) -> str:
        """Get OpenStreetMap attribution."""
        return '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Use Nominatim for reverse geocoding."""
        cache_key = f"reverse_geocode_{lat}_{lng}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'limit': 1,
            }
            headers = {'User-Agent': 'CommuMap/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data and 'address' in data:
                address_info = {
                    'formatted_address': data.get('display_name', ''),
                    'street_number': data['address'].get('house_number', ''),
                    'street_name': data['address'].get('road', ''),
                    'city': data['address'].get('city') or data['address'].get('town') or data['address'].get('village', ''),
                    'state': data['address'].get('state', ''),
                    'postal_code': data['address'].get('postcode', ''),
                    'country': data['address'].get('country', ''),
                }
                
                # Cache for 1 hour
                cache.set(cache_key, address_info, 3600)
                return address_info
                
        except Exception as e:
            logger.warning(f"Reverse geocoding failed for {lat}, {lng}: {e}")
        
        return None
    
    def forward_geocode(self, address: str) -> Optional[Point]:
        """Use Nominatim for forward geocoding."""
        cache_key = f"forward_geocode_{hash(address)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Point(cached_result['lng'], cached_result['lat'])
        
        try:
            url = "https://nominatim.openstreetmap.org/search"
            params = {
                'q': address,
                'format': 'json',
                'limit': 1,
                'addressdetails': 1,
            }
            headers = {'User-Agent': 'CommuMap/1.0'}
            
            response = requests.get(url, params=params, headers=headers, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                result = data[0]
                lat = float(result['lat'])
                lng = float(result['lon'])
                
                # Cache for 24 hours
                cache.set(cache_key, {'lat': lat, 'lng': lng}, 86400)
                return Point(lng, lat)
                
        except Exception as e:
            logger.warning(f"Forward geocoding failed for '{address}': {e}")
        
        return None


class GoogleMapsAdapter(MapProvider):
    """
    Adapter for Google Maps integration.
    
    Provides high-quality maps and geocoding with Google's API.
    Requires API key and may have usage costs.
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'GOOGLE_MAPS_API_KEY', '')
        if not self.api_key:
            logger.warning("Google Maps API key not configured")
    
    def get_map_config(self) -> Dict[str, Any]:
        """Get Google Maps configuration."""
        return {
            'provider': 'google',
            'api_key': self.api_key,
            'max_zoom': 21,
            'min_zoom': 1,
            'default_zoom': getattr(settings, 'DEFAULT_MAP_ZOOM', 12),
            'center': {
                'lat': getattr(settings, 'DEFAULT_MAP_CENTER_LAT', 40.7128),
                'lng': getattr(settings, 'DEFAULT_MAP_CENTER_LNG', -74.0060),
            },
            'options': {
                'mapTypeId': 'roadmap',
                'disableDefaultUI': False,
                'zoomControl': True,
                'mapTypeControl': True,
                'streetViewControl': True,
                'fullscreenControl': True,
            }
        }
    
    def get_tile_url(self) -> str:
        """Google Maps doesn't use tile URLs in the same way."""
        return ''
    
    def get_attribution(self) -> str:
        """Get Google Maps attribution."""
        return '&copy; Google Maps'
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Use Google Geocoding API for reverse geocoding."""
        if not self.api_key:
            return None
        
        cache_key = f"google_reverse_{lat}_{lng}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'latlng': f"{lat},{lng}",
                'key': self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                result = data['results'][0]
                address_components = result.get('address_components', [])
                
                # Parse address components
                address_info = {
                    'formatted_address': result.get('formatted_address', ''),
                    'street_number': '',
                    'street_name': '',
                    'city': '',
                    'state': '',
                    'postal_code': '',
                    'country': '',
                }
                
                for component in address_components:
                    types = component.get('types', [])
                    value = component.get('long_name', '')
                    
                    if 'street_number' in types:
                        address_info['street_number'] = value
                    elif 'route' in types:
                        address_info['street_name'] = value
                    elif 'locality' in types:
                        address_info['city'] = value
                    elif 'administrative_area_level_1' in types:
                        address_info['state'] = value
                    elif 'postal_code' in types:
                        address_info['postal_code'] = value
                    elif 'country' in types:
                        address_info['country'] = value
                
                # Cache for 1 hour
                cache.set(cache_key, address_info, 3600)
                return address_info
                
        except Exception as e:
            logger.warning(f"Google reverse geocoding failed for {lat}, {lng}: {e}")
        
        return None
    
    def forward_geocode(self, address: str) -> Optional[Point]:
        """Use Google Geocoding API for forward geocoding."""
        if not self.api_key:
            return None
        
        cache_key = f"google_forward_{hash(address)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Point(cached_result['lng'], cached_result['lat'])
        
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': self.api_key,
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data['status'] == 'OK' and data['results']:
                location = data['results'][0]['geometry']['location']
                lat = location['lat']
                lng = location['lng']
                
                # Cache for 24 hours
                cache.set(cache_key, {'lat': lat, 'lng': lng}, 86400)
                return Point(lng, lat)
                
        except Exception as e:
            logger.warning(f"Google forward geocoding failed for '{address}': {e}")
        
        return None


class MapboxAdapter(MapProvider):
    """
    Adapter for Mapbox integration.
    
    Provides customizable maps with Mapbox's API.
    Requires access token and may have usage costs.
    """
    
    def __init__(self):
        self.access_token = getattr(settings, 'MAPBOX_ACCESS_TOKEN', '')
        if not self.access_token:
            logger.warning("Mapbox access token not configured")
    
    def get_map_config(self) -> Dict[str, Any]:
        """Get Mapbox configuration."""
        return {
            'provider': 'mapbox',
            'access_token': self.access_token,
            'style': 'mapbox://styles/mapbox/streets-v11',
            'max_zoom': 22,
            'min_zoom': 0,
            'default_zoom': getattr(settings, 'DEFAULT_MAP_ZOOM', 12),
            'center': {
                'lat': getattr(settings, 'DEFAULT_MAP_CENTER_LAT', 40.7128),
                'lng': getattr(settings, 'DEFAULT_MAP_CENTER_LNG', -74.0060),
            },
            'options': {
                'interactive': True,
                'scrollZoom': True,
                'boxZoom': True,
                'dragRotate': True,
                'dragPan': True,
                'keyboard': True,
                'doubleClickZoom': True,
                'touchZoomRotate': True,
            }
        }
    
    def get_tile_url(self) -> str:
        """Get Mapbox tile URL template."""
        return f'https://api.mapbox.com/styles/v1/mapbox/streets-v11/tiles/{{z}}/{{x}}/{{y}}?access_token={self.access_token}'
    
    def get_attribution(self) -> str:
        """Get Mapbox attribution."""
        return '&copy; <a href="https://www.mapbox.com/">Mapbox</a> &copy; <a href="https://www.openstreetmap.org/">OpenStreetMap</a>'
    
    def reverse_geocode(self, lat: float, lng: float) -> Optional[Dict[str, str]]:
        """Use Mapbox Geocoding API for reverse geocoding."""
        if not self.access_token:
            return None
        
        cache_key = f"mapbox_reverse_{lat}_{lng}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return cached_result
        
        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{lng},{lat}.json"
            params = {
                'access_token': self.access_token,
                'types': 'address',
                'limit': 1,
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data['features']:
                feature = data['features'][0]
                properties = feature.get('properties', {})
                context = feature.get('context', [])
                
                address_info = {
                    'formatted_address': feature.get('place_name', ''),
                    'street_number': properties.get('address', ''),
                    'street_name': feature.get('text', ''),
                    'city': '',
                    'state': '',
                    'postal_code': '',
                    'country': '',
                }
                
                # Parse context for additional details
                for ctx in context:
                    ctx_id = ctx.get('id', '')
                    if ctx_id.startswith('place'):
                        address_info['city'] = ctx.get('text', '')
                    elif ctx_id.startswith('region'):
                        address_info['state'] = ctx.get('text', '')
                    elif ctx_id.startswith('postcode'):
                        address_info['postal_code'] = ctx.get('text', '')
                    elif ctx_id.startswith('country'):
                        address_info['country'] = ctx.get('text', '')
                
                # Cache for 1 hour
                cache.set(cache_key, address_info, 3600)
                return address_info
                
        except Exception as e:
            logger.warning(f"Mapbox reverse geocoding failed for {lat}, {lng}: {e}")
        
        return None
    
    def forward_geocode(self, address: str) -> Optional[Point]:
        """Use Mapbox Geocoding API for forward geocoding."""
        if not self.access_token:
            return None
        
        cache_key = f"mapbox_forward_{hash(address)}"
        cached_result = cache.get(cache_key)
        if cached_result:
            return Point(cached_result['lng'], cached_result['lat'])
        
        try:
            url = f"https://api.mapbox.com/geocoding/v5/mapbox.places/{address}.json"
            params = {
                'access_token': self.access_token,
                'limit': 1,
                'types': 'address,poi',
            }
            
            response = requests.get(url, params=params, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            if data['features']:
                coordinates = data['features'][0]['geometry']['coordinates']
                lng, lat = coordinates
                
                # Cache for 24 hours
                cache.set(cache_key, {'lat': lat, 'lng': lng}, 86400)
                return Point(lng, lat)
                
        except Exception as e:
            logger.warning(f"Mapbox forward geocoding failed for '{address}': {e}")
        
        return None


class MapAdapterFactory:
    """
    Factory for creating map provider adapters.
    
    Implements the Factory Method pattern for map provider selection
    based on configuration or user preference.
    """
    
    _adapters = {
        'leaflet': LeafletOpenStreetMapAdapter,
        'google': GoogleMapsAdapter,
        'mapbox': MapboxAdapter,
    }
    
    @classmethod
    def create_adapter(cls, provider: str = None) -> MapProvider:
        """
        Create a map provider adapter.
        
        Args:
            provider: Map provider name (leaflet, google, mapbox)
                     If None, uses default from settings
        
        Returns:
            MapProvider instance
        
        Raises:
            ValueError: If provider is not supported
        """
        if provider is None:
            provider = getattr(settings, 'DEFAULT_MAP_PROVIDER', 'leaflet')
        
        provider = provider.lower()
        if provider not in cls._adapters:
            available = ', '.join(cls._adapters.keys())
            raise ValueError(f"Unsupported map provider '{provider}'. Available: {available}")
        
        adapter_class = cls._adapters[provider]
        return adapter_class()
    
    @classmethod
    def get_available_providers(cls) -> List[str]:
        """Get list of available map providers."""
        return list(cls._adapters.keys())
    
    @classmethod
    def register_adapter(cls, name: str, adapter_class: type) -> None:
        """Register a new map adapter."""
        if not issubclass(adapter_class, MapProvider):
            raise ValueError("Adapter class must inherit from MapProvider")
        
        cls._adapters[name] = adapter_class


class ExternalDataAdapter(ABC):
    """
    Abstract adapter for external data feeds.
    
    Provides a unified interface for importing service data
    from external sources like government APIs or partner systems.
    """
    
    @abstractmethod
    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from external source."""
        pass
    
    @abstractmethod
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform external data to CommuMap format."""
        pass
    
    @abstractmethod
    def get_source_name(self) -> str:
        """Get the name of the data source."""
        pass
    
    def import_services(self) -> Tuple[int, int, List[str]]:
        """
        Import services from external source.
        
        Returns:
            Tuple of (created_count, updated_count, errors)
        """
        try:
            raw_data = self.fetch_data()
            transformed_data = self.transform_data(raw_data)
            
            created_count = 0
            updated_count = 0
            errors = []
            
            from .models import Service, ServiceCategory
            from .factories import ServiceFactoryRegistry
            
            for service_data in transformed_data:
                try:
                    # Check if service already exists
                    existing_service = None
                    if 'external_id' in service_data:
                        # Try to find by external ID (would need to add this field to Service model)
                        pass
                    else:
                        # Try to find by name and location
                        existing_service = Service.objects.filter(
                            name=service_data['name'],
                            location__distance_lte=(service_data['location'], 100)  # 100 meters
                        ).first()
                    
                    if existing_service:
                        # Update existing service
                        for key, value in service_data.items():
                            if hasattr(existing_service, key):
                                setattr(existing_service, key, value)
                        existing_service.save()
                        updated_count += 1
                    else:
                        # Create new service
                        ServiceFactoryRegistry.create_service(**service_data)
                        created_count += 1
                        
                except Exception as e:
                    error_msg = f"Error processing service '{service_data.get('name', 'Unknown')}': {e}"
                    errors.append(error_msg)
                    logger.error(error_msg)
            
            return created_count, updated_count, errors
            
        except Exception as e:
            error_msg = f"Failed to import from {self.get_source_name()}: {e}"
            logger.error(error_msg)
            return 0, 0, [error_msg]


class Government311Adapter(ExternalDataAdapter):
    """
    Adapter for importing data from government 311 APIs.
    
    Many cities provide 311 service data through standardized APIs.
    This adapter can be customized for specific city implementations.
    """
    
    def __init__(self, api_url: str, api_key: str = None):
        self.api_url = api_url
        self.api_key = api_key
    
    def fetch_data(self) -> List[Dict[str, Any]]:
        """Fetch data from 311 API."""
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            response = requests.get(self.api_url, headers=headers, timeout=30)
            response.raise_for_status()
            
            return response.json()
            
        except Exception as e:
            logger.error(f"Failed to fetch 311 data: {e}")
            return []
    
    def transform_data(self, raw_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Transform 311 data to CommuMap format."""
        transformed = []
        
        for item in raw_data:
            try:
                # This is a simplified transformation - would need to be
                # customized based on the specific 311 API format
                service_data = {
                    'name': item.get('agency_name', 'Unknown Service'),
                    'description': item.get('description', ''),
                    'short_description': item.get('service_name', '')[:300],
                    'address': item.get('address', ''),
                    'city': item.get('city', ''),
                    'state_province': item.get('state', ''),
                    'phone': item.get('phone', ''),
                    'website': item.get('url', ''),
                    'is_verified': True,  # Government data is pre-verified
                }
                
                # Convert coordinates if available
                if item.get('latitude') and item.get('longitude'):
                    service_data['location'] = Point(
                        float(item['longitude']),
                        float(item['latitude'])
                    )
                
                # Map service type to category
                service_type = item.get('service_type', 'other')
                category_mapping = {
                    'health': 'healthcare',
                    'housing': 'shelter',
                    'food': 'food',
                    'emergency': 'emergency',
                    'social': 'social',
                }
                category_type = category_mapping.get(service_type.lower(), 'other')
                
                # Get or create category
                from .models import ServiceCategory
                category, created = ServiceCategory.objects.get_or_create(
                    category_type=category_type,
                    defaults={'name': service_type.title()}
                )
                service_data['category'] = category
                
                transformed.append(service_data)
                
            except Exception as e:
                logger.warning(f"Failed to transform 311 item: {e}")
                continue
        
        return transformed
    
    def get_source_name(self) -> str:
        return "Government 311 API"


# Convenience function for getting the default map adapter
def get_default_map_adapter() -> MapProvider:
    """Get the default map adapter based on settings."""
    return MapAdapterFactory.create_adapter() 