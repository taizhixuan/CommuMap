"""
Management command to verify service manager accounts.
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.core.models import UserRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Verify service manager accounts'

    def add_arguments(self, parser):
        parser.add_argument(
            'email',
            type=str,
            help='Email of the service manager to verify'
        )

    def handle(self, *args, **options):
        email = options['email']
        
        try:
            # Get the service manager user
            service_manager = User.objects.get(email=email, role=UserRole.SERVICE_MANAGER)
            
            # Create or get an admin user to perform the verification
            admin_user, created = User.objects.get_or_create(
                email='admin@commumap.com',
                defaults={
                    'first_name': 'Admin',
                    'last_name': 'User',
                    'role': UserRole.ADMIN,
                    'is_verified': True
                }
            )
            
            if created:
                admin_user.set_password('admin123')
                admin_user.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Created admin user: {admin_user.email}')
                )
            
            # Verify the service manager
            service_manager.verify_user(admin_user)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully verified service manager: {service_manager.email}'
                )
            )
            
        except User.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(
                    f'Service manager with email {email} not found'
                )
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error: {str(e)}')
            ) 