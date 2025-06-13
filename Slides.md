## System Objectives & Deliverables

• Centralized web platform for community service discovery via interactive maps
• Real-time service updates by authorized managers ensuring reliable information
• User-provider collaboration through feedback enhancing transparency and trust
• Contributing to SDG 10 and 11 by reducing service access disparities

 CommuMap addresses fragmented community service information by creating a unified platform where residents can locate essential services like clinics, shelters, and food banks. The system enables real-time updates from service managers and incorporates user feedback to maintain data accuracy and build community trust.

## System Scope

• Interactive map with real-time rendering of essential community services
• Advanced search filters by category distance and availability status
• Live status feeds with capacity indicators and closure alerts
• Emergency "Help Me Now" button for verified nearby resources
• Role-based dashboards for managers moderators and administrators
• Responsive UI optimized for desktop tablet and mobile devices

 The system focuses on core functionalities including an interactive map interface, advanced filtering capabilities, and real-time status updates. It supports multiple user roles with specialized dashboards while maintaining a responsive design to serve users across all device types.

## System Overview

• Django-based web application with REST API architecture
• Role-based access control supporting four user types
• Real-time capacity monitoring with visual indicators
• Integrated feedback and moderation workflow system
• Mobile-first responsive design for accessibility
• PostgreSQL database with geospatial PostGIS extensions

 CommuMap is built as a modern Django web application featuring role-based access control for different user types. The system provides real-time monitoring capabilities and includes comprehensive feedback mechanisms, all delivered through a mobile-responsive interface with geospatial database support.

## Component-Level Diagram

• Core module handles authentication landing pages and RBAC middleware
• Services module manages service discovery mapping and capacity tracking
• Feedback module processes user comments ratings and moderation workflows
• Users module provides profile management and role assignments
• Managers module enables service provider dashboard and real-time updates
• Moderators module facilitates content verification and community moderation
• Console module delivers admin interface for system-wide management

The system architecture consists of seven main Django applications, each handling specific domain responsibilities. Components communicate through REST APIs and shared database models, with the core module providing authentication and access control services that other modules depend on.

**Complete Component-Level Diagram Details:**

**Primary Components:**
1. **Core Component**
   - Provides: Authentication API, RBAC Middleware, Landing Pages, User Session Management
   - Requires: Database Connection, User Model Access
   - Dependencies: None (foundational component)

2. **Services Component** 
   - Provides: Service Discovery API, Mapping Interface, Capacity Tracking API, Search/Filter API
   - Requires: Authentication from Core, Database Connection, Geospatial Database Access
   - Dependencies: Core (for authentication)

3. **Feedback Component**
   - Provides: Comments API, Ratings API, Moderation Queue Interface
   - Requires: Authentication from Core, User Profile Access, Database Connection
   - Dependencies: Core, Users

4. **Users Component**
   - Provides: Profile Management API, Role Assignment Interface, User Dashboard
   - Requires: Authentication from Core, Database Connection
   - Dependencies: Core

5. **Managers Component**
   - Provides: Service Management Dashboard, Real-time Update API, Capacity Update Interface
   - Requires: Authentication from Core, Service Data Access, Manager Role Verification
   - Dependencies: Core, Services

6. **Moderators Component**
   - Provides: Content Moderation Interface, Approval Workflow API, Community Management Dashboard
   - Requires: Authentication from Core, Moderator Role Verification, Feedback Access
   - Dependencies: Core, Feedback

7. **Console Component**
   - Provides: Admin Dashboard, System Management Interface, User Role Management API
   - Requires: Authentication from Core, Admin Role Verification, Full System Access
   - Dependencies: Core, All other components

**External Components:**
1. **PostgreSQL Database**
   - Provides: Data Persistence, PostGIS Geospatial Extensions, ACID Transactions
   - Interface: Django ORM Connection

2. **Redis Cache**
   - Provides: Session Storage, Caching Layer, Real-time Data Storage
   - Interface: Redis Protocol Connection

3. **Celery Task Queue**
   - Provides: Background Task Processing, Scheduled Jobs, Notification Processing
   - Interface: Message Queue Protocol

