"""
URL configuration for the managers app.

Implements the exact URL structure from the role-by-role sitemap.md
for Service Manager functionality.
"""
from django.urls import path
from . import views

app_name = 'manager'

urlpatterns = [
    # Home page for Service Managers
    path('home/', views.ManagerHomeView.as_view(), name='home'),
    
    # Dashboard
    path('dashboard/', views.ManagerDashboardView.as_view(), name='dashboard'),
    
    # Profile
    path('profile/', views.ManagerProfileView.as_view(), name='profile'),
    
    # Services management
    path('services/', views.ManagerServicesView.as_view(), name='services'),
    path('services/add/', views.ServiceCreateView.as_view(), name='service_create'),
    path('services/<uuid:pk>/edit/', views.ServiceUpdateView.as_view(), name='service_edit'),
    path('services/<uuid:pk>/delete/', views.ServiceDeleteView.as_view(), name='service_delete'),
    
    # Real-time status management
    path('services/<uuid:pk>/status/', views.ServiceStatusView.as_view(), name='service_status'),
    
    # Analytics and reporting
    path('services/<uuid:pk>/analytics/', views.ServiceAnalyticsView.as_view(), name='service_analytics'),
    path('services/<uuid:pk>/analytics/report/', views.GenerateReportView.as_view(), name='generate_report'),
    
    # Feedback and comments management
    path('services/<uuid:pk>/feedback/', views.ServiceFeedbackView.as_view(), name='service_feedback'),
    path('services/<uuid:pk>/comments/', views.ServiceCommentsView.as_view(), name='service_comments'),
    
    # AJAX endpoints for real-time updates
    path('api/services/<uuid:pk>/status/update/', views.UpdateServiceStatusAPIView.as_view(), name='api_update_status'),
    path('api/services/<uuid:pk>/capacity/update/', views.UpdateCapacityAPIView.as_view(), name='api_update_capacity'),
    path('api/notifications/mark-read/<uuid:pk>/', views.MarkNotificationReadAPIView.as_view(), name='api_mark_notification_read'),
] 