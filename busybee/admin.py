from django.contrib import admin
from .models import *

# Register your models here.
admin.site.register(User)
admin.site.register(Event)
admin.site.register(Notification)
admin.site.register(FriendRequest)
admin.site.register(Friendship)
admin.site.register(EventInterest)
admin.site.register(EventInvitation)
admin.site.register(WorkEvent)
admin.site.register(Message)
admin.site.register(Chat)