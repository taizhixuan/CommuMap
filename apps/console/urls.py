"""
URL configuration for CommuMap Admin Console.

Implements the exact URL structure specified in the role-by-role sitemap.
"""
from django.urls import path
from . import views

app_name = 'console'

urlpatterns = [
    # Admin home page
    path('', views.AdminHomeView.as_view(), name='home'),
    path('home/', views.AdminHomeView.as_view(), name='home_alt'),
    
    # Main admin dashboard
    path('dashboard/', views.AdminDashboardView.as_view(), name='dashboard'),
    
    # Admin profile management
    path('profile/', views.AdminProfileView.as_view(), name='profile'),
    
    # User management
    path('users/', views.UserManagementView.as_view(), name='users'),
    path('users/add/', views.UserCreateView.as_view(), name='user_add'),
    path('users/<uuid:user_id>/edit/', views.UserEditView.as_view(), name='user_edit'),
    path('users/<uuid:user_id>/delete/', views.UserDeleteView.as_view(), name='user_delete'),
    path('users/<uuid:user_id>/reactivate/', views.UserReactivateView.as_view(), name='user_reactivate'),
    path('users/pending-managers/', views.PendingManagersView.as_view(), name='pending_managers'),
    path('users/pending-moderators/', views.PendingModeratorsView.as_view(), name='pending_moderators'),
    
    # User verification actions
    path('users/<uuid:user_id>/verify/', views.VerifyUserView.as_view(), name='verify_user'),
    path('users/<uuid:user_id>/reject/', views.RejectUserView.as_view(), name='reject_user'),
    
    # Service management
    path('services/', views.ServiceManagementView.as_view(), name='services'),
    path('services/add/', views.AdminServiceCreateView.as_view(), name='service_create'),
    path('services/<uuid:service_id>/edit/', views.AdminServiceEditView.as_view(), name='service_edit'),
    path('services/<uuid:service_id>/emergency-toggle/', views.EmergencyToggleView.as_view(), name='emergency_toggle'),
    path('services/<uuid:service_id>/delete/', views.AdminServiceDeleteView.as_view(), name='service_delete'),
    path('services/bulk-action/', views.BulkServiceActionView.as_view(), name='bulk_service_action'),
    
    # System announcements
    path('announcements/', views.AnnouncementView.as_view(), name='announcements'),
    path('announcements/add/', views.AnnouncementCreateView.as_view(), name='announcement_add'),
    path('announcements/<uuid:announcement_id>/edit/', views.AnnouncementEditView.as_view(), name='announcement_edit'),
    path('announcements/<uuid:announcement_id>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
    
    # Maintenance tools
    path('maintenance/', views.MaintenanceToolsView.as_view(), name='maintenance'),
    path('maintenance/backup/', views.BackupDatabaseView.as_view(), name='backup_database'),
    path('maintenance/cache-clear/', views.ClearCacheView.as_view(), name='clear_cache'),
    path('maintenance/log-rotation/', views.LogRotationView.as_view(), name='log_rotation'),
    path('maintenance/feature-toggle/', views.FeatureToggleView.as_view(), name='feature_toggle'),
    path('maintenance/cleanup/', views.DataCleanupView.as_view(), name='data_cleanup'),
    
    # Global feedback and comments management
    path('feedback/', views.AdminFeedbackView.as_view(), name='feedback'),
    path('feedback/<uuid:feedback_id>/reply/', views.FeedbackReplyView.as_view(), name='feedback_reply'),
    path('comments/', views.AdminCommentsView.as_view(), name='comments'),
    path('comments/<uuid:comment_id>/reply/', views.CommentReplyView.as_view(), name='comment_reply'),
    path('comments/<uuid:comment_id>/delete/', views.CommentDeleteView.as_view(), name='comment_delete'),
    
    # System monitoring and health checks
    path('system/health/', views.SystemHealthView.as_view(), name='system_health'),
    path('system/metrics/', views.SystemMetricsView.as_view(), name='system_metrics'),
    path('system/audit-logs/', views.AuditLogsView.as_view(), name='audit_logs'),
    
    # Emergency mode management
    path('emergency/toggle/', views.EmergencyModeToggleView.as_view(), name='emergency_mode_toggle'),
    
    # Settings management
    path('settings/', views.SystemSettingsView.as_view(), name='settings'),
    path('settings/backup/', views.SettingsBackupView.as_view(), name='settings_backup')
] 