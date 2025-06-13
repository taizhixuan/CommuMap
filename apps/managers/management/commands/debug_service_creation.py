"""
Django management command to debug service creation issues.
"""

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import UserRole
from apps.services.models import Service, ServiceCategory
from apps.managers.models import ManagerNotification
from apps.moderators.models import ModeratorNotification
from decimal import Decimal

User = get_user_model()


class Command(BaseCommand):
    help = 'Debug service creation and notification system'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-user',
            action='store_true',
            help='Create test users',
        )
        parser.add_argument(
            '--test-service',
            action='store_true',
            help='Create test service',
        )
        parser.add_argument(
            '--test-notifications',
            action='store_true',
            help='Test notification creation',
        )
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up test data',
        )

    def handle(self, *args, **options):
        if options['cleanup']:
            self.cleanup_test_data()
        
        if options['test_user']:
            self.create_test_users()
        
        if options['test_service']:
            self.create_test_service()
        
        if options['test_notifications']:
            self.test_notifications()
    
    def create_test_users(self):
        """Create test users for debugging."""
        self.stdout.write('Creating test users...')
        
        # Create service manager
        manager, created = User.objects.get_or_create(
            email='test.manager@debug.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Manager',
                'full_name': 'Test Manager',
                'role': UserRole.SERVICE_MANAGER,
                'is_verified': True,
                'is_active': True,
            }
        )
        if created:
            manager.set_password('debug123')
            manager.save()
            self.stdout.write(f'Created service manager: {manager.email}')
        else:
            self.stdout.write(f'Service manager already exists: {manager.email}')
        
        # Create moderator
        moderator, created = User.objects.get_or_create(
            email='test.moderator@debug.com',
            defaults={
                'first_name': 'Test',
                'last_name': 'Moderator',
                'full_name': 'Test Moderator',
                'role': UserRole.COMMUNITY_MODERATOR,
                'is_verified': True,
                'is_active': True,
            }
        )
        if created:
            moderator.set_password('debug123')
            moderator.save()
            self.stdout.write(f'Created moderator: {moderator.email}')
        else:
            self.stdout.write(f'Moderator already exists: {moderator.email}')
    
    def create_test_service(self):
        """Create a test service to check if basic creation works."""
        self.stdout.write('Creating test service...')
        
        try:
            # Get test manager
            manager = User.objects.get(email='test.manager@debug.com')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Test manager not found. Run with --test-user first.'))
            return
        
        # Get or create category
        category, created = ServiceCategory.objects.get_or_create(
            name='Debug Category',
            defaults={
                'description': 'Category for debugging',
                'is_active': True,
            }
        )
        
        try:
            # Create service directly
            service = Service.objects.create(
                name='Debug Test Service',
                description='A service created for debugging purposes',
                short_description='Debug service',
                category=category,
                manager=manager,
                is_verified=False,
                address='123 Debug Street',
                country='Malaysia',
                current_capacity=0,
                quality_score=Decimal('0.00'),
                total_ratings=0,
                current_status='open',
            )
            self.stdout.write(self.style.SUCCESS(f'Successfully created service: {service.name} (ID: {service.pk})'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create service: {str(e)}'))
            import traceback
            traceback.print_exc()
    
    def test_notifications(self):
        """Test notification creation manually."""
        self.stdout.write('Testing notification creation...')
        
        try:
            # Get test users
            manager = User.objects.get(email='test.manager@debug.com')
            moderator = User.objects.get(email='test.moderator@debug.com')
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR('Test users not found. Run with --test-user first.'))
            return
        
        try:
            # Get test service
            service = Service.objects.filter(name='Debug Test Service').first()
            if not service:
                self.stdout.write(self.style.ERROR('Test service not found. Run with --test-service first.'))
                return
            
            # Test ModeratorNotification creation
            mod_notification = ModeratorNotification.objects.create(
                moderator=moderator,
                notification_type='new_service_submitted',
                title=f'Debug: New Service Submitted: {service.name}',
                message=f'Debug test notification for service {service.name}',
                priority='normal',
                related_service=service,
                action_url='/moderators/services/pending/'
            )
            self.stdout.write(self.style.SUCCESS(f'Created moderator notification: {mod_notification.pk}'))
            
            # Test ManagerNotification creation
            mgr_notification = ManagerNotification.objects.create(
                manager=manager,
                notification_type='service_approved',
                title=f'Debug: Service Approved: {service.name}',
                message=f'Debug test notification for service approval',
                priority='normal',
                related_service=service,
                action_url='/manager/services/'
            )
            self.stdout.write(self.style.SUCCESS(f'Created manager notification: {mgr_notification.pk}'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Failed to create notifications: {str(e)}'))
            import traceback
            traceback.print_exc()
    
    def cleanup_test_data(self):
        """Clean up test data."""
        self.stdout.write('Cleaning up test data...')
        
        # Delete test notifications
        ModeratorNotification.objects.filter(title__contains='Debug:').delete()
        ManagerNotification.objects.filter(title__contains='Debug:').delete()
        
        # Delete test service
        Service.objects.filter(name='Debug Test Service').delete()
        
        # Delete test category
        ServiceCategory.objects.filter(name='Debug Category').delete()
        
        # Delete test users
        User.objects.filter(email__in=['test.manager@debug.com', 'test.moderator@debug.com']).delete()
        
        self.stdout.write(self.style.SUCCESS('Test data cleaned up')) 