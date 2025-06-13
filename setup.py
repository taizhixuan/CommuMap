#!/usr/bin/env python
"""
CommuMap Setup Script

This script helps set up the CommuMap development environment.
Run this after installing requirements and setting up PostgreSQL with PostGIS.
"""

import os
import sys
import subprocess
import django
from pathlib import Path

# Add the project root to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commumap.settings.development')

def run_command(command, description=""):
    """Run a shell command and handle errors."""
    print(f"\n🔄 {description or command}")
    try:
        result = subprocess.run(command, shell=True, check=True, 
                              capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def check_requirements():
    """Check if required packages are installed."""
    print("🔍 Checking requirements...")
    
    required_packages = [
        'django',
        'psycopg2',
        'django-environ',
        'pillow',
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing packages: {', '.join(missing_packages)}")
        print("Please install requirements: pip install -r requirements.txt")
        return False
    
    print("✅ All required packages are installed")
    return True

def setup_django():
    """Set up Django application."""
    print("\n🚀 Setting up Django...")
    
    # Import Django and configure
    django.setup()
    
    # Run migrations
    if not run_command("python manage.py makemigrations", "Creating migrations"):
        return False
        
    if not run_command("python manage.py migrate", "Running migrations"):
        return False
    
    # Collect static files
    if not run_command("python manage.py collectstatic --noinput", "Collecting static files"):
        return False
    
    return True

def create_superuser():
    """Create a superuser account."""
    print("\n👤 Creating superuser account...")
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    if User.objects.filter(is_superuser=True).exists():
        print("✅ Superuser already exists")
        return True
    
    try:
        # Create admin user
        user = User.objects.create_superuser(
            username='admin',
            email='admin@commumap.com',
            password='admin123',
            first_name='Admin',
            last_name='User',
            role='admin'
        )
        print("✅ Superuser created: admin / admin123")
        return True
    except Exception as e:
        print(f"❌ Error creating superuser: {e}")
        return False

def create_sample_data():
    """Create sample service categories and data."""
    print("\n📊 Creating sample data...")
    
    try:
        from apps.services.models import ServiceCategory, Service
        from apps.core.models import User
        from django.contrib.gis.geos import Point
        
        # Create service categories
        categories_data = [
            {
                'name': 'Healthcare',
                'slug': 'healthcare',
                'description': 'Medical services, clinics, and health resources',
                'icon_class': 'fas fa-heartbeat',
                'color': '#ef4444'
            },
            {
                'name': 'Food Assistance',
                'slug': 'food',
                'description': 'Food banks, soup kitchens, and meal programs',
                'icon_class': 'fas fa-utensils',
                'color': '#10b981'
            },
            {
                'name': 'Shelter & Housing',
                'slug': 'shelter',
                'description': 'Emergency shelters and housing assistance',
                'icon_class': 'fas fa-home',
                'color': '#3b82f6'
            },
            {
                'name': 'Mental Health',
                'slug': 'mental-health',
                'description': 'Counseling, therapy, and mental health support',
                'icon_class': 'fas fa-brain',
                'color': '#8b5cf6'
            },
            {
                'name': 'Emergency Services',
                'slug': 'emergency',
                'description': 'Crisis hotlines and emergency assistance',
                'icon_class': 'fas fa-exclamation-triangle',
                'color': '#f59e0b'
            }
        ]
        
        for cat_data in categories_data:
            category, created = ServiceCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                print(f"✅ Created category: {category.name}")
        
        # Create a sample service manager user
        admin_user = User.objects.filter(is_superuser=True).first()
        if admin_user:
            # Create sample services
            healthcare_cat = ServiceCategory.objects.get(slug='healthcare')
            food_cat = ServiceCategory.objects.get(slug='food')
            
            services_data = [
                {
                    'name': 'Community Health Clinic',
                    'description': 'Free and low-cost medical services for the community. Walk-ins welcome.',
                    'category': healthcare_cat,
                    'address': '123 Main Street, Community City',
                    'phone': '(555) 123-4567',
                    'email': 'info@communityclinic.org',
                    'website': 'https://communityclinic.org',
                    'location': Point(-122.4194, 37.7749),  # San Francisco coordinates
                    'is_active': True,
                    'featured': True,
                    'created_by': admin_user
                },
                {
                    'name': 'Downtown Food Bank',
                    'description': 'Emergency food assistance for families in need. No questions asked.',
                    'category': food_cat,
                    'address': '456 Oak Avenue, Community City',
                    'phone': '(555) 987-6543',
                    'email': 'help@foodbank.org',
                    'location': Point(-122.4094, 37.7849),
                    'is_active': True,
                    'created_by': admin_user
                }
            ]
            
            for service_data in services_data:
                service, created = Service.objects.get_or_create(
                    name=service_data['name'],
                    defaults=service_data
                )
                if created:
                    print(f"✅ Created service: {service.name}")
        
        print("✅ Sample data created successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error creating sample data: {e}")
        return False

def main():
    """Main setup function."""
    print("🎯 CommuMap Setup Script")
    print("=" * 50)
    
    # Check if .env file exists
    env_file = BASE_DIR / '.env'
    if not env_file.exists():
        print("\n⚠️  No .env file found. Creating from template...")
        env_example = BASE_DIR / 'env.example'
        if env_example.exists():
            import shutil
            shutil.copy(env_example, env_file)
            print("✅ Created .env file from template")
            print("📝 Please edit .env file with your database settings")
        else:
            print("❌ No env.example file found")
            return
    
    # Check requirements
    if not check_requirements():
        return
    
    # Setup Django
    if not setup_django():
        return
    
    # Create superuser
    if not create_superuser():
        return
    
    # Create sample data
    if not create_sample_data():
        return
    
    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Visit http://localhost:8000 to see CommuMap")
    print("3. Admin panel: http://localhost:8000/admin (admin / admin123)")
    print("\nNote: Make sure PostgreSQL with PostGIS is running")

if __name__ == '__main__':
    main() 