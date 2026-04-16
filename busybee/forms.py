from django import forms
from django.forms import ModelForm, ModelChoiceField
from .models import User
from .models import *
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm


class UserSignupForm(UserCreationForm):
    is_work_user = forms.BooleanField(
        required=False,  # Optional field
        label="Are you using this application for work?",
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'is_work_user']

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data.get('email')  # Explicitly save email
        user.is_work_user = self.cleaned_data.get('is_work_user', False)  # Save is_work_user checkbox
        
        if commit:
            user.save()  # ensure user is saved before redirecting
        return user
    
class UserLoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super(UserLoginForm, self).__init__(*args, **kwargs)
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder':'Your username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder':'Your password'}))


# user can input the event details
class EventForm(forms.ModelForm):
    EVENT_TYPE_CHOICES = [
        ('timed', 'Timed Event'),
        ('all_day', 'All-Day Event'),
    ]

    # extra field to choose event type
    event_type = forms.ChoiceField(
        choices=EVENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        initial='timed'
    )
    
    # title and location
    title = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=True
    )
    location = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control'}),
        required=False
    )

    # checkbox for if private
    is_private = forms.BooleanField(required=False, label="Make this event private")

    # timed event fields (date and time)
    timed_start = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    timed_end = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
        required=False
    )
    
    # all-day event fields (date-only)
    all_day_start = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    all_day_end = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )

    # repeat fields
    REPEAT_CHOICES = [
        ('none', 'Never'),
        ('daily', 'Every Day'),
        ('weekly', 'Every Week'),
        ('monthly', 'Every Month'),
        ('yearly', 'Every Year')
    ]
    repeat_frequency = forms.ChoiceField(
        choices=REPEAT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        initial='none',
        required=False
    )
    # date field for the repeat end date
    repeat_end_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        required=False
    )
    
    # invited friends
    invited_friends = forms.ModelMultipleChoiceField(
        queryset=User.objects.none(),  # This will be dynamically set in the view
        widget=forms.CheckboxSelectMultiple,
        required=False
    )

    class Meta:
        model = Event
        fields = ['title', 'location', 'is_private', 'event_type', 
                  'timed_start', 'timed_end', 'all_day_start', 'all_day_end', 
                  'repeat_frequency', 'repeat_end_date', 'invited_friends']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)  # Get the current user from the view
        super().__init__(*args, **kwargs)
        if user:
            # Set the queryset to only show the friends of the current user
            self.fields['invited_friends'].queryset = user.friends.all()

    # makes sure user cant make any improper events
    def clean(self):
        cleaned_data = super().clean()
        is_public = cleaned_data.get('is_public', False)
        event_type = cleaned_data.get("event_type")
        repeat_frequency = cleaned_data.get("repeat_frequency")
        repeat_end_date = cleaned_data.get("repeat_end_date")
        
        if event_type == 'timed':
            start = cleaned_data.get("timed_start")
            end = cleaned_data.get("timed_end")
            if not start or not end:
                raise forms.ValidationError("Timed events require a start and end time.")
            if end <= start:
                self.add_error('timed_end', "End time must be after start time.")
            if repeat_frequency != 'none' and repeat_end_date:
                if repeat_end_date < start.date():
                    self.add_error('repeat_end_date', "Repeat end date must be on or after the start date.")
        elif event_type == 'all_day':
            start = cleaned_data.get("all_day_start")
            end = cleaned_data.get("all_day_end")
            if not start or not end:
                raise forms.ValidationError("All-day events require a start and end date.")
            if end < start:
                self.add_error('all_day_end', "End date must be on or after the start date.")
            if repeat_frequency != 'none' and repeat_end_date:
                if repeat_end_date < start:
                    self.add_error('repeat_end_date', "Repeat end date must be on or after the start date.")
        else:
            raise forms.ValidationError("Please choose a valid event type.")
        
        if is_public and not cleaned_data.get('category'):
            self.add_error('category', 'Required for public events.')
        if is_public and not cleaned_data.get('description'):
            self.add_error('description', 'Required for public events.')
        
        return cleaned_data


class WorkEventForm(forms.ModelForm):
    is_discoverable = forms.BooleanField(
        required=True,
        label="Make this event visible on the discovery page",
        error_messages={'required': 'You must check this box to publish the event.'}
    )
    
    EVENT_TYPE_CHOICES = [
        ('timed', 'Timed'),
        ('all_day', 'All Day'),
    ]

    is_public = forms.BooleanField(
        required=False,
        label="Make this event public",
        initial=True
    )

    price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'}),
        help_text="Leave blank for free events"
    )
    
    currency = forms.ChoiceField(
        choices=[('EUR', '€'), ('USD', '$'), ('GBP', '£')],
        initial='EUR',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    ticket_url = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={'class': 'form-control'}),
        label="Ticket Purchase URL"
    )

    event_type = forms.ChoiceField(
        choices=EVENT_TYPE_CHOICES,
        widget=forms.RadioSelect,
        required=True
    )

    class Meta:
        model = WorkEvent
        fields = ['title', 'location', 'category', 'description','event_type', 'price', 'currency', 
                  'event_type', 'timed_start', 'timed_end', 'all_day_start', 'all_day_end',
                  'repeat_frequency', 'repeat_end_date','is_discoverable', 'image']

        widgets = {
            'timed_start': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'timed_end': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'form-control'}),
            'all_day_start': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'all_day_end': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'repeat_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control'}),
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'location': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        event_type = cleaned_data.get("event_type")

        if event_type == 'timed':
            if not cleaned_data.get("timed_start") or not cleaned_data.get("timed_end"):
                raise forms.ValidationError("Timed events require both start and end time.")
        elif event_type == 'all_day':
            if not cleaned_data.get("all_day_start") or not cleaned_data.get("all_day_end"):
                raise forms.ValidationError("All-day events require both start and end date.")
        if not cleaned_data.get('is_discoverable'):
            self.add_error('is_discoverable', 'This field is required.')
        return cleaned_data

class EditProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'bio', 'date_of_birth',
            'phone_number', 'profile_picture',
            'company_name', 'industry', 'event_focus',
            'is_discoverable', 'work_description'
        ]
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.is_work_user:
            self.fields['company_name'].widget = forms.HiddenInput()
            self.fields['industry'].widget = forms.HiddenInput()
            self.fields['event_focus'].widget = forms.HiddenInput()
            self.fields['is_discoverable'].widget = forms.HiddenInput()
            self.fields['work_description'].widget = forms.HiddenInput()

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['receiver', 'content']

class GroupCreateForm(forms.ModelForm):
    members = forms.ModelMultipleChoiceField(
    queryset=User.objects.all(),
    widget=forms.CheckboxSelectMultiple,
    required=True,
    label="Select Friends"
    )

    class Meta:
        model = Group
        fields = ['name', 'members']