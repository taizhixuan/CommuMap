"""
Management command to create sample comments for testing the moderation system.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.core.models import User
from apps.services.models import Service
from apps.feedback.models import ServiceComment, ServiceReview
import random


class Command(BaseCommand):
    help = 'Create sample comments and reviews for testing the moderation system'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--comments',
            type=int,
            default=5,
            help='Number of sample comments to create'
        )
        parser.add_argument(
            '--reviews',
            type=int,
            default=3,
            help='Number of sample flagged reviews to create'
        )
    
    def handle(self, *args, **options):
        # Get or create test users
        test_users = []
        user_data = [
            {'email': 'alice.user@test.com', 'full_name': 'Alice Johnson'},
            {'email': 'bob.user@test.com', 'full_name': 'Bob Smith'},
            {'email': 'carol.user@test.com', 'full_name': 'Carol Davis'},
            {'email': 'david.user@test.com', 'full_name': 'David Wilson'},
            {'email': 'eva.user@test.com', 'full_name': 'Eva Rodriguez'},
        ]
        
        for data in user_data:
            user, created = User.objects.get_or_create(
                email=data['email'],
                defaults={
                    'full_name': data['full_name'],
                    'is_active': True,
                    'role': 'resident'
                }
            )
            test_users.append(user)
            if created:
                self.stdout.write(f'Created user: {user.full_name}')
        
        # Get existing services or create sample ones
        services = list(Service.objects.all()[:10])
        if not services:
            self.stdout.write(self.style.WARNING('No services found. Creating sample services...'))
            # Create some basic services for testing
            from apps.services.models import ServiceCategory
            category, _ = ServiceCategory.objects.get_or_create(
                name='Community Services',
                defaults={'description': 'General community services'}
            )
            
            service_data = [
                'Food Bank Central',
                'Community Health Center', 
                'Housing Assistance Office',
                'Job Training Center',
                'Senior Care Services'
            ]
            
            for name in service_data:
                service, created = Service.objects.get_or_create(
                    name=name,
                    defaults={
                        'description': f'Sample service: {name}',
                        'category': category,
                        'address': '123 Test St',
                        'is_verified': True
                    }
                )
                services.append(service)
                if created:
                    self.stdout.write(f'Created service: {service.name}')
        
        # Sample comment content
        comment_templates = [
            "This service has been really helpful for our family. The staff is professional and caring.",
            "Great experience here! Fast service and friendly people. Highly recommend.",
            "The wait times can be long but the help is worth it. Staff does their best.",
            "Could use better organization but overall helpful service for the community.",
            "Excellent programs available here. Made a real difference in my life.",
            "Service is okay but could be improved. Sometimes hard to get information.",
            "Very satisfied with the assistance provided. Professional and efficient.",
            "Good location and hours. Staff is knowledgeable about available resources."
        ]
        
        # Create sample comments
        for i in range(options['comments']):
            user = random.choice(test_users)
            service = random.choice(services)
            content = random.choice(comment_templates)
            
            comment = ServiceComment.objects.create(
                user=user,
                service=service,
                content=content,
                is_approved=False,  # Pending approval
                created_at=timezone.now() - timezone.timedelta(hours=random.randint(1, 48))
            )
            
            self.stdout.write(f'Created comment by {user.full_name} for {service.name}')
        
        # Sample flagged review content
        flagged_review_templates = [
            {
                'content': "This place is terrible! Staff was rude and unhelpful. Complete waste of time.",
                'rating': 1,
                'reason': 'inappropriate_language'
            },
            {
                'content': "The doctor here doesn't know what he's doing. Maybe he should go back to medical school.",
                'rating': 2,
                'reason': 'defamatory_statements'
            },
            {
                'content': "Great service! You can reach them at 555-1234 or visit them at 123 Main St. Ask for John.",
                'rating': 5,
                'reason': 'privacy_violation'
            }
        ]
        
        # Create sample flagged reviews
        for i in range(min(options['reviews'], len(flagged_review_templates))):
            user = random.choice(test_users)
            service = random.choice(services)
            template = flagged_review_templates[i]
            
            review = ServiceReview.objects.create(
                user=user,
                service=service,
                title=f"Review for {service.name}",
                content=template['content'],
                rating=template['rating'],
                is_flagged=True,
                created_at=timezone.now() - timezone.timedelta(hours=random.randint(1, 72))
            )
            
            self.stdout.write(f'Created flagged review by {user.full_name} for {service.name}')
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\nSuccessfully created:\n'
                f'- {options["comments"]} pending comments\n'
                f'- {min(options["reviews"], len(flagged_review_templates))} flagged reviews\n'
                f'Ready for moderation testing!'
            )
        ) 