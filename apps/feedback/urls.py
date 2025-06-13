"""
URL configuration for the feedback app.
"""
from django.urls import path
from . import views

app_name = 'feedback'

urlpatterns = [
    # Review URLs
    path('services/<uuid:service_id>/reviews/', views.ServiceReviewListView.as_view(), name='review_list'),
    path('services/<uuid:service_id>/reviews/new/', views.CreateReviewView.as_view(), name='create_review'),
    path('reviews/<uuid:pk>/', views.ReviewDetailView.as_view(), name='review_detail'),
    path('reviews/<uuid:pk>/edit/', views.EditReviewView.as_view(), name='edit_review'),
    path('reviews/<uuid:pk>/vote/', views.ReviewVoteView.as_view(), name='vote_review'),
    
    # Comment URLs
    path('services/<uuid:service_id>/comments/', views.ServiceCommentListView.as_view(), name='comment_list'),
    path('services/<uuid:service_id>/comments/new/', views.CreateCommentView.as_view(), name='create_comment'),
    path('comments/<uuid:pk>/reply/', views.CreateCommentReplyView.as_view(), name='reply_comment'),
    path('comments/<uuid:pk>/like/', views.CommentLikeView.as_view(), name='like_comment'),
    path('comments/<uuid:pk>/delete/', views.DeleteCommentView.as_view(), name='delete_comment'),
    
    # Flagging URLs
    path('reviews/<uuid:review_id>/flag/', views.FlagReviewView.as_view(), name='flag_review'),
    path('comments/<uuid:comment_id>/flag/', views.FlagCommentView.as_view(), name='flag_comment'),
    
    # API endpoints for AJAX
    path('api/reviews/', views.ReviewAPIView.as_view(), name='api_reviews'),
    path('api/comments/', views.CommentAPIView.as_view(), name='api_comments'),
    path('api/reviews/create/<uuid:service_id>/', views.CreateReviewAPIView.as_view(), name='api_create_review'),
    path('api/comments/create/<uuid:service_id>/', views.CreateCommentAPIView.as_view(), name='api_create_comment'),
    
    # New API endpoints for like/reply functionality
    path('api/feedback/reply/', views.CreateReplyAPIView.as_view(), name='api_create_reply'),
    path('api/feedback/review/<uuid:review_id>/helpful/', views.ReviewHelpfulAPIView.as_view(), name='api_review_helpful'),
    path('api/feedback/review/<uuid:review_id>/unhelpful/', views.ReviewUnhelpfulAPIView.as_view(), name='api_review_unhelpful'),
    path('api/feedback/comment/<uuid:comment_id>/like/', views.CommentLikeAPIView.as_view(), name='api_comment_like'),
    path('reviews/<uuid:pk>/delete/', views.DeleteFeedbackView.as_view(), name='delete_feedback'),
] 