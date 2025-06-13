#!/usr/bin/env python
"""
Script to create an admin user for CommuMap Admin Console access.
"""
import os
import sys
import django
from getpass import getpass

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'commumap.settings.development')
django.setup()

from apps.core.models import User, UserRole

def main():
    print("=== CommuMap Admin Account Manager ===\n")
    
    # Check existing users
    print("Checking existing users...")
    users = User.objects.all()
    
    if users.exists():
        print(f"\nFound {users.count()} existing users:")
        for user in users:
            print(f"  • Email: {user.email}")
            print(f"    Role: {user.get_role_display()}")
            print(f"    Active: {user.is_active}")
            print(f"    Verified: {user.is_verified}")
            print(f"    Superuser: {user.is_superuser}")
            print()
    else:
        print("No existing users found.\n")
    
    # Check for existing admin users
    admin_users = User.objects.filter(role=UserRole.ADMIN, is_verified=True)
    if admin_users.exists():
        print("✅ Existing verified admin users found:")
        for admin in admin_users:
            print(f"  • {admin.email}")
        
        print("\n🔐 You can login to the admin console at /console/dashboard/ with any of these accounts.")
        return
    
    # Create new admin user
    print("❌ No verified admin users found. Let's create one!\n")
    
    try:
        # Get admin details
        email = input("Enter admin email: ").strip()
        if not email:
            print("Email is required!")
            return
        
        # Check if user already exists
        if User.objects.filter(email=email).exists():
            existing_user = User.objects.get(email=email)
            print(f"\nUser with email {email} already exists.")
            
            if existing_user.role != UserRole.ADMIN:
                confirm = input(f"Upgrade {email} to admin role? (y/N): ").strip().lower()
                if confirm == 'y':
                    existing_user.role = UserRole.ADMIN
                    existing_user.is_verified = True
                    existing_user.is_active = True
                    existing_user.save()
                    print(f"✅ User {email} upgraded to verified admin!")
                    print(f"🔐 Login at /console/dashboard/ with your existing password.")
                    return
                else:
                    print("Admin creation cancelled.")
                    return
            else:
                if not existing_user.is_verified:
                    existing_user.is_verified = True
                    existing_user.save()
                    print(f"✅ Admin user {email} verified!")
                print(f"🔐 Login at /console/dashboard/ with your existing password.")
                return
        
        # Get other details for new user
        first_name = input("Enter first name: ").strip()
        last_name = input("Enter last name: ").strip()
        password = getpass("Enter password: ")
        
        if not password:
            print("Password is required!")
            return
        
        # Create admin user
        admin_user = User.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.ADMIN,
            is_verified=True,
            is_active=True
        )
        
        print(f"\n✅ Admin user created successfully!")
        print(f"📧 Email: {admin_user.email}")
        print(f"👤 Name: {admin_user.get_display_name()}")
        print(f"🛡️  Role: {admin_user.get_role_display()}")
        print(f"✅ Verified: {admin_user.is_verified}")
        
        print(f"\n🔐 Login Details:")
        print(f"   URL: http://localhost:8000/console/dashboard/")
        print(f"   Email: {email}")
        print(f"   Password: [the password you entered]")
        
        print(f"\n🚀 The admin console is now ready for use!")
        
    except KeyboardInterrupt:
        print("\n\nAdmin creation cancelled.")
    except Exception as e:
        print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    main() 