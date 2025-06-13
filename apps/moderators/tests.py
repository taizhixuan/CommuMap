"""
Tests for the moderators app.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model

from apps.core.models import UserRole
from apps.services.models import Service, ServiceCategory, ServiceComment
from .models import OutreachPost, ModerationAction

User = get_user_model()


class ModeratorTestCase(TestCase):
    """
    Base test case for moderator functionality.
    """
    
    def setUp(self):
        # Create test users
        self.moderator = User.objects.create_user(
            email='moderator@test.com',
            password='testpass123',
            role=UserRole.COMMUNITY_MODERATOR,
            is_verified=True,
            full_name='Test Moderator'
        )
        
        self.regular_user = User.objects.create_user(
            email='user@test.com',
            password='testpass123',
            role=UserRole.USER,
            is_verified=True
        )
        
        # Create test data
        self.category = ServiceCategory.objects.create(
            name='Test Category',
            description='Test category description'
        )
        
        self.client = Client()


class ModeratorAccessTestCase(ModeratorTestCase):
    """
    Test moderator access control.
    """
    
    def test_moderator_can_access_dashboard(self):
        """Test that verified moderators can access the dashboard."""
        self.client.login(email='moderator@test.com', password='testpass123')
        response = self.client.get(reverse('moderators:dashboard'))
        self.assertEqual(response.status_code, 200)
    
    def test_regular_user_cannot_access_dashboard(self):
        """Test that regular users cannot access moderator dashboard."""
        self.client.login(email='user@test.com', password='testpass123')
        response = self.client.get(reverse('moderators:dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_anonymous_user_redirected_to_login(self):
        """Test that anonymous users are redirected to login."""
        response = self.client.get(reverse('moderators:dashboard'))
        self.assertEqual(response.status_code, 302)


class OutreachPostTestCase(ModeratorTestCase):
    """
    Test outreach post functionality.
    """
    
    def test_create_outreach_post(self):
        """Test creating an outreach post."""
        post = OutreachPost.objects.create(
            title='Test Post',
            content='Test content',
            created_by=self.moderator
        )
        self.assertEqual(post.title, 'Test Post')
        self.assertEqual(post.created_by, self.moderator)
        self.assertTrue(post.is_active)
    
    def test_outreach_post_str_representation(self):
        """Test string representation of outreach post."""
        post = OutreachPost.objects.create(
            title='Test Post',
            content='Test content',
            created_by=self.moderator
        )
        expected = f"Test Post by {self.moderator.get_display_name()}"
        self.assertEqual(str(post), expected)


class ModerationActionTestCase(ModeratorTestCase):
    """
    Test moderation action logging.
    """
    
    def test_log_action_helper(self):
        """Test the log_action helper method."""
        action = ModerationAction.log_action(
            moderator=self.moderator,
            action_type='approve_service',
            reason='Test approval'
        )
        self.assertEqual(action.moderator, self.moderator)
        self.assertEqual(action.action_type, 'approve_service')
        self.assertEqual(action.reason, 'Test approval')
    
    def test_moderation_action_str_representation(self):
        """Test string representation of moderation action."""
        action = ModerationAction.log_action(
            moderator=self.moderator,
            action_type='approve_service',
            reason='Test approval'
        )
        expected = f"{self.moderator.get_display_name()}: Approved Service"
        self.assertEqual(str(action), expected) 