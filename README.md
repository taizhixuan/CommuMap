# CommuMap

**Community Resource Mapping & Public Services Locator**

A web-based platform that empowers residents to discover, evaluate, and access essential community resources through an interactive map interface. CommuMap bridges the gap between community services and those who need them most.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Tech Stack](#tech-stack)
- [Architecture & Design Patterns](#architecture--design-patterns)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Running the Application](#running-the-application)
- [User Roles](#user-roles)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview

CommuMap is a comprehensive community service mapping platform designed to address the critical challenge of fragmented and outdated community resource information. The platform serves as a centralized hub where residents can:

- **Discover** essential services including healthcare clinics, emergency shelters, food banks, libraries, learning centers, and more
- **Access** real-time information about operating hours, current capacity, and service availability
- **Evaluate** services through community feedback and ratings
- **Navigate** to services using an intuitive, mobile-responsive map interface

### Mission Alignment

CommuMap directly advances **UN Sustainable Development Goals**:
- **SDG 10**: Reduced Inequalities - by lowering information barriers that disproportionately affect vulnerable populations
- **SDG 11**: Sustainable Cities & Communities - by improving urban service infrastructure and accessibility

---

## Key Features

### For All Users

- **Interactive Map Interface**: Real-time visualization of community services with intuitive filtering
- **Advanced Search & Filters**: Search by category, distance, status, and accessibility requirements
- **"Help Me Now" Emergency Mode**: One-tap access to verified, open emergency services within 5km
- **Service Details**: Comprehensive information including:
  - Operating hours and contact information
  - Real-time capacity indicators
  - User ratings and reviews
  - Accessibility features
  - Appointment requirements
- **Bookmarking System**: Save and organize favorite services for quick access
- **Mobile-Responsive Design**: Seamless experience across desktop, tablet, and mobile devices

### For Service Managers

- **Service Management Dashboard**: Create and maintain service listings
- **Real-Time Updates**: Push live capacity and status changes
- **Closure Alerts**: Broadcast temporary closures or urgent updates
- **Analytics & Reports**: Monitor service usage and user feedback
- **Verification System**: Trusted badge for verified service providers

### For Community Moderators

- **Content Moderation**: Review and approve service listings
- **Feedback Management**: Moderate user comments and reviews
- **Bulk Operations**: Efficiently manage multiple submissions
- **Quality Assurance**: Ensure data accuracy and community trust

### For Administrators

- **User Management**: Manage user accounts and role assignments
- **System Configuration**: Control platform-wide settings
- **Emergency Management**: Toggle emergency mode and manage alerts
- **Audit Logging**: Track administrative actions for security and compliance
- **System Monitoring**: Monitor platform health and performance

---

## Tech Stack

### Backend
- **Framework**: Django 5.0.0
- **API**: Django REST Framework 3.14.0
- **Database**: SQLite (development), PostgreSQL + PostGIS (production)
- **Task Queue**: Celery 5.3.4
- **Cache/Broker**: Redis 5.0.1

### Frontend
- **Templates**: Django Templates
- **JavaScript**: Vanilla JS with modern ES6+ features
- **Maps**: Leaflet.js + OpenStreetMap (configurable for Google Maps, Mapbox)
- **Styling**: CSS3 with responsive design

### Security & Authentication
- **Authentication**: Django's built-in auth system
- **2FA**: Django OTP 1.2.3
- **Permissions**: Django Guardian 2.4.0 (object-level permissions)
- **CORS**: Django CORS Headers 4.4.0

### Development & Testing
- **Testing**: Pytest Django 4.7.0
- **Test Data**: Factory Boy 3.3.0, Model Bakery 1.17.0
- **Debugging**: Django Debug Toolbar 4.2.0

### Deployment
- **WSGI Server**: Gunicorn 21.2.0
- **Static Files**: WhiteNoise 6.6.0
- **Containerization**: Docker & Docker Compose

---

## Architecture & Design Patterns

CommuMap implements several robust design patterns for maintainability and scalability:

### Design Patterns

1. **Singleton Pattern** (`apps/core/models.py`)
   - `SystemSettings`: Thread-safe global configuration management
   - `NotificationDispatcher`: System-wide messaging coordination

2. **Observer Pattern** (`apps/services/signals.py`)
   - Real-time status change notifications
   - Automated alerts for capacity thresholds
   - Custom Django signals for service events

3. **Strategy Pattern** (`apps/services/strategies.py`)
   - Pluggable search algorithms:
     - `BasicTextSearchStrategy`
     - `GeographicSearchStrategy`
     - `EmergencySearchStrategy`
     - `AvailabilitySearchStrategy`

4. **Adapter Pattern** (`apps/services/adapters.py`)
   - Multi-provider map support (Leaflet, Google Maps, Mapbox)
   - External data source integration (Government 311, NGO APIs)

5. **Factory Method Pattern** (`apps/services/factories.py`)
   - Service creation with type-specific defaults:
     - `HealthcareServiceFactory`
     - `ShelterServiceFactory`
     - `FoodServiceFactory`
     - `EmergencyServiceFactory`

6. **Repository Pattern** (`apps/services/models.py`)
   - Custom QuerySet managers for domain-specific queries
   - Chainable query methods for complex filtering

### Key Architectural Features

- **Role-Based Access Control (RBAC)**: Fine-grained permissions system
- **Real-Time Data Pipelines**: Instant status updates and notifications
- **Geographic Indexing**: Optimized location-based queries
- **Audit Logging**: Complete trail of administrative actions
- **Moderation Queue**: Transparent content review workflow

---

## Getting Started

### Prerequisites

- **Python**: 3.8 or higher
- **Git**: Latest version
- **Storage**: Minimum 500MB free space
- **Memory**: 4GB RAM recommended

### Installation

1. **Clone the Repository**
   ```bash
   git clone https://github.com/yourusername/CommuMap.git
   cd CommuMap
   ```

2. **Set Up Virtual Environment**
   ```bash
   # Create virtual environment
   python -m venv .venv

   # Activate virtual environment
   # On Linux/macOS:
   source .venv/bin/activate

   # On Windows:
   .venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create Required Directories**
   ```bash
   mkdir logs
   ```

5. **Configure Environment Variables**
   ```bash
   cp env.example .env
   # Edit .env file with your configuration
   ```

6. **Set Up Database**
   ```bash
   # Run migrations
   python manage.py migrate

   # Create superuser (for admin access)
   python manage.py createsuperuser
   ```

7. **Load Initial Data (Optional)**
   ```bash
   # Load sample service categories and data
   python manage.py loaddata initial_data.json
   ```

### Running the Application

1. **Start the Development Server**
   ```bash
   python manage.py runserver
   ```

2. **Access the Application**
   - Main Application: http://127.0.0.1:8000/
   - Admin Panel: http://127.0.0.1:8000/admin/

### Test Accounts

The database includes pre-populated test accounts:

| Role | Email | Password | Access Level |
|------|-------|----------|--------------|
| **Admin** | admin@commumap.com | admin123 | Full system control |
| **User** | usertesting@gmail.com | user@123 | Service discovery, feedback |
| **Service Manager** | smtest@gmail.com | manager@123 | Service management |
| **Community Moderator** | cmtest@gmail.com | moderator@123 | Content moderation |

---

## User Roles

### Regular Users
- Search and browse community services
- View detailed service information
- Bookmark favorite services
- Submit reviews and feedback
- Receive notifications about bookmarked services

### Service Managers
- Create and manage service listings
- Update real-time capacity and status
- Respond to user feedback
- Generate service analytics reports
- Push emergency alerts and closures

### Community Moderators
- Review and approve new service listings
- Moderate user comments and reviews
- Verify service information accuracy
- Manage content quality
- Handle user reports

### Administrators
- Manage all user accounts and roles
- Configure system-wide settings
- Tag emergency services
- Broadcast system announcements
- Access audit logs and system monitoring
- Perform platform maintenance

---

## Project Structure

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
│   │   ├── base.py               # Shared settings
│   │   ├── development.py        # Development settings
│   │   └── production.py         # Production settings
│   ├── urls.py                   # Main URL routing
│   ├── wsgi.py                   # WSGI configuration
│   └── asgi.py                   # ASGI configuration
├── templates/                     # Django templates
├── static/                        # Static assets (CSS, JS, images)
├── staticfiles/                   # Collected static files
├── logs/                          # Application logs
├── requirements.txt               # Python dependencies
├── manage.py                      # Django management script
├── db.sqlite3                     # SQLite database (development)
├── docker-compose.yml             # Docker orchestration
├── Dockerfile                     # Container definition
├── .env.example                   # Environment variables template
└── README.md                      # This file
```

---

## API Documentation

### REST Endpoints

#### Service Discovery
- `GET /api/services/` - List services with filtering
- `GET /api/services/<id>/` - Service detail
- `GET /api/services/map-data/` - Geospatial data for map
- `GET /api/services/categories/` - Service categories

#### Service Management (Auth Required)
- `POST /api/services/` - Create service
- `PUT /api/services/<id>/` - Update service
- `POST /api/services/<id>/status/` - Update status
- `POST /api/services/<id>/capacity/` - Update capacity

#### Feedback (Auth Required)
- `POST /api/feedback/reviews/` - Submit review
- `POST /api/feedback/comments/` - Add comment
- `POST /api/feedback/reviews/<id>/helpful/` - Mark review helpful

#### Moderation (Moderator/Admin Only)
- `POST /api/moderate/services/<id>/approve/` - Approve service
- `POST /api/moderate/services/<id>/reject/` - Reject service
- `POST /api/moderate/bulk-approve/` - Bulk approve services

### Authentication
All protected endpoints require authentication via Django session or token authentication.

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=apps

# Run specific app tests
pytest apps/services/tests/

# Run with verbose output
pytest -v
```

### Test Structure

```
apps/
└── <app_name>/
    └── tests/
        ├── test_models.py
        ├── test_views.py
        ├── test_apis.py
        └── test_utils.py
```

---

## Deployment

### Docker Deployment

1. **Build and Run with Docker Compose**
   ```bash
   docker-compose up -d
   ```

2. **Run Migrations in Container**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Create Superuser**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

### Production Checklist

- [ ] Set `DEBUG = False` in production settings
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set up PostgreSQL database
- [ ] Configure Redis for caching
- [ ] Set up Celery workers for background tasks
- [ ] Configure email backend for notifications
- [ ] Set up SSL/TLS certificates
- [ ] Configure static file serving (WhiteNoise or CDN)
- [ ] Set up backup procedures
- [ ] Configure monitoring and logging
- [ ] Enable security features (CSRF, XFrame protection, etc.)

---

## Contributing

We welcome contributions to CommuMap! Here's how you can help:

### Development Workflow

1. **Fork the Repository**
   ```bash
   git clone https://github.com/yourusername/CommuMap.git
   cd CommuMap
   ```

2. **Create a Feature Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make Your Changes**
   - Follow PEP 8 style guidelines
   - Add tests for new functionality
   - Update documentation as needed

4. **Run Tests**
   ```bash
   pytest
   ```

5. **Commit Your Changes**
   ```bash
   git commit -m "Add: brief description of changes"
   ```

6. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

### Coding Standards

- Follow Django best practices
- Write meaningful commit messages
- Add docstrings to functions and classes
- Maintain test coverage above 80%
- Update documentation for API changes

### Areas for Contribution

- New service categories and types
- Additional map provider integrations
- Accessibility improvements
- Internationalization and localization
- Performance optimizations
- Mobile app development
- API enhancements

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## Acknowledgments

### Built With

- [Django](https://www.djangoproject.com/) - The web framework for perfectionists with deadlines
- [Leaflet](https://leafletjs.com/) - Open-source JavaScript library for mobile-friendly interactive maps
- [OpenStreetMap](https://www.openstreetmap.org/) - Free, editable map of the world

### Inspiration

CommuMap was inspired by the need to:
- Reduce information barriers in accessing community services
- Support vulnerable populations in finding critical resources
- Advance UN Sustainable Development Goals 10 and 11
- Build more equitable and resilient communities

### Contact & Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/CommuMap/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/CommuMap/discussions)
- **Email**: support@commumap.com

---

**Made with ❤️ for building more inclusive communities**
