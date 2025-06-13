"""
URL configuration for the moderators app.

Implements the exact URL structure from the role-by-role sitemap.md
for Community Moderator functionality.
"""
from django.urls import path
from . import views

app_name = 'moderators'

urlpatterns = [
    # Home page for Community Moderators
    path('home/', views.ModeratorHomeView.as_view(), name='home'),
    
    # Dashboard
    path('dashboard/', views.ModeratorDashboardView.as_view(), name='dashboard'),
    
    # Profile
    path('profile/', views.ModeratorProfileView.as_view(), name='profile'),
    
    # Service approval queue
    path('services/pending/', views.ServiceApprovalQueueView.as_view(), name='services_pending'),
    path('services/<uuid:pk>/edit/', views.ServiceModeratorEditView.as_view(), name='service_edit'),
    
    # Outreach management
    path('outreach/', views.OutreachView.as_view(), name='outreach'),
    path('outreach/new/', views.OutreachCreateView.as_view(), name='outreach_create'),
    path('outreach/<uuid:pk>/', views.OutreachDetailView.as_view(), name='outreach_detail'),
    path('outreach/<uuid:pk>/edit/', views.OutreachUpdateView.as_view(), name='outreach_edit'),
    path('outreach/<uuid:pk>/delete/', views.OutreachDeleteView.as_view(), name='outreach_delete'),
    
    # Feedback moderation
    path('feedback/', views.FeedbackModerationView.as_view(), name='feedback'),
    
    # Comment approval queue
    path('comments/pending/', views.CommentApprovalQueueView.as_view(), name='comments_pending'),
    path('comments/<uuid:pk>/thread/', views.CommentThreadView.as_view(), name='comment_thread'),
    
    # AJAX endpoints for approvals
    path('api/services/<uuid:pk>/approve/', views.ApproveServiceAPIView.as_view(), name='api_approve_service'),
    path('api/services/<uuid:pk>/reject/', views.RejectServiceAPIView.as_view(), name='api_reject_service'),
    path('api/services/bulk-approve/', views.BulkApproveServicesAPIView.as_view(), name='api_bulk_approve_services'),
    path('api/services/bulk-reject/', views.BulkRejectServicesAPIView.as_view(), name='api_bulk_reject_services'),
    
    path('api/comments/<uuid:pk>/approve/', views.ApproveCommentAPIView.as_view(), name='api_approve_comment'),
    path('api/comments/<uuid:pk>/reject/', views.RejectCommentAPIView.as_view(), name='api_reject_comment'),
    path('api/comments/bulk-approve/', views.BulkApproveCommentsAPIView.as_view(), name='api_bulk_approve_comments'),
    path('api/comments/bulk-reject/', views.BulkRejectCommentsAPIView.as_view(), name='api_bulk_reject_comments'),
    
    # Flag resolution
    path('api/flags/<uuid:pk>/resolve/', views.ResolveFlagAPIView.as_view(), name='api_resolve_flag'),
    
    # Notification management
    path('api/notifications/<uuid:pk>/mark-read/', views.MarkModeratorNotificationReadAPIView.as_view(), name='api_mark_notification_read'),
    
    # Action history
    path('actions/', views.ModerationActionsView.as_view(), name='actions'),
    path('actions/<uuid:pk>/', views.ModerationActionDetailView.as_view(), name='action_detail'),
] 