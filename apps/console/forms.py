"""
Forms for CommuMap Admin Console.

Provides form classes for user management, system announcements,
maintenance tasks, and admin profile management.
"""
from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from apps.core.models import User, UserRole, SystemSettings
from apps.services.models import Service, ServiceStatus, ServiceCategory
from .models import SystemAnnouncement, MaintenanceTask


class AdminUserCreationForm(UserCreationForm):
    """
    Enhanced user creation form for admin use.
    
    Allows admins to create users with any role and provides
    additional fields for role-specific information.
    """
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    first_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    last_name = forms.CharField(
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    full_name = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Full display name (optional, auto-generated from first/last name if empty)"
    )
    phone = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    role = forms.ChoiceField(
        choices=UserRole.choices,
        required=True,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    is_active = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Account is active and can log in"
    )
    is_verified = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Check to automatically verify this user account."
    )
    send_notification = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Send welcome email to the new user."
    )
    
    # Service Manager specific fields
    service_name = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Name of the service (for Service Managers only)."
    )
    official_email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-control'}),
        help_text="Official work email (for Service Managers only)."
    )
    contact_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Official contact number (for Service Managers only)."
    )
    organization = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Organization name (for Service Managers and Moderators)."
    )
    
    # Community Moderator specific fields
    community_experience = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
        required=False,
        help_text="Community management experience (for Moderators only)."
    )
    relevant_community = forms.CharField(
        max_length=200,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        help_text="Relevant community (for Moderators only)."
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'full_name', 'phone', 'role', 
            'is_active', 'is_verified', 'service_name', 'official_email', 
            'contact_number', 'organization', 'community_experience', 'relevant_community'
        ]
    
    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop('created_by', None)
        super().__init__(*args, **kwargs)
        # Username is automatically set from email, no separate field needed
        
        # Style the password fields that are inherited from UserCreationForm
        if 'password1' in self.fields:
            self.fields['password1'].widget.attrs.update({'class': 'form-control'})
        if 'password2' in self.fields:
            self.fields['password2'].widget.attrs.update({'class': 'form-control'})
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        
        # Validate role-specific required fields
        if role == UserRole.SERVICE_MANAGER:
            if not cleaned_data.get('service_name'):
                self.add_error('service_name', 'Service name is required for Service Managers.')
            if not cleaned_data.get('official_email'):
                self.add_error('official_email', 'Official email is required for Service Managers.')
        
        elif role == UserRole.COMMUNITY_MODERATOR:
            if not cleaned_data.get('community_experience'):
                self.add_error('community_experience', 'Community experience is required for Moderators.')
        
        return cleaned_data
    
    def save(self, commit=True):
        # Let Django's UserCreationForm handle password creation first
        user = super().save(commit=False)
        
        # Set additional fields
        user.email = self.cleaned_data['email']
        user.username = self.cleaned_data['email']  # Use email as username
        user.role = self.cleaned_data['role']
        user.is_active = self.cleaned_data.get('is_active', True)
        user.is_verified = self.cleaned_data.get('is_verified', True)
        
        # Set full_name if provided, otherwise auto-generate
        full_name = self.cleaned_data.get('full_name', '').strip()
        if not full_name:
            first_name = self.cleaned_data.get('first_name', '').strip()
            last_name = self.cleaned_data.get('last_name', '').strip()
            if first_name and last_name:
                full_name = f"{first_name} {last_name}"
        user.full_name = full_name
        
        user.phone = self.cleaned_data.get('phone', '')
        
        # Set role-specific fields
        user.service_name = self.cleaned_data.get('service_name', '')
        user.official_email = self.cleaned_data.get('official_email', '')
        user.contact_number = self.cleaned_data.get('contact_number', '')
        user.organization = self.cleaned_data.get('organization', '')
        user.community_experience = self.cleaned_data.get('community_experience', '')
        user.relevant_community = self.cleaned_data.get('relevant_community', '')
        
        # Set verified_by if admin is creating a verified account
        if user.is_verified and self.created_by:
            user.verified_by = self.created_by
        
        if commit:
            user.save()
        
        return user


