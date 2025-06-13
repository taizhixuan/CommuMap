"""
Main URL configuration for CommuMap project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Admin
    path('django-admin/', admin.site.urls),
    
    # Core app - landing, auth
    path('', include('apps.core.urls')),
    
    # Authentication (allauth) - commented out until allauth is available
    # path('accounts/', include('allauth.urls')),
    
    # User-specific URLs
    path('u/', include('apps.users.urls')),
    
    # Service Manager URLs
    path('manager/', include('apps.managers.urls')),
    
    # Community Moderator URLs
    path('moderator/', include('apps.moderators.urls')),
    
    # Admin Console URLs
    path('admin/', include('apps.console.urls')),
    
    # Service discovery and details
    path('', include('apps.services.urls')),
    
    # Feedback system
    path('', include('apps.feedback.urls')),
    
    # API endpoints - commented out until api_urls is created
    # path('api/', include('apps.core.api_urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar
    if 'debug_toolbar' in settings.INSTALLED_APPS:
        import debug_toolbar
        urlpatterns = [
            path('__debug__/', include(debug_toolbar.urls)),
        ] + urlpatterns 