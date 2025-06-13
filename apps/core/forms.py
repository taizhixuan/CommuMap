"""
Forms for CommuMap core functionality.

This module contains forms for user registration, authentication,
and other core features with appropriate validation and styling.
"""
from typing import Dict, Any
from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, Submit, Div, HTML
from crispy_forms.bootstrap import FormActions

from .models import User, UserRole


class CustomLoginForm(AuthenticationForm):
    """
    Custom login form with enhanced styling and validation.
    
    Uses email instead of username and provides better error handling
    and user experience with Tailwind CSS styling.
    """
    username = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'usertest@gmail.com',
            'autocomplete': 'email',
        })
    )
    
    password = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': '••••••••••',
            'autocomplete': 'current-password',
        })
    )
    
    remember_me = forms.BooleanField(
        required=False,
        label=_('Remember me'),
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox',
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        self.helper.layout = Layout(
            Field('username', css_class='form-control'),
            Field('password', css_class='form-control'),
            Field('remember_me', css_class='form-check'),
            FormActions(
                Submit('submit', _('Sign In'), css_class='btn-auth'),
            )
        )
    
    def clean(self):
        """Enhanced validation with better error messages."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Try to authenticate using email as username
            self.user_cache = authenticate(
                self.request,
                username=username,
                password=password
            )
            if self.user_cache is None:
                # Check if user exists but password is wrong
                try:
                    user = User.objects.get(email=username)
                    raise ValidationError(
                        _('Invalid password. Please try again.'),
                        code='invalid_password',
                    )
                except User.DoesNotExist:
                    raise ValidationError(
                        _('No account found with this email address.'),
                        code='invalid_email',
                    )
            else:
                self.confirm_login_allowed(self.user_cache)
        
        return cleaned_data


class UserRegistrationForm(UserCreationForm):
    """
    Enhanced user registration form with role-specific verification fields.
    
    Supports all user roles with specialized fields for Service Manager 
    and Community Moderator verification.
    """
    email = forms.EmailField(
        label=_('Email Address'),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email',
        }),
        help_text=_('We will use this email for account verification and important notifications.')
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your first name',
            'autocomplete': 'given-name',
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your last name',
            'autocomplete': 'family-name',
        })
    )
    
    phone = forms.CharField(
        label=_('Phone Number'),
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your phone number (optional)',
            'autocomplete': 'tel',
        }),
        help_text=_('Optional. May be used for account verification.')
    )
    
    # Define public signup role choices (excluding Admin)
    PUBLIC_ROLE_CHOICES = [
        (UserRole.USER, _('User')),
        (UserRole.SERVICE_MANAGER, _('Service Manager')),
        (UserRole.COMMUNITY_MODERATOR, _('Community Moderator')),
    ]
    
    role = forms.ChoiceField(
        label=_('Account Type'),
        choices=PUBLIC_ROLE_CHOICES,
        initial=UserRole.USER,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'role-select',
        }),
        help_text=_('Select your account type. Service Managers and Moderators require admin approval.')
    )
    
    # Service Manager specific fields
    service_name = forms.CharField(
        label=_('Service Name'),
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter the name of your service/organization',
        }),
        help_text=_('Required for Service Managers. The official name of your service or organization.')
    )
    
    official_email = forms.EmailField(
        label=_('Official Email'),
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your official work email',
        }),
        help_text=_('Required for Service Managers. Must be your official work email for verification.')
    )
    
    contact_number = forms.CharField(
        label=_('Official Contact Number'),
        required=False,
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter official contact number',
        }),
        help_text=_('Required for Service Managers. Official contact number for verification.')
    )
    
    # Community Moderator specific fields
    community_experience = forms.CharField(
        label=_('Community/Moderation Experience'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 4,
            'placeholder': 'Describe your relevant community management or moderation experience...',
        }),
        help_text=_('Required for Community Moderators. Describe your relevant experience in community management or content moderation.')
    )
    
    relevant_community = forms.CharField(
        label=_('Relevant Community/Organization'),
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Name of community or organization',
        }),
        help_text=_('Optional for Community Moderators. Name of community or organization you\'re associated with.')
    )
    
    # Common verification fields
    organization = forms.CharField(
        label=_('Organization'),
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your organization name',
        }),
        help_text=_('Required for Service Managers and Moderators.')
    )
    
    password1 = forms.CharField(
        label=_('Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Create a secure password',
            'autocomplete': 'new-password',
        }),
        help_text=_('Password must be at least 8 characters long.')
    )
    
    password2 = forms.CharField(
        label=_('Confirm Password'),
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Confirm your password',
            'autocomplete': 'new-password',
        })
    )
    
    terms_accepted = forms.BooleanField(
        label=_('I agree to the Terms of Service and Privacy Policy'),
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox',
        })
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'phone', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        self.helper.layout = Layout(
            Div(
                Field('first_name', css_class='form-control'),
                Field('last_name', css_class='form-control'),
                css_class='form-row'
            ),
            Field('email', css_class='form-control'),
            Field('phone', css_class='form-control'),
            Field('role', css_class='form-control'),
            
            # Service Manager fields
            HTML('<div id="service-manager-fields" class="role-specific-fields" style="display: none;">'),
            HTML('<h3 class="text-lg font-semibold text-gray-700 mb-3">Service Manager Verification</h3>'),
            Field('service_name', css_class='form-control'),
            Field('official_email', css_class='form-control'),
            Field('contact_number', css_class='form-control'),
            Field('organization', css_class='form-control'),
            HTML('</div>'),
            
            # Community Moderator fields
            HTML('<div id="community-moderator-fields" class="role-specific-fields" style="display: none;">'),
            HTML('<h3 class="text-lg font-semibold text-gray-700 mb-3">Community Moderator Verification</h3>'),
            Field('community_experience', css_class='form-control'),
            Field('relevant_community', css_class='form-control'),
            Field('organization', css_class='form-control', wrapper_class='community-org-field'),
            HTML('</div>'),
            
            Div(
                Field('password1', css_class='form-control'),
                Field('password2', css_class='form-control'),
                css_class='form-row'
            ),
            Field('terms_accepted', css_class='form-check'),
            FormActions(
                Submit('submit', _('Create Account'), css_class='btn-auth'),
            )
        )
    
    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('An account with this email address already exists.'))
        return email
    
    def clean_official_email(self):
        """Validate official email for service managers."""
        official_email = self.cleaned_data.get('official_email')
        role = self.cleaned_data.get('role')
        
        if role == UserRole.SERVICE_MANAGER and official_email:
            # Check if official email is different from personal email
            personal_email = self.cleaned_data.get('email')
            if official_email == personal_email:
                raise ValidationError(_('Official email should be different from your personal email.'))
        
        return official_email
    
    def clean_phone(self):
        """Validate phone number format."""
        phone = self.cleaned_data.get('phone')
        if phone:
            # Remove non-digit characters for validation
            digits_only = ''.join(filter(str.isdigit, phone))
            if len(digits_only) < 10:
                raise ValidationError(_('Please enter a valid phone number.'))
        return phone
    
    def clean(self):
        """Additional validation for role-specific requirements."""
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        
        # Ensure only public roles are allowed during signup
        if role == UserRole.ADMIN:
            raise ValidationError(_('Admin accounts cannot be created through public signup.'))
        
        # Service Manager validation
        if role == UserRole.SERVICE_MANAGER:
            required_fields = ['service_name', 'official_email', 'contact_number', 'organization']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, _('This field is required for Service Managers.'))
        
        # Community Moderator validation
        elif role == UserRole.COMMUNITY_MODERATOR:
            if not cleaned_data.get('community_experience'):
                self.add_error('community_experience', _('Community experience is required for Community Moderators.'))
            if not cleaned_data.get('organization'):
                self.add_error('organization', _('Organization is required for Community Moderators.'))
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save user with additional fields including verification data."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.phone = self.cleaned_data.get('phone', '')
        user.role = self.cleaned_data['role']
        
        # Save role-specific verification fields
        if user.role == UserRole.SERVICE_MANAGER:
            user.service_name = self.cleaned_data.get('service_name', '')
            user.official_email = self.cleaned_data.get('official_email', '')
            user.contact_number = self.cleaned_data.get('contact_number', '')
            user.organization = self.cleaned_data.get('organization', '')
        elif user.role == UserRole.COMMUNITY_MODERATOR:
            user.community_experience = self.cleaned_data.get('community_experience', '')
            user.relevant_community = self.cleaned_data.get('relevant_community', '')
            user.organization = self.cleaned_data.get('organization', '')
        
        if commit:
            user.save()
        return user


class AdminUserCreationForm(UserCreationForm):
    """
    Admin-only form for creating user accounts including admin accounts.
    
    This form can only be used by existing admin users to create accounts
    of any role type, including other admin accounts.
    """
    email = forms.EmailField(
        label=_('Email Address'),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter email address',
        })
    )
    
    first_name = forms.CharField(
        label=_('First Name'),
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter first name',
        })
    )
    
    last_name = forms.CharField(
        label=_('Last Name'),
        required=True,
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter last name',
        })
    )
    
    role = forms.ChoiceField(
        label=_('Account Type'),
        choices=UserRole.choices,  # All roles including Admin
        initial=UserRole.USER,
        widget=forms.Select(attrs={
            'class': 'form-select',
        }),
        help_text=_('Select the account type for this user.')
    )
    
    is_verified = forms.BooleanField(
        label=_('Account Verified'),
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox',
        }),
        help_text=_('Check to automatically verify this account.')
    )
    
    verification_notes = forms.CharField(
        label=_('Verification Notes'),
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-input',
            'rows': 3,
            'placeholder': 'Add any notes about this account creation...',
        }),
        help_text=_('Optional notes about account creation or verification.')
    )
    
    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'role')
    
    def __init__(self, *args, **kwargs):
        self.created_by = kwargs.pop('created_by', None)
        super().__init__(*args, **kwargs)
        
        # Only admin users can use this form
        if self.created_by and not self.created_by.is_admin_user:
            raise ValidationError(_('Only admin users can create accounts using this form.'))
    
    def clean_email(self):
        """Validate email uniqueness."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError(_('An account with this email address already exists.'))
        return email
    
    def save(self, commit=True):
        """Save user with admin-specified settings."""
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.role = self.cleaned_data['role']
        
        # Set verification status and notes
        user.is_verified = self.cleaned_data.get('is_verified', True)
        user.verification_notes = self.cleaned_data.get('verification_notes', '')
        if self.created_by:
            user.verified_by = self.created_by
        
        if commit:
            user.save()
        return user


class ProfileUpdateForm(forms.ModelForm):
    """
    Form for updating user profile information.
    
    Allows users to update their personal information and preferences
    while maintaining appropriate field restrictions based on role.
    """
    avatar = forms.ImageField(
        label=_('Profile Picture'),
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input file-input-bordered w-full',
            'accept': 'image/*',
        }),
        help_text=_('Upload a profile picture (optional). Maximum file size: 2MB.')
    )
    
    search_radius_km = forms.IntegerField(
        label=_('Default Search Radius (km)'),
        min_value=1,
        max_value=100,
        initial=10,
        widget=forms.NumberInput(attrs={
            'class': 'input input-bordered w-full',
            'min': '1',
            'max': '100',
        }),
        help_text=_('Default radius for service searches.')
    )
    
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'full_name', 'phone', 'avatar', 'search_radius_km']
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'autocomplete': 'family-name',
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'autocomplete': 'tel',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_enctype = 'multipart/form-data'
        self.helper.form_class = 'space-y-4'
        
        self.helper.layout = Layout(
            Div(
                Field('first_name', css_class='form-control'),
                Field('last_name', css_class='form-control'),
                css_class='grid grid-cols-2 gap-4'
            ),
            Field('full_name', css_class='form-control'),
            Field('phone', css_class='form-control'),
            Field('avatar', css_class='form-control'),
            Field('search_radius_km', css_class='form-control'),
            FormActions(
                Submit('submit', _('Update Profile'), css_class='btn btn-primary'),
            )
        )
    
    def clean_avatar(self):
        """Validate avatar file size and type."""
        avatar = self.cleaned_data.get('avatar')
        if avatar:
            # Check file size (2MB limit)
            if avatar.size > 2 * 1024 * 1024:
                raise ValidationError(_('Profile picture must be smaller than 2MB.'))
            
            # Check file type
            if not avatar.content_type.startswith('image/'):
                raise ValidationError(_('File must be an image.'))
        
        return avatar