class AdminUserEditForm(forms.ModelForm):
    """
    Form for editing existing user accounts by admins.
    
    Provides comprehensive user editing capabilities with role-specific fields.
    """
    
    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'last_name', 'full_name', 'phone', 'role', 
            'is_active', 'is_verified', 'service_name', 'official_email', 
            'contact_number', 'organization', 'community_experience', 'relevant_community'
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'full_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'official_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'contact_number': forms.TextInput(attrs={'class': 'form-control'}),
            'organization': forms.TextInput(attrs={'class': 'form-control'}),
            'community_experience': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'relevant_community': forms.TextInput(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make role-specific fields conditional
        if self.instance and self.instance.pk:
            if self.instance.role not in [UserRole.SERVICE_MANAGER, UserRole.COMMUNITY_MODERATOR]:
                # Hide role-specific fields for regular users and admins
                role_specific_fields = [
                    'service_name', 'official_email', 'contact_number', 'organization',
                    'community_experience', 'relevant_community'
                ]
                for field in role_specific_fields:
                    if field in self.fields:
                        self.fields[field].widget = forms.HiddenInput()
    
    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Auto-generate full_name if not provided
        if not user.full_name:
            if user.first_name and user.last_name:
                user.full_name = f"{user.first_name} {user.last_name}"
        
        if commit:
            user.save()
        
        return user


class AdminProfileForm(forms.ModelForm):
    """
    Form for admin profile management.
    
    Allows admins to update their own profile information.
    """
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'phone', 'email']
        widgets = {
            'email': forms.EmailInput(attrs={'readonly': True}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Make email readonly
        self.fields['email'].widget.attrs['readonly'] = True
        self.fields['email'].help_text = "Email cannot be changed. Contact system administrator if needed."


class SystemAnnouncementForm(forms.ModelForm):
    """
    Form for creating and editing system announcements.
    
    Provides rich text editing and targeting options for announcements.
    """
    target_roles = forms.MultipleChoiceField(
        choices=UserRole.choices,
        widget=forms.CheckboxSelectMultiple,
        required=False,
        help_text="Select user roles to target. Leave empty to target all users."
    )
    
    class Meta:
        model = SystemAnnouncement
        fields = [
            'title', 'content', 'announcement_type', 'target_roles',
            'is_active', 'is_urgent', 'show_from', 'show_until'
        ]
        widgets = {
            'content': forms.Textarea(attrs={'rows': 6}),
            'show_from': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'show_until': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            if field_name not in ['target_roles']:  # Skip checkbox fields
                field.widget.attrs.update({'class': 'form-control'})
        
        # Set help text
        self.fields['show_until'].help_text = "Leave empty for permanent announcement."
        self.fields['is_urgent'].help_text = "Urgent announcements are displayed prominently."
    
    def clean(self):
        cleaned_data = super().clean()
        show_from = cleaned_data.get('show_from')
        show_until = cleaned_data.get('show_until')
        
        if show_from and show_until and show_from >= show_until:
            self.add_error('show_until', 'End time must be after start time.')
        
        return cleaned_data


class MaintenanceTaskForm(forms.ModelForm):
    """
    Form for creating maintenance tasks.
    
    Provides options for different types of maintenance operations.
    """
    
    class Meta:
        model = MaintenanceTask
        fields = ['task_type', 'title', 'description', 'parameters']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
            'parameters': forms.Textarea(attrs={'rows': 4}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'form-control'})
        
        # Set help text
        self.fields['parameters'].help_text = "JSON parameters for the task (e.g., {'backup_name': 'manual_backup'})"
        self.fields['parameters'].required = False
    
    def clean_parameters(self):
        parameters = self.cleaned_data.get('parameters', '{}')
        if not parameters:
            return {}
        
        try:
            import json
            return json.loads(parameters)
        except json.JSONDecodeError:
            raise ValidationError("Parameters must be valid JSON.")


class BulkUserActionForm(forms.Form):
    """
    Form for bulk user actions in the admin interface.
    
    Allows admins to perform actions on multiple users at once.
    """
    ACTION_CHOICES = [
        ('verify', 'Verify Users'),
        ('unverify', 'Remove Verification'),
        ('activate', 'Activate Users'),
        ('deactivate', 'Deactivate Users'),
        ('delete', 'Delete Users'),
        ('change_role', 'Change Role'),
    ]
    
    action = forms.ChoiceField(choices=ACTION_CHOICES, widget=forms.Select(attrs={'class': 'form-control'}))
    user_ids = forms.CharField(widget=forms.HiddenInput())
    new_role = forms.ChoiceField(
        choices=UserRole.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Required when changing user roles."
    )
    confirm = forms.BooleanField(
        required=True,
        help_text="Confirm that you want to perform this bulk action."
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        new_role = cleaned_data.get('new_role')
        
        if action == 'change_role' and not new_role:
            self.add_error('new_role', 'New role is required when changing user roles.')
        
        return cleaned_data


class SystemSettingsForm(forms.ModelForm):
    """
    Form for system settings management.
    
    Provides interface for configuring system-wide settings.
    """
    
    class Meta:
        model = SystemSettings
        fields = [
            'maintenance_mode', 'system_announcement', 'announcement_active',
            'registration_enabled', 'service_submissions_enabled', 'emergency_mode',
            'default_map_center_lat', 'default_map_center_lng', 'default_map_zoom',
            'emergency_search_radius_km', 'auto_approve_services', 'auto_approve_comments'
        ]
        widgets = {
            'system_announcement': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'default_map_center_lat': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control'}),
            'default_map_center_lng': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control'}),
            'default_map_zoom': forms.NumberInput(attrs={'class': 'form-control'}),
            'emergency_search_radius_km': forms.NumberInput(attrs={'step': 'any', 'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Add CSS classes to all fields
        for field_name, field in self.fields.items():
            if field_name not in ['system_announcement', 'default_map_center_lat', 
                                'default_map_center_lng', 'default_map_zoom', 'emergency_search_radius_km']:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Add help text
        self.fields['maintenance_mode'].help_text = "Enable maintenance mode to restrict access"
        self.fields['emergency_mode'].help_text = "Enable emergency mode to show only emergency services"
        self.fields['auto_approve_services'].help_text = "Automatically approve new service submissions"


class FeatureToggleForm(forms.Form):
    """
    Form for toggling system features.
    
    Provides interface for enabling/disabling system features at runtime.
    """
    FEATURE_CHOICES = [
        ('registration', 'User Registration'),
        ('service_submissions', 'Service Submissions'),
        ('emergency_mode', 'Emergency Mode'),
        ('auto_approve_services', 'Auto-approve Services'),
        ('auto_approve_comments', 'Auto-approve Comments'),
        ('maintenance_mode', 'Maintenance Mode'),
    ]
    
    feature = forms.ChoiceField(
        choices=FEATURE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    enabled = forms.BooleanField(
        required=False,
        help_text="Enable or disable this feature."
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load current feature states
        settings_loader = None
        try:
            from .managers import SettingsLoader
            settings_loader = SettingsLoader()
        except:
            pass
        
        if settings_loader:
            feature_flags = settings_loader.get_all_feature_flags()
            self.fields['enabled'].help_text += f" Current states: {feature_flags}"


class AdminServiceForm(forms.ModelForm):
    """
    Comprehensive service management form for admin users.
    
    Provides full control over all service content and metadata.
    """
    
    # Additional fields for better content management
    hours_monday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_tuesday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_wednesday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_thursday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_friday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_saturday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    hours_sunday = forms.CharField(max_length=50, required=False, help_text="e.g., 9:00 AM - 5:00 PM")
    
    tags_input = forms.CharField(
        required=False,
        help_text="Enter tags separated by commas (e.g., healthcare, emergency, 24/7)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'healthcare, emergency, 24/7'
        })
    )
    
    class Meta:
        model = Service
        fields = [
            'name', 'slug', 'description', 'short_description', 'category',
            'latitude', 'longitude', 'address', 'postal_code', 'city', 
            'state_province', 'country', 'phone', 'phone_alt', 'email', 
            'website', 'is_24_7', 'seasonal_info', 'max_capacity', 
            'current_capacity', 'is_emergency_service', 'requires_appointment', 
            'accepts_walk_ins', 'is_free', 'cost_info', 'eligibility_criteria', 
            'required_documents', 'age_restrictions', 'manager', 'is_verified', 
            'current_status', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter service name',
                'required': True
            }),
            'description': forms.Textarea(attrs={
                'rows': 6, 
                'class': 'form-control',
                'placeholder': 'Provide a detailed description of the service',
                'required': True
            }),
            'short_description': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Brief summary for service listings (max 300 characters)',
                'required': True
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'required': True
            }),
            'address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter full street address',
                'required': True
            }),
            'city': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'City name',
                'value': 'Cyberjaya',
                'required': True
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'State or Province',
                'value': 'Selangor',
                'required': True
            }),
            'country': forms.TextInput(attrs={
                'class': 'form-control',
                'value': 'Malaysia'
            }),
            'postal_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Postal code'
            }),
            'latitude': forms.NumberInput(attrs={
                'step': 'any', 
                'class': 'form-control',
                'placeholder': 'Latitude coordinate',
                'required': True
            }),
            'longitude': forms.NumberInput(attrs={
                'step': 'any', 
                'class': 'form-control',
                'placeholder': 'Longitude coordinate',
                'required': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '(555) 123-4567'
            }),
            'phone_alt': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alternative phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'contact@service.org'
            }),
            'website': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.service.org'
            }),
            'seasonal_info': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Seasonal operation details'
            }),
            'cost_info': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Cost and payment information'
            }),
            'eligibility_criteria': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': 'Who is eligible for this service'
            }),
            'required_documents': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Required documentation'
            }),
            'age_restrictions': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 18+, Children only, All ages'
            }),
            'max_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'placeholder': 'Maximum capacity'
            }),
            'current_capacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'placeholder': 'Current capacity'
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control', 
                'readonly': True
            }),
            'manager': forms.Select(attrs={
                'class': 'form-control'
            }),
            'current_status': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make essential fields required
        self.fields['name'].required = True
        self.fields['description'].required = True
        self.fields['short_description'].required = True
        self.fields['category'].required = True
        self.fields['address'].required = True
        self.fields['city'].required = True
        self.fields['state_province'].required = True
        self.fields['latitude'].required = True
        self.fields['longitude'].required = True
        
        # Add CSS classes to all fields that don't have them
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                field.widget.attrs.update({'class': 'form-control'})
        
        # Pre-populate hours fields if editing existing service
        if self.instance and self.instance.pk and self.instance.hours_of_operation:
            hours = self.instance.hours_of_operation
            self.fields['hours_monday'].initial = hours.get('monday', '')
            self.fields['hours_tuesday'].initial = hours.get('tuesday', '')
            self.fields['hours_wednesday'].initial = hours.get('wednesday', '')
            self.fields['hours_thursday'].initial = hours.get('thursday', '')
            self.fields['hours_friday'].initial = hours.get('friday', '')
            self.fields['hours_saturday'].initial = hours.get('saturday', '')
            self.fields['hours_sunday'].initial = hours.get('sunday', '')
        
        # Pre-populate tags field
        if self.instance and self.instance.pk and self.instance.tags:
            self.fields['tags_input'].initial = ', '.join(self.instance.tags)
        
        # Filter manager choices to only service managers and admins
        self.fields['manager'].queryset = User.objects.filter(
            role__in=[UserRole.SERVICE_MANAGER, UserRole.ADMIN]
        ).order_by('first_name', 'last_name')
        
        # Set empty labels for better UX
        self.fields['manager'].empty_label = "Select a manager (optional)"
        self.fields['category'].empty_label = "Select a category"
        
        # Add field descriptions with better help text
        self.fields['slug'].help_text = "URL-friendly identifier (auto-generated from name)"
        self.fields['short_description'].help_text = "Brief summary for service listings (max 300 characters)"
        self.fields['latitude'].help_text = "Geographic latitude coordinate (-90 to 90)"
        self.fields['longitude'].help_text = "Geographic longitude coordinate (-180 to 180)"
        self.fields['max_capacity'].help_text = "Maximum number of people this service can accommodate"
        self.fields['current_capacity'].help_text = "Current number of people using this service"
        self.fields['is_verified'].help_text = "Service has been verified by moderators"
        self.fields['is_active'].help_text = "Service is visible to public users"
        self.fields['is_24_7'].help_text = "Check if service operates 24 hours a day, 7 days a week"
        self.fields['is_emergency_service'].help_text = "Check if this service is available during emergencies"
        self.fields['requires_appointment'].help_text = "Check if appointments are required"
        self.fields['accepts_walk_ins'].help_text = "Check if walk-in clients are accepted"
        self.fields['is_free'].help_text = "Check if service is provided free of charge"
    
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not name or len(name.strip()) < 2:
            raise forms.ValidationError('Service name must be at least 2 characters long.')
        return name.strip()
    
    def clean_short_description(self):
        short_description = self.cleaned_data.get('short_description')
        if short_description and len(short_description) > 300:
            raise forms.ValidationError('Short description cannot exceed 300 characters.')
        if not short_description or len(short_description.strip()) < 10:
            raise forms.ValidationError('Short description must be at least 10 characters long.')
        return short_description.strip()
    
    def clean_description(self):
        description = self.cleaned_data.get('description')
        if not description or len(description.strip()) < 20:
            raise forms.ValidationError('Description must be at least 20 characters long.')
        return description.strip()
    
    def clean_tags_input(self):
        tags_input = self.cleaned_data.get('tags_input', '')
        if tags_input:
            # Split by comma and clean up tags
            tags = [tag.strip().lower() for tag in tags_input.split(',') if tag.strip()]
            # Limit to 10 tags max
            if len(tags) > 10:
                raise forms.ValidationError('Maximum 10 tags allowed.')
            return tags
        return []
    
    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude is None:
            raise forms.ValidationError('Latitude is required.')
        if latitude < -90 or latitude > 90:
            raise forms.ValidationError('Latitude must be between -90 and 90 degrees.')
        return latitude
    
    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude is None:
            raise forms.ValidationError('Longitude is required.')
        if longitude < -180 or longitude > 180:
            raise forms.ValidationError('Longitude must be between -180 and 180 degrees.')
        return longitude
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate capacity
        max_capacity = cleaned_data.get('max_capacity')
        current_capacity = cleaned_data.get('current_capacity')
        
        if max_capacity and current_capacity and current_capacity > max_capacity:
            self.add_error('current_capacity', 'Current capacity cannot exceed maximum capacity.')
        
        # Validate coordinates together
        latitude = cleaned_data.get('latitude')
        longitude = cleaned_data.get('longitude')
        
        if latitude is not None and longitude is not None:
            # Basic sanity check for Malaysia coordinates
            if not (1.0 <= latitude <= 7.5 and 99.0 <= longitude <= 120.0):
                self.add_error('latitude', 'Coordinates appear to be outside Malaysia. Please verify.')
                self.add_error('longitude', 'Coordinates appear to be outside Malaysia. Please verify.')
        
        # Validate phone number format if provided
        phone = cleaned_data.get('phone')
        if phone:
            import re
            # Basic phone validation
            phone_pattern = re.compile(r'^[\d\-\+\(\)\s]+$')
            if not phone_pattern.match(phone):
                self.add_error('phone', 'Please enter a valid phone number.')
        
        # Validate email if provided
        email = cleaned_data.get('email')
        if email:
            from django.core.validators import validate_email
            try:
                validate_email(email)
            except forms.ValidationError:
                self.add_error('email', 'Please enter a valid email address.')
        
        # Validate website URL if provided
        website = cleaned_data.get('website')
        if website:
            from django.core.validators import URLValidator
            try:
                validator = URLValidator()
                validator(website)
            except forms.ValidationError:
                self.add_error('website', 'Please enter a valid website URL.')
        
        # Auto-generate slug if not provided
        name = cleaned_data.get('name')
        if name and not cleaned_data.get('slug'):
            from django.utils.text import slugify
            cleaned_data['slug'] = slugify(name)
        
        return cleaned_data
    
    def save(self, commit=True):
        service = super().save(commit=False)
        
        # Process hours of operation
        hours_data = {}
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            field_name = f'hours_{day}'
            if field_name in self.cleaned_data:
                hours_value = self.cleaned_data[field_name]
                if hours_value and hours_value.strip():
                    hours_data[day] = hours_value.strip()
        
        service.hours_of_operation = hours_data
        
        # Process tags
        tags = self.cleaned_data.get('tags_input', [])
        service.tags = tags
        
        # Auto-generate slug if not set
        if not service.slug and service.name:
            from django.utils.text import slugify
            service.slug = slugify(service.name)
        
        if commit:
            service.save()
        
        return service