4. **Web Browser Client**
   - Provides: User Interface Rendering, User Input Collection
   - Requires: HTTP/REST API Access, Static File Serving

5. **Mobile Client (Future)**
   - Provides: Mobile User Interface, Location Services
   - Requires: REST API Access, Real-time Updates

**Component Interfaces:**
- **HTTP REST API**: All components expose REST endpoints for external access
- **Django ORM**: All components share database models and relationships
- **Middleware Pipeline**: Core component provides authentication/authorization middleware
- **Template System**: Components provide HTML templates for web interface
- **WebSocket (Planned)**: Real-time updates for capacity monitoring
- **Message Queue**: Background task processing for notifications and updates

**Data Flow:**
1. User requests → Core (authentication) → Target Component → Database
2. Manager updates → Managers Component → Services Component → Real-time notifications
3. User feedback → Feedback Component → Moderation Queue → Moderators Component
4. System administration → Console Component → All other components

## Software Architecture

• Presentation layer using Django templates with responsive Bootstrap styling
• API layer built with Django REST Framework for mobile integration
• Domain layer containing business logic across specialized Django applications
• Infrastructure layer supporting PostgreSQL Redis and Celery background processing
• Middleware layer implementing custom RBAC and security controls
• Deployment layer using Docker containers with Nginx load balancing

The architecture follows a layered approach with clear separation of concerns. The presentation layer provides web interfaces while the API layer enables future mobile app integration. Business logic is encapsulated in domain-specific Django apps, supported by robust infrastructure including database clustering and background task processing.

**Complete Software Architecture Diagram Details:**

**Layered Architecture:**

**1. Presentation Layer (Client Tier)**
- **Web Browser Client**
  - Technology: HTML5, CSS3, Bootstrap 4, JavaScript
  - Responsibilities: UI rendering, user input validation, responsive design
  - Communication: HTTP/HTTPS requests to API layer
  
- **Mobile Client (Future)**
  - Technology: React Native / Flutter (planned)
  - Responsibilities: Mobile UI, location services, offline capabilities
  - Communication: REST API calls, WebSocket connections

**2. Web/API Layer (Presentation Tier)**
- **Django Web Framework**
  - Technology: Django 5.0, Django Templates, Whitenoise
  - Responsibilities: HTTP request handling, template rendering, static file serving
  - Components: URL routing, view controllers, form handling
  
- **REST API Layer**
  - Technology: Django REST Framework 3.14
  - Responsibilities: API endpoint management, serialization, authentication
  - Features: Token authentication, pagination, CORS support

**3. Middleware Layer (Cross-Cutting Concerns)**
- **Security Middleware**
  - Components: CSRF protection, XFrame options, CORS headers
  - Custom: RoleBasedAccessMiddleware for RBAC
  
- **Authentication Middleware**
  - Technology: Django OTP, Django Guardian
  - Features: Multi-factor authentication, object-level permissions

**4. Business/Domain Layer (Application Tier)**
- **Core Business Logic**
  - Apps: core, services, feedback, users, managers, moderators, console
  - Patterns: Model-View-Controller, Repository pattern
  - Features: Service discovery, capacity tracking, moderation workflows

- **Background Processing**
  - Technology: Celery 5.3.4 with Redis broker
  - Responsibilities: Async tasks, scheduled jobs, notification processing
  - Tasks: Email notifications, data synchronization, cleanup jobs

**5. Data Access Layer (Data Tier)**
- **Django ORM**
  - Technology: Django Models with PostgreSQL backend
  - Features: Migrations, relationships, query optimization
  - Extensions: PostGIS for geospatial data

- **Caching Layer**
  - Technology: Redis 7 with django-redis
  - Responsibilities: Session storage, query caching, real-time data

**6. Infrastructure Layer (Data Storage)**
- **Primary Database**
  - Technology: PostgreSQL 15 with PostGIS 3.3
  - Responsibilities: Persistent data storage, geospatial queries, ACID transactions
  - Features: Full-text search, JSON support, spatial indexing

- **Cache/Session Store**
  - Technology: Redis 7 Alpine
  - Responsibilities: Session management, temporary data, message brokering

**Deployment Architecture (Containerized):**

