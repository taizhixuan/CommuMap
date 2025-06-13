# CommuMap - Comprehensive Codebase Reference

## Overview

CommuMap is a community resource mapping platform that enables residents to discover, evaluate, and access essential community services through an interactive web interface. The platform serves as a centralized hub for healthcare, shelter, food, education, emergency, and other vital community services.

## Technology Stack

### Primary Language & Framework
- **Backend**: Django 5.0.0 (Python web framework)
- **Frontend**: Django Templates with JavaScript
- **Database**: SQLite (development), designed for PostgreSQL/PostGIS (production)

### Key Libraries & Services

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Web Framework** | Django 5.0.0 | Core web application framework |
| **API Framework** | Django REST Framework 3.14.0 | REST API endpoints |
| **Database** | SQLite/PostgreSQL | Data storage |
| **GIS Support** | PostGIS (commented out) | Geographic data handling |
| **Task Queue** | Celery 5.3.4 | Background task processing |
| **Cache/Message Broker** | Redis 5.0.1 | Caching and real-time features |
| **Authentication** | Django OTP 1.2.3 | Two-factor authentication |
| **Permissions** | Django Guardian 2.4.0 | Object-level permissions |
| **Forms** | Django Crispy Forms 2.1 | Enhanced form rendering |
| **Static Files** | WhiteNoise 6.6.0 | Static file serving |
| **WSGI Server** | Gunicorn 21.2.0 | Production deployment |
| **CORS** | Django CORS Headers 4.4.0 | Cross-origin requests |
| **Testing** | Pytest Django 4.7.0 | Testing framework |
| **Development** | Django Debug Toolbar 4.2.0 | Development debugging |

## Repository Structure

```
CommuMap/
├── apps/                          # Django applications
│   ├── core/                      # Core functionality, auth, landing
│   ├── services/                  # Service listings and discovery
│   ├── users/                     # User profiles and preferences
│   ├── managers/                  # Service manager interface
│   ├── moderators/                # Content moderation tools
│   ├── feedback/                  # Reviews and comments system
│   └── console/                   # Admin console
├── commumap/                      # Django project configuration
│   ├── settings/                  # Environment-based settings
│   ├── urls.py                    # Main URL routing
│   ├── wsgi.py                    # WSGI configuration
│   └── asgi.py                    # ASGI configuration (for real-time)
├── templates/                     # Django templates
├── static/                        # Static assets (CSS, JS, images)
├── staticfiles/                   # Collected static files
├── services/                      # Additional service modules
├── logs/                          # Application logs
├── requirements.txt               # Python dependencies
├── manage.py                      # Django management script
├── db.sqlite3                     # SQLite database
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Container definition
└── .env.example                   # Environment variables template
```

## Major Apps / Modules

| App | Purpose | Notable Classes / Functions |
|-----|---------|----------------------------|
| **core** | Landing page, authentication, system settings | `User`, `UserRole`, `SystemSettings`, `AuditLog`, `CustomLoginView` |
| **services** | Service listings, search, categories, real-time status | `Service`, `ServiceCategory`, `RealTimeStatusUpdate`, `ServiceAlert` |
| **users** | User profiles, bookmarks, notifications, preferences | `UserProfile`, `ServiceBookmark`, `UserNotification`, `UserActivity` |
| **managers** | Service manager dashboard and tools | Service management views, status update APIs |
| **moderators** | Content moderation and approval workflows | Approval/rejection APIs, bulk operations |
| **feedback** | Reviews, comments, ratings system | `Review`, `Comment`, rating APIs |
| **console** | Admin dashboard and system management | System monitoring, user management, maintenance tools |

## Core Data Models

### User Management (`apps/core/models.py`)

