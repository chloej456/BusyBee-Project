from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.utils.timezone import now
import uuid

class User(AbstractUser):
    email = models.EmailField(unique=True)  # ensure email is unique
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    is_work_user = models.BooleanField(default=False, verbose_name="Using for Work")  # true if using the app for work
    friends = models.ManyToManyField("self", blank=True, symmetrical=False, related_name='friend_set')

    # fields for work users
    company_name = models.CharField(max_length=255, blank=True, null=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    event_focus = models.CharField(max_length=255, blank=True, null=True)
    is_discoverable = models.BooleanField(default=True)
    work_description = models.TextField(blank=True, null=True)
    is_work_user = models.BooleanField(default=False)
    followers = models.ManyToManyField('self', symmetrical=False, related_name='following', blank=True)

    def __str__(self):
        return self.username

class FriendRequest(models.Model):
    from_user = models.ForeignKey(User, related_name='sent_requests', on_delete=models.CASCADE)
    to_user = models.ForeignKey(User, related_name='received_requests', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)  # Used for accept/reject

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    def __str__(self):
        return f"{self.from_user} → {self.to_user}"


class Friendship(models.Model):
    user1 = models.ForeignKey(User, related_name='friendship_initiator', on_delete=models.CASCADE)
    user2 = models.ForeignKey(User, related_name='friendship_receiver', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    status = models.CharField(max_length=20, default='pending')

    class Meta:
        unique_together = ('user1', 'user2')
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(user1=models.F('user2')),
                name='prevent_self_friendship'
            )
        ]

    def __str__(self):
        return f"Friendship between {self.user1.username} and {self.user2.username}"

    def get_friend_for(self, user):
        """Returns the other user in the friendship given one."""
        return self.user2 if self.user1 == user else self.user1
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    timestamp = models.DateTimeField(auto_now_add=True)



# stores all of the event data for the user
class Event(models.Model):
    REPEAT_CHOICES = [
        ('none', 'Never'),
        ('daily', 'Every Day'),
        ('weekly', 'Every Week'),
        ('monthly', 'Every Month'),
        ('yearly', 'Every Year')
    ]

    title = models.CharField(max_length=100)
    location = models.CharField(max_length=200, blank=True, null=True)
    all_day = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    repeat_frequency = models.CharField(max_length=10, choices=REPEAT_CHOICES, default='none')
    repeat_end_date = models.DateField(blank=True, null=True)  # Allows users to set an end date for recurring events

    # owner of the event
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='events')

    # all users who are attending this event
    attendees = models.ManyToManyField(User, related_name='attending_events', blank=True)

    # if private event
    is_private = models.BooleanField(default=False)  # if true, only owner sees full details

    # parent event
    parent_event = models.ForeignKey(
        'self', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='child_events'
    )

    class Meta:
        ordering = ['start_time']

    def __str__(self):
        return f"{self.title} ({self.start_time})"




# TICKETMASTER EVENT INTEREST

class EventInterest(models.Model):
    STATUS_CHOICES = [
        ('interested', 'Interested'),
        ('going', 'Going'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_interests")
    event_id = models.CharField(max_length=255)  # stores ticketmaster event id
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    timestamp = models.DateTimeField(default=now)

    class Meta:
        unique_together = ('user', 'event_id')  # prevents duplicate entries

    def __str__(self):
        return f"{self.user.username} is {self.status} for {self.event_id}"


EVENT_TYPE_CHOICES = [
    ('timed', 'Timed'),
    ('all_day', 'All Day'),
]

REPEAT_CHOICES = [
    ('none', 'Never'),
    ('daily', 'Daily'),
    ('weekly', 'Weekly'),
    ('monthly', 'Monthly'),
    ('yearly', 'Yearly'),
]

CATEGORY_CHOICES = [
    ('networking', 'Networking'),
    ('workshop', 'Workshop'),
    ('conference', 'Conference'),
    ('seminar', 'Seminar'),
    ('social', 'Social'),
    ('other', 'Other'),
]

# INVITE FRIEND TO AN EVENT
class EventInvitation(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invitations')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_invitations')
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_invitations')
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')], default='pending')
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invitation from {self.sender.username} to {self.recipient.username} for {self.event.title}"


class WorkEvent(models.Model):
    image = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    planner = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    event_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)
    location = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    event_type = models.CharField(max_length=20, choices=[('timed', 'Timed'), ('all_day', 'All Day')])
    
    # For timed events
    timed_start = models.DateTimeField(null=True, blank=True)
    timed_end = models.DateTimeField(null=True, blank=True)

    # For all-day events
    all_day_start = models.DateField(null=True, blank=True)
    all_day_end = models.DateField(null=True, blank=True)

    repeat_frequency = models.CharField(max_length=10, choices=REPEAT_CHOICES, default='none')
    repeat_end_date = models.DateField(null=True, blank=True)

    is_discoverable = models.BooleanField(default=False, help_text="Required. Must be checked to publish the event.")
    created_at = models.DateTimeField(auto_now_add=True)

    # price for work event
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default='EUR', blank=True)
    image = models.ImageField(upload_to='work_events/', null=True, blank=True)

    # ticket url for work event
    ticket_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.title


class Message(models.Model):
    sender = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='sent_messages'
    )
    receiver = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='received_messages'
    )
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f'{self.sender.username} -> {self.receiver.username}: {self.content[:20]}'

class Chat(models.Model):
    name = models.CharField(max_length=255, blank=True)
    participants = models.ManyToManyField(User, related_name='chats')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name or f"Chat {self.id}"
    
from django.conf import settings

class Group(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, related_name="groups_joined")
    created_at = models.DateTimeField(auto_now_add=True)

class GroupMessage(models.Model):
    group = models.ForeignKey(Group, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    
