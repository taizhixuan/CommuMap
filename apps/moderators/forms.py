"""
Forms for Community Moderator functionality.
"""
from django import forms
from django.forms import ModelForm
from django.utils.translation import gettext_lazy as _

from apps.core.models import User
from apps.services.models import Service, ServiceCategory
from .models import OutreachPost


class OutreachPostForm(ModelForm):
    """
    Form for creating and editing outreach posts.
    """
    
    class Meta:
        model = OutreachPost
        fields = [
            'title', 'content', 'banner_image_url', 'target_categories', 
            'is_active', 'expires_at'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter post title...'
            }),
            'content': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-32',
                'placeholder': 'Write your outreach content...'
            }),
            'banner_image_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter banner image URL...'
            }),
            'target_categories': forms.CheckboxSelectMultiple(attrs={
                'class': 'checkbox'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'toggle toggle-success'
            }),
            'expires_at': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
        }
        labels = {
            'title': _('Post Title'),
            'content': _('Content'),
            'banner_image_url': _('Banner Image URL'),
            'target_categories': _('Target Categories'),
            'is_active': _('Active'),
            'expires_at': _('Expiry Date (Optional)'),
        }
        help_texts = {
            'target_categories': _('Select categories to target with this post'),
            'expires_at': _('Leave empty for no expiry'),
        }


class ServiceModeratorEditForm(ModelForm):
    """
    Form for moderators to make light edits to services.
    """
    
    class Meta:
        model = Service
        fields = [
            'name', 'description', 'phone', 'email',
            'hours_of_operation', 'website', 'eligibility_criteria'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-32'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'hours_of_operation': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-24'
            }),
            'website': forms.URLInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'eligibility_criteria': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full h-24'
            }),
        }


class CommentModerationForm(forms.Form):
    """
    Form for moderator replies to comments.
    """
    content = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full h-24',
            'placeholder': 'Write your moderator reply...'
        }),
        label=_('Reply'),
        min_length=10,
        max_length=1000
    )
    
    is_official = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        label=_('Mark as Official Moderator Response'),
        required=False,
        initial=True
    )


class BulkActionForm(forms.Form):
    """
    Form for bulk moderation actions.
    """
    ACTION_CHOICES = [
        ('approve', _('Approve Selected')),
        ('reject', _('Reject Selected')),
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered'
        }),
        label=_('Action')
    )
    
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full h-20',
            'placeholder': 'Enter reason for bulk action...'
        }),
        label=_('Reason'),
        required=False,
        max_length=500
    )
    
    selected_items = forms.CharField(
        widget=forms.HiddenInput(),
        required=True
    )


class ServiceFilterForm(forms.Form):
    """
    Form for filtering services in the approval queue.
    """
    search = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Search services...'
        }),
        label=_('Search'),
        required=False
    )
    
    category = forms.ModelChoiceField(
        queryset=ServiceCategory.objects.all(),
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label=_('Category'),
        required=False,
        empty_label=_('All Categories')
    )
    
    date_from = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'date'
        }),
        label=_('From Date'),
        required=False
    )
    
    date_to = forms.DateField(
        widget=forms.DateInput(attrs={
            'class': 'input input-bordered w-full',
            'type': 'date'
        }),
        label=_('To Date'),
        required=False
    )


class FlagResolutionForm(forms.Form):
    """
    Form for resolving flagged content.
    """
    RESOLUTION_CHOICES = [
        ('valid', _('Flag Valid - Content Removed')),
        ('invalid', _('Flag Invalid - Content Kept')),
        ('warning', _('Warning Issued - Content Kept')),
        ('edited', _('Content Edited - Flag Resolved')),
    ]
    
    resolution_type = forms.ChoiceField(
        choices=RESOLUTION_CHOICES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label=_('Resolution Type')
    )
    
    resolution_notes = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full h-24',
            'placeholder': 'Enter resolution notes...'
        }),
        label=_('Resolution Notes'),
        required=True,
        min_length=10,
        max_length=500
    )


class ModeratorProfileForm(forms.ModelForm):
    """
    Form for moderator profile updates.
    """
    class Meta:
        model = User
        fields = ['full_name', 'phone', 'community_experience', 'relevant_community', 'organization']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
            'community_experience': forms.Textarea(attrs={'class': 'form-input form-textarea'}),
            'relevant_community': forms.TextInput(attrs={'class': 'form-input'}),
            'organization': forms.TextInput(attrs={'class': 'form-input'}),
        }
    
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
            user.save(update_fields=['full_name', 'phone', 'community_experience', 'relevant_community', 'organization'])
        
        return user 