#### User Model
```python
class User(AbstractUser):
    # Core fields
    id = UUIDField(primary_key=True)
    email = EmailField(unique=True)  # Primary identifier
    role = CharField(choices=UserRole.choices)
    
    # Profile information
    full_name = CharField(max_length=150)
    phone = CharField(max_length=20)
    
    # Service Manager verification
    service_name = CharField(max_length=200)
    official_email = EmailField()
    contact_number = CharField(max_length=20)
    
    # Community Moderator verification
    community_experience = TextField()
    relevant_community = CharField(max_length=200)
    
    # Geographic preferences
    preferred_location_lat = FloatField()
    preferred_location_lng = FloatField()
    search_radius_km = PositiveIntegerField(default=10)
    
    # Verification status
    is_verified = BooleanField(default=False)
    verification_requested_at = DateTimeField()
    verified_by = ForeignKey('self')
```

#### User Roles
- **USER**: General public users (search, bookmark services)
- **SERVICE_MANAGER**: Manage specific service listings and real-time status
- **COMMUNITY_MODERATOR**: Verify services and moderate content
- **ADMIN**: System-wide administration and user management

#### System Settings (Singleton Pattern)
```python
class SystemSettings(models.Model):
    maintenance_mode = BooleanField(default=False)
    registration_enabled = BooleanField(default=True)
    emergency_mode = BooleanField(default=False)
    default_map_center_lat = FloatField(default=40.7128)
    default_map_center_lng = FloatField(default=-74.0060)
```

### Service Management (`apps/services/models.py`)

#### Service Model
```python
class Service(TimestampedMixin):
    id = UUIDField(primary_key=True)
    name = CharField(max_length=200)
    slug = SlugField(unique=True)
    description = TextField()
    
    # Categorization
    category = ForeignKey(ServiceCategory)
    tags = JSONField(default=list)
    
    # Geographic data
    latitude = FloatField()
    longitude = FloatField()
    address = CharField(max_length=300)
    city = CharField(max_length=100)
    
    # Contact information
    phone = CharField(max_length=20)
    email = EmailField()
    website = URLField()
    
    # Operating information
    hours_of_operation = JSONField(default=dict)
    is_24_7 = BooleanField(default=False)
    
    # Capacity and status
    max_capacity = PositiveIntegerField()
    current_capacity = PositiveIntegerField(default=0)
    current_status = CharField(choices=ServiceStatus.choices)
    
    # Service characteristics
    is_emergency_service = BooleanField(default=False)
    requires_appointment = BooleanField(default=False)
    is_free = BooleanField(default=True)
    
    # Administrative
    manager = ForeignKey(User, related_name='managed_services')
    is_verified = BooleanField(default=False)
    verified_by = ForeignKey(User, related_name='verified_services')
```

#### Service Categories
```python
class ServiceCategory(TimestampedMixin):
    CATEGORY_TYPES = [
        ('healthcare', 'Healthcare & Medical'),
        ('shelter', 'Shelter & Housing'),
        ('food', 'Food & Nutrition'),
        ('education', 'Education & Learning'),
        ('emergency', 'Emergency Services'),
        ('social', 'Social Services'),
        ('employment', 'Employment & Training'),
        ('legal', 'Legal Aid'),
        ('transportation', 'Transportation'),
        ('utilities', 'Utilities & Basic Needs'),
        ('recreation', 'Recreation & Community'),
        ('other', 'Other Services'),
    ]
```

#### Real-Time Status Updates (Observer Pattern)
```python
class RealTimeStatusUpdate(TimestampedMixin):
    service = ForeignKey(Service, related_name='status_updates')
    change_type = CharField(choices=CHANGE_TYPES)
    old_status = CharField(choices=ServiceStatus.choices)
    new_status = CharField(choices=ServiceStatus.choices)
    old_capacity = PositiveIntegerField()
    new_capacity = PositiveIntegerField()
    updated_by = ForeignKey(User)
```

### User Extensions (`apps/users/models.py`)