class BulkServiceActionForm(forms.Form):
    """
    Form for bulk service actions in the admin interface.
    
    Allows admins to perform actions on multiple services at once.
    """
    ACTION_CHOICES = [
        ('verify', 'Verify Services'),
        ('unverify', 'Remove Verification'),
        ('activate', 'Activate Services'),
        ('deactivate', 'Deactivate Services'),
        ('delete', 'Delete Services'),
        ('emergency_on', 'Enable Emergency Status'),
        ('emergency_off', 'Disable Emergency Status'),
        ('change_status', 'Change Status'),
        ('change_category', 'Change Category'),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES, 
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    service_ids = forms.CharField(widget=forms.HiddenInput())
    new_status = forms.ChoiceField(
        choices=ServiceStatus.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Required when changing service status."
    )
    new_category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'}),
        help_text="Required when changing service category."
    )
    confirm = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Confirm that you want to perform this action on selected services."
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        # Validate required fields based on action
        if action == 'change_status' and not cleaned_data.get('new_status'):
            self.add_error('new_status', 'New status is required when changing service status.')
        
        if action == 'change_category' and not cleaned_data.get('new_category'):
            self.add_error('new_category', 'New category is required when changing service category.')
        
        return cleaned_data


class ServiceSearchForm(forms.Form):
    """
    Advanced search form for service management.
    
    Provides filtering and search capabilities for the admin service list.
    """
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search services by name, description, or manager...'
        })
    )
    status = forms.ChoiceField(
        choices=[('', 'All Statuses')] + list(ServiceStatus.choices),
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.filter(is_active=True),
        required=False,
        empty_label="All Categories",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    verification_status = forms.ChoiceField(
        choices=[('', 'All'), ('verified', 'Verified'), ('unverified', 'Unverified')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    active_status = forms.ChoiceField(
        choices=[('', 'All'), ('active', 'Active'), ('inactive', 'Inactive')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    emergency_services = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Show only emergency services"
    )
    has_manager = forms.ChoiceField(
        choices=[('', 'All'), ('yes', 'Has Manager'), ('no', 'No Manager')],
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    ) 