class ContactForm(forms.Form):
    """
    Contact form for user inquiries and support requests.
    
    Provides a way for users to contact the CommuMap team
    with questions, feedback, or support needs.
    """
    SUBJECT_CHOICES = [
        ('general', _('General Inquiry')),
        ('support', _('Technical Support')),
        ('service', _('Service Information')),
        ('partnership', _('Partnership Opportunity')),
        ('feedback', _('Feedback & Suggestions')),
        ('bug', _('Report a Bug')),
        ('other', _('Other')),
    ]
    
    name = forms.CharField(
        label=_('Your Name'),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter your full name',
        })
    )
    
    email = forms.EmailField(
        label=_('Email Address'),
        widget=forms.EmailInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter your email address',
        })
    )
    
    subject = forms.ChoiceField(
        label=_('Subject'),
        choices=SUBJECT_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full',
        })
    )
    
    message = forms.CharField(
        label=_('Message'),
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 6,
            'placeholder': 'Enter your message...',
        }),
        help_text=_('Please provide as much detail as possible.')
    )
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill fields for authenticated users
        if user and user.is_authenticated:
            self.fields['name'].initial = user.get_display_name()
            self.fields['email'].initial = user.email
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        self.helper.layout = Layout(
            Div(
                Field('name', css_class='form-control'),
                Field('email', css_class='form-control'),
                css_class='grid grid-cols-2 gap-4'
            ),
            Field('subject', css_class='form-control'),
            Field('message', css_class='form-control'),
            FormActions(
                Submit('submit', _('Send Message'), css_class='btn btn-primary'),
            )
        )


class PreferenceForm(forms.ModelForm):
    """
    Form for updating user preferences and settings.
    
    Allows users to customize their CommuMap experience
    with notification preferences and display options.
    """
    email_notifications = forms.BooleanField(
        label=_('Receive email notifications'),
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary',
        }),
        help_text=_('Receive notifications about nearby service updates and alerts.')
    )
    
    class Meta:
        model = User
        fields = ['search_radius_km']
        widgets = {
            'search_radius_km': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'max': '100',
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'space-y-4'
        
        self.helper.layout = Layout(
            Field('search_radius_km', css_class='form-control'),
            Field('email_notifications', css_class='form-check'),
            FormActions(
                Submit('submit', _('Save Preferences'), css_class='btn btn-primary'),
            )
        ) 