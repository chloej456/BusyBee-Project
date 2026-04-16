from .models import FriendRequest, Message

def pending_requests_count(request):
    if request.user.is_authenticated:
        count = FriendRequest.objects.filter(to_user=request.user).count()
        return {'pending_requests_count': count}
    return {'pending_requests_count': 0}

def pending_messages_count(request):
    if request.user.is_authenticated:
        count = Message.objects.filter(receiver=request.user, is_read=False).count()
        return {'pending_messages_count': count}
    return {}