#### User Profile
```python
class UserProfile(TimestampedMixin):
    user = OneToOneField(User, related_name='profile')
    
    # Geographic preferences
    preferred_location_lat = FloatField()
    preferred_location_lng = FloatField()
    search_radius_km = PositiveIntegerField(default=10)
    
    # Accessibility preferences
    requires_wheelchair_access = BooleanField(default=False)
    requires_sign_language = BooleanField(default=False)
    preferred_languages = JSONField(default=list)
    
    # Communication preferences
    email_notifications = BooleanField(default=True)
    emergency_alerts = BooleanField(default=True)
```

#### Service Bookmarks
```python
class ServiceBookmark(TimestampedMixin):
    user = ForeignKey(User, related_name='bookmarks')
    service = ForeignKey('services.Service', related_name='bookmarked_by')
    folder_name = CharField(max_length=100, blank=True)
    notes = TextField(blank=True)
    last_accessed = DateTimeField(default=timezone.now)
    access_count = PositiveIntegerField(default=1)
```

## API & Real-Time Interfaces

### REST Endpoints

#### Service Discovery API (`apps/services/views.py`)
- `ServiceSearchAPIView` - Service search with filters (uses Strategy pattern)
- `ServiceCategoryAPIView` - Category-based filtering
- `MapDataAPIView` - Geospatial service data for map (uses Adapter pattern)
- `BookmarkToggleAPIView` - Add/remove bookmarks

#### Service Management API (`apps/managers/views.py`)
- `UpdateServiceStatusAPIView` - Real-time status updates
- `UpdateCapacityAPIView` - Capacity management
- `MarkNotificationReadAPIView` - Notification management

#### Moderation API (`apps/moderators/views.py`)
- `ApproveServiceAPIView` / `RejectServiceAPIView` - Service approval
- `BulkApproveServicesAPIView` / `BulkRejectServicesAPIView` - Bulk operations
- `ApproveCommentAPIView` / `RejectCommentAPIView` - Comment moderation
- `ResolveFlagAPIView` - Flag resolution

#### Feedback API (`apps/feedback/views.py`)
- `CreateReviewAPIView` - Submit service reviews
- `CreateCommentAPIView` - Add comments
- `ReviewHelpfulAPIView` / `ReviewUnhelpfulAPIView` - Review voting
- `CommentLikeAPIView` - Comment interactions

### URL Structure

```
/                           # Landing page
/accounts/                  # Authentication (allauth - commented out)
/u/                        # User-specific URLs
/manager/                  # Service Manager interface
/moderator/                # Community Moderator interface
/admin/                    # Admin Console
/services/                 # Service discovery and details
/feedback/                 # Feedback system
/api/                      # API endpoints (planned)
```

## Authentication & Authorization

### Authentication System
- Custom User model with email as primary identifier
- Role-based access control (RBAC)
- Two-factor authentication support (Django OTP)
- Object-level permissions (Django Guardian)

### Role-Based Middleware
```python
class RoleBasedAccessMiddleware:
    """Custom middleware for role-based access control"""
```

### Verification Workflow
1. **Service Managers**: Submit official details → Admin verification → Full access
2. **Community Moderators**: Application with experience → Admin review → Moderation tools
3. **Regular Users**: Immediate access after registration

## Real-Time Features

### Status Update System
- Service managers can push real-time capacity updates
- Automatic notifications to subscribed users
- Observer pattern implementation for status changes

### Emergency Mode
- "Help Me Now" button filters emergency-eligible services
- Priority display for urgent services
- System-wide emergency mode toggle

### Notification System
```python
class UserNotification(TimestampedMixin):
    NOTIFICATION_TYPES = [
        ('service_update', 'Service Update'),
        ('emergency_alert', 'Emergency Alert'),
        ('bookmark_update', 'Bookmark Update'),
        ('system_announcement', 'System Announcement'),
    ]
```

## Geographic Features

### Current Implementation
- Latitude/longitude coordinate storage
- Distance-based search functionality (via Strategy pattern)
- Multi-provider map integration (via Adapter pattern)
- Geocoding support (forward and reverse)

