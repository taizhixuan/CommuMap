"""
URL configuration for the services app.
"""
from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    # Service listings
    path('services/', views.ServiceListView.as_view(), name='list'),
    
    # Service detail
    path('services/<uuid:pk>/', views.ServiceDetailView.as_view(), name='detail'),
    
    # Service search
    path('search/', views.ServiceSearchView.as_view(), name='search'),
    
    # Category view
    path('category/<slug:category_slug>/', views.CategoryDetailView.as_view(), name='category'),
    
    # Map view
    path('map/', views.ServiceMapView.as_view(), name='map'),
    
    # Service management (for service managers)
    path('manage/', views.ServiceManagementView.as_view(), name='manage'),
    
    # API endpoints
    path('api/services/bookmark/<uuid:service_id>/', views.BookmarkToggleAPIView.as_view(), name='bookmark_toggle'),
] 