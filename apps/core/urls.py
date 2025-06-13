"""
URL configuration for the core app.
"""
from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Landing page
    path('', views.LandingPageView.as_view(), name='landing'),
    # Home alias (same as landing)
    path('home/', views.LandingPageView.as_view(), name='home'),
    
    # Health check
    path('health/', views.health_check, name='health_check'),
    
    # Authentication
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('signup/', views.UserRegistrationView.as_view(), name='signup'),
    path('register/', views.UserRegistrationView.as_view(), name='register'),  # Alias for signup
    path('registration-success/', views.RegistrationSuccessView.as_view(), name='registration_success'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Static pages
    path('about/', views.AboutView.as_view(), name='about'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy'),
    path('terms/', views.TermsOfServiceView.as_view(), name='terms'),
] 