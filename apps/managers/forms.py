"""
Forms for the managers app.
"""
from django import forms
from django.core.exceptions import ValidationError
from apps.services.models import Service, ServiceCategory
from apps.core.models import User


class ServiceForm(forms.ModelForm):
    """
    Custom form for service creation with enhanced validation.
    """
    
    class Meta:
        model = Service
        fields = [
            'name', 'description', 'short_description', 'category',
            'address', 'latitude', 'longitude', 'city', 'state_province',
            'phone', 'email', 'website', 'max_capacity',
            'is_emergency_service', 'requires_appointment', 'accepts_walk_ins',
            'is_free', 'cost_info', 'eligibility_criteria'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter service name'
            }),
            'short_description': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Brief description for listings'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-24',
                'placeholder': 'Detailed service description'
            }),
            'category': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'address': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Full street address'
            }),
            'city': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'City name',
                'value': 'Cyberjaya'
            }),
            'state_province': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'State or Province',
                'value': 'Selangor'
            }),
            'latitude': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': 'any',
                'readonly': True
            }),
            'longitude': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': 'any',
                'readonly': True
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '(555) 123-4567'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'contact@service.org'
            }),
            'website': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://www.service.org'
            }),
            'max_capacity': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1'
            }),
            'cost_info': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-20',
                'placeholder': 'Pricing and payment information'
            }),
            'eligibility_criteria': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-20',
                'placeholder': 'Who is eligible for this service'
            }),
            'is_emergency_service': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'requires_appointment': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'accepts_walk_ins': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'is_free': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Make certain fields required
        self.fields['name'].required = True
        self.fields['description'].required = True
        self.fields['short_description'].required = True
        self.fields['category'].required = True
        self.fields['address'].required = True
        self.fields['city'].required = True
        self.fields['state_province'].required = True
        
        # Make location fields optional for now to avoid validation issues
        self.fields['latitude'].required = False
        self.fields['longitude'].required = False
        
        # Set up category choices
        self.fields['category'].queryset = ServiceCategory.objects.filter(is_active=True)
        
    def clean_latitude(self):
        latitude = self.cleaned_data.get('latitude')
        if latitude is not None:
            if latitude < -90 or latitude > 90:
                raise ValidationError("Latitude must be between -90 and 90 degrees.")
        return latitude
    
    def clean_longitude(self):
        longitude = self.cleaned_data.get('longitude')
        if longitude is not None:
            if longitude < -180 or longitude > 180:
                raise ValidationError("Longitude must be between -180 and 180 degrees.")
        return longitude
    
    def clean_max_capacity(self):
        max_capacity = self.cleaned_data.get('max_capacity')
        if max_capacity is not None and max_capacity <= 0:
            raise ValidationError("Maximum capacity must be greater than 0.")
        return max_capacity
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Validate that if not free, cost info is provided
        is_free = cleaned_data.get('is_free')
        cost_info = cleaned_data.get('cost_info')
        
        if not is_free and not cost_info:
            raise ValidationError({
                'cost_info': 'Cost information is required for paid services.'
            })
        
        return cleaned_data


class ManagerProfileForm(forms.ModelForm):
    """
    Form for Service Manager profile management.
    """
    
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone', 'full_name'
        ]
        
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your first name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your last name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'your.email@example.com'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '(555) 123-4567'
            }),
            'full_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Your full display name'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Set email as required and readonly for verified users
        self.fields['email'].required = True
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError("Email address is required.")
        
        # Check if email is already taken by another user
        if self.instance and self.instance.pk:
            existing = User.objects.filter(email=email).exclude(pk=self.instance.pk)
            if existing.exists():
                raise ValidationError("This email address is already in use.")
        
        return email
    
    def save(self, commit=True):
        """Override save to ensure is_verified is not modified by this form."""
        user = super().save(commit=False)
        
        # Preserve the original is_verified value
        if hasattr(self.instance, 'is_verified') and self.instance.pk:
            # Get the original value from the database
            original_user = User.objects.get(pk=self.instance.pk)
            user.is_verified = original_user.is_verified
            
            # Ensure it's a proper boolean value, not a function
            if not isinstance(user.is_verified, bool):
                # If somehow it's not a boolean, get the value from the database field
                user.is_verified = bool(original_user.is_verified)
        
        if commit:
            # Only save the fields that this form is supposed to handle
            user.save(update_fields=['first_name', 'last_name', 'email', 'phone', 'full_name'])
        
        return user 