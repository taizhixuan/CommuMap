"""
URL configuration for the users app.
"""
from django.urls import path
from . import views

app_name = 'users'

urlpatterns = [
    # User dashboard
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # User profile and preferences
    path('profile/', views.profile_view, name='profile'),
    path('profile/edit/', views.profile_edit_view, name='profile_edit'),
    path('profile/password/', views.password_change_view, name='password_change'),
    path('profile/preferences/', views.preferences_update_view, name='preferences_update'),
    path('preferences/', views.UserPreferencesUpdateView.as_view(), name='preferences'),
    
    # User bookmarks with enhanced functionality
    path('bookmarks/', views.bookmarks_view, name='bookmarks'),
    path('api/bookmark-toggle/', views.bookmark_toggle_view, name='bookmark_toggle'),
    
    # User notifications
    path('notifications/', views.notifications_view, name='notifications'),
    
    # Recommendations
    path('recommendations/', views.recommendations_view, name='recommendations'),
    
    # Search history and analytics
    path('search-history/', views.search_history_view, name='search_history'),
] 