**1. Load Balancer Tier**
- **Nginx Container**
  - Technology: Nginx Alpine
  - Responsibilities: Reverse proxy, static file serving, SSL termination
  - Configuration: Load balancing, compression, security headers

**2. Application Tier**
- **Django Web Container**
  - Technology: Python 3.11, Django 5.0, Gunicorn 21.2
  - Responsibilities: Web request processing, API endpoints
  - Scaling: Horizontal scaling via multiple container instances

- **Celery Worker Container**
  - Technology: Celery worker processes
  - Responsibilities: Background task execution
  - Scaling: Independent scaling based on queue load

- **Celery Beat Container**
  - Technology: Celery beat scheduler
  - Responsibilities: Periodic task scheduling
  - Pattern: Single instance with database scheduler

**3. Data Tier**
- **PostgreSQL Container**
  - Technology: PostGIS/PostGIS:15-3.3
  - Responsibilities: Primary data storage
  - Features: Data persistence, backup capabilities

- **Redis Container**
  - Technology: Redis:7-alpine
  - Responsibilities: Caching, session storage, message brokering
  - Persistence: Append-only file (AOF) enabled

**Communication Patterns:**
- **Synchronous**: HTTP/HTTPS REST API calls between client and server
- **Asynchronous**: Celery task queue for background processing
- **Database**: Django ORM with connection pooling
- **Cache**: Redis protocol for caching operations
- **Real-time (Planned)**: WebSocket connections for live updates

**Security Architecture:**
- **Authentication**: Token-based authentication with session fallback
- **Authorization**: Role-based access control (RBAC) with object permissions
- **Data Protection**: HTTPS encryption, CSRF protection, XSS prevention
- **Network Security**: Container isolation, internal network communication

**Scalability Patterns:**
- **Horizontal Scaling**: Multiple Django/Celery containers behind load balancer
- **Database Scaling**: Read replicas, connection pooling
- **Caching Strategy**: Multi-level caching (Redis, application-level)
- **Background Processing**: Queue-based task distribution

**Technology Stack Summary:**
- **Backend**: Django 5.0, Python 3.11, Django REST Framework
- **Database**: PostgreSQL 15 + PostGIS 3.3, Redis 7
- **Queue**: Celery 5.3.4 with Redis broker
- **Web Server**: Nginx, Gunicorn WSGI
- **Frontend**: Django Templates, Bootstrap 4, JavaScript
- **Containerization**: Docker, Docker Compose
- **Security**: Django OTP, Guardian, CORS, CSRF protection

## Input & Output

• User inputs include service searches location filters and feedback submissions
• Manager inputs provide service details capacity updates and closure alerts
• System outputs deliver interactive maps filtered results and notifications
• API outputs enable mobile integration and third-party service consumption
• Admin outputs include user management reports and system monitoring
• Notification outputs support email alerts and dashboard updates

 The system processes various input types from different user roles and provides corresponding outputs through multiple channels. Users interact primarily through the web interface while managers update service information and administrators oversee system operations through specialized dashboards.

## Solution Achieved?

• Successfully implemented unified service discovery platform reducing information fragmentation
• Delivered real-time capacity monitoring with visual indicators for better decision-making
• Established comprehensive RBAC system supporting multiple stakeholder types
• Created mobile-responsive interface ensuring accessibility across device types
• Integrated feedback mechanisms building community trust and data accuracy
• Deployed scalable architecture supporting future growth and mobile expansion

 The project successfully delivers on its core objectives by creating a unified platform that reduces information barriers. The implemented solution provides real-time capabilities, comprehensive user management, and accessible interfaces while establishing a foundation for future scalability and mobile integration.

## Work Segregation

• Frontend development including responsive templates and user interfaces
• Backend development covering Django applications and REST API implementation
• Database design featuring geospatial models and relationship management
• Authentication system implementing RBAC and security middleware
• Infrastructure setup including Docker containerization and deployment configuration
• Testing and quality assurance across all system components

The development work was distributed across multiple technical domains including frontend and backend development, database design, and infrastructure setup. Each team member contributed to specific areas while maintaining integration points, ensuring comprehensive coverage of all system requirements and quality standards.