### Map Provider Support (Adapter Pattern)
- **Leaflet + OpenStreetMap**: Free, open-source mapping
- **Google Maps**: High-quality maps with API key
- **Mapbox**: Enhanced mapping capabilities
- **Configurable**: Switch providers via settings

### Planned GIS Integration
- PostGIS support (currently commented out)
- Advanced spatial queries
- Geographic indexing for performance

## Security Features

### Authentication & Authorization
- Secure password validation
- Role-based access control
- Object-level permissions
- CSRF protection
- XFrame protection

### Data Protection
- User consent management
- Privacy controls
- Audit logging for administrative actions

### System Security
```python
class AuditLog(TimestampedMixin):
    ACTION_CHOICES = [
        ('user_created', 'User Created'),
        ('service_approved', 'Service Approved'),
        ('emergency_toggled', 'Emergency Status Toggled'),
        # ... more actions
    ]
```

## Development & Deployment

### Environment Configuration
- Development settings (`commumap/settings/development.py`)
- Production settings (`commumap/settings/production.py`)
- Environment variables via django-environ

### Docker Support
- `Dockerfile` for containerization
- `docker-compose.yml` for orchestration
- Production-ready with Gunicorn

### Testing Framework
- Pytest Django for unit tests
- Factory Boy for test data generation
- Model Bakery for object creation

## Key Design Patterns

### Singleton Pattern (`apps/core/models.py`, `apps/console/managers.py`)
- **Purpose**: One-per-system instances for global configuration and system managers
- **Key Participants**:
  - `SystemSettings` - Global system configuration with thread-safe singleton
  - `NotificationDispatcher` - System-wide messaging manager
  - `SettingsLoader` - Runtime configuration manager
- **Implementation Features**:
  - Thread-safe singleton creation with `threading.Lock()`
  - Lazy initialization on first access
  - Global accessor methods (`SystemSettings.get_instance()`)
- **Usage**: 
  ```python
  settings = SystemSettings.get_instance()
  dispatcher = NotificationDispatcher()  # Auto-singleton
  ```

### Observer Pattern (`apps/services/signals.py`)
- **Purpose**: Push real-time alerts and notifications when service status changes
- **Key Participants**:
  - `NotificationDispatcher` (Subject) - Manages observer subscriptions
  - Django Signals - Built-in observer mechanism for model changes
  - `RealTimeStatusUpdate` - Observable status change events
  - Observer classes: `WebsocketObserver`, `EmailObserver`, `AlertService`
- **Custom Signals**:
  - `service_capacity_changed` - Capacity threshold alerts
  - `service_status_changed` - Status change notifications  
  - `emergency_alert_created` - Emergency broadcast system
- **Signal Handlers**:
  - `@receiver(post_save, sender=Service)` - Service creation/update notifications
  - `@receiver(pre_save, sender=Service)` - State change tracking
  - Automatic notification dispatch to subscribed observers
- **Usage**: `notification_dispatcher.subscribe(observer)`

### Strategy Pattern (`apps/services/strategies.py`)
- **Purpose**: Pluggable search algorithms without altering controllers
- **Key Participants**:
  - `SearchStrategy` (Abstract base class)
  - `SearchContext` (Context class)
  - `SearchStrategyFactory` (Factory for strategy creation)
- **Concrete Strategies**:
  - `BasicTextSearchStrategy` - Text matching across name, description, tags
  - `GeographicSearchStrategy` - Distance-based search from user location
  - `CategorySearchStrategy` - Category and subcategory filtering
  - `EmergencySearchStrategy` - Emergency-focused search with priority ordering
  - `AvailabilitySearchStrategy` - Prioritizes open services with capacity
  - `SmartSearchStrategy` - AI-enhanced search combining multiple factors
- **Usage**: `SearchContext('geographic').search(queryset, user_location=point)`

### Adapter Pattern (`apps/services/adapters.py`)
- **Purpose**: Swap map providers and external data feeds via unified interface
- **Key Participants**:
  - `MapProvider` (Abstract base adapter)
  - `MapAdapterFactory` (Factory for adapter creation)
  - `ExternalDataAdapter` (For data source integration)
- **Map Provider Adapters**:
  - `LeafletOpenStreetMapAdapter` - Free OpenStreetMap integration
  - `GoogleMapsAdapter` - Google Maps with API key support
  - `MapboxAdapter` - Mapbox integration for enhanced mapping
- **External Data Adapters**:
  - `Government311Adapter` - Government service data import
- **Usage**: `MapAdapterFactory.create_adapter('leaflet')`

### Factory Method Pattern (`apps/services/factories.py`, `apps/managers/factories.py`)
- **Purpose**: Centralized creation of polymorphic domain objects with validation and defaults
- **Key Participants**:
  - `ServiceFactory` (Abstract base) - Common service creation interface
  - `ServiceFactoryRegistry` - Factory selection and management
  - `AlertFactory` - Service alert creation with type-specific defaults
  - `StatusUpdateFactory` - Real-time status update creation
- **Concrete Service Factories**:
  - `HealthcareServiceFactory` - Medical services with appointment requirements
  - `ShelterServiceFactory` - Housing services with capacity management
  - `FoodServiceFactory` - Food bank/pantry services
  - `EmergencyServiceFactory` - Emergency response services
  - `GeneralServiceFactory` - Fallback for other service types
- **Features**:
  - Type-specific validation and default values
  - Category-based factory selection
  - Location validation and geographic defaults
  - Tag management and service-specific metadata
- **Usage**: 
  ```python
  service = ServiceFactoryRegistry.create_service('healthcare', 
                                                  category=category, 
                                                  name="City Hospital")
  alert = AlertFactory.create_emergency_alert(service, "Fire evacuation")
  ```

### Repository Pattern (`apps/services/models.py`)
- **Purpose**: Custom QuerySet managers for complex queries and service discovery abstractions
- **Key Participants**:
  - `ServiceQuerySet` - Custom queryset with domain-specific filters
  - `Service.objects` - Custom manager using ServiceQuerySet
- **Query Methods**:
  - `active()` - Filter to active services only
  - `verified()` - Filter to verified services only  
  - `public()` - Services visible to public (active + verified)
  - `emergency_eligible()` - Emergency services filter
  - `open_now()` - Currently open services
  - `near_point(point, distance_km)` - Geographic proximity search
  - `by_category(category_slug)` - Category-based filtering
  - `search(query)` - Text search across service fields
- **Usage**: 
  ```python
  Service.objects.public().emergency_eligible().open_now()
  Service.objects.near_point((lat, lng), 5).by_category('healthcare')
  ```

## Database Schema Highlights

### Indexes for Performance
```python
class Meta:
    indexes = [
        models.Index(fields=['role', 'is_verified']),
        models.Index(fields=['latitude', 'longitude']),
        models.Index(fields=['category', 'is_active']),
        models.Index(fields=['current_status', 'is_emergency_service']),
    ]
```

### JSON Fields for Flexibility
- Service `tags` and `hours_of_operation`
- User `preferred_languages` and preferences
- Audit log `metadata` for contextual information

## Business Logic Highlights

### Service Verification Workflow
1. Service Manager creates/updates listing
2. Requires moderator/admin approval for public visibility
3. Real-time status updates bypass approval (for verified managers)

### Capacity Management
- Real-time capacity tracking
- Visual indicators (red markers for ≥90% capacity)
- Automatic status updates based on capacity thresholds

### Emergency Service Discovery
- "Help Me Now" button for emergency situations
- 5km default radius for emergency searches
- Priority display for verified emergency services

### Content Moderation
- User feedback requires moderation
- Bulk approval/rejection workflows
- Transparent moderation queue system

This comprehensive reference covers the complete CommuMap codebase architecture, from the Django foundation through the specialized apps handling service discovery, user management, and real-time updates. The platform is designed for scalability and maintainability while serving the critical need for accessible community resource information.
