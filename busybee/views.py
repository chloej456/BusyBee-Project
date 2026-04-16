from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse, HttpResponseForbidden
from django.views.generic import CreateView, TemplateView
from django.contrib.auth import login, logout, get_user_model
from .forms import *
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q, Count
from itertools import chain
from datetime import timedelta, datetime, time
from django.conf import settings
from django.views import View
from .models import User, Event, FriendRequest, Friendship, EventInterest, EventInvitation, WorkEvent, Notification, Message
from django.contrib.auth.models import User
from django.views.decorators.http import require_http_methods, require_POST
from dateutil.relativedelta import relativedelta
from django.views.decorators.csrf import csrf_exempt
from django.utils.dateparse import parse_datetime
from django.utils.timezone import localtime, make_aware, is_naive
from django.contrib import messages
from collections import defaultdict
from django.contrib import messages
from django.urls import reverse

import requests
from dotenv import load_dotenv
from zoneinfo import ZoneInfo
import os
import json

import logging
logger = logging.getLogger(__name__)

load_dotenv()


# Your Ticketmaster API Key
API_KEY = settings.TICKETMASTER_API_KEY 
API_URL = "https://app.ticketmaster.com/discovery/v2/events/"



# USER SIGN UP AND LOG IN
class UserSignupView(CreateView):
    model = User
    form_class = UserSignupForm
    template_name = 'register.html'

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)  # Log the user in after successful registration

        # Debugging print
        print(f"User {user.username} is_work_user: {user.is_work_user}")

        # Redirect based on user type
        if user.is_work_user:
            return redirect('workhome')
        else:
            return redirect('index')

    def form_invalid(self, form):
        print(form.errors)
        return self.render_to_response(self.get_context_data(form=form))  
        

class UserLoginView(LoginView):
    template_name = 'login.html'
    authentication_form = UserLoginForm
    redirect_authenticated_user = True
    next_page = '/'

    def form_invalid(self, form):
        print(form.errors)
        messages.error(self.request, "Invalid username or password.")
        return self.render_to_response(self.get_context_data(form=form)) 
        

def logout_user(request):
    logout(request)
    return redirect("/")

# NAV LINKS
def index(request):
    return render(request, 'index.html')

def workhome(request):
    return render(request, 'workhome.html')  

def work_follows(request):
    work_following = request.user.following.filter(is_work_user=True)
    featured_orgs = User.objects.filter(is_work_user=True) \
                                .exclude(id__in=request.user.following.filter(is_work_user=True)
                                                              .values_list('id', flat=True))
    return render(request, 'find_friends.html', {
        'work_following': work_following,
        'featured_orgs': featured_orgs,
    })

def view_profile(request, username):
    user_profile = get_object_or_404(User, username=username)
    return render(request, 'view_profile.html', {'profile': user_profile})

def follow_user(request, user_id):
    user_to_follow = get_object_or_404(User, id=user_id)
    request.user.following.add(user_to_follow)
    return redirect('view_profile', username=user_to_follow.username)

def unfollow_user(request, user_id):
    user_to_unfollow = get_object_or_404(User, id=user_id)
    request.user.following.remove(user_to_unfollow)
    return redirect('account', username=user_to_unfollow.username)

def search_results(request):
    query = request.GET.get("query", "").strip()
    location = request.GET.get("location", "").strip()
    events = []

    if query:
        api_url = f"{API_URL}?apikey={API_KEY}&classificationName={query}&size=150"
        if location:
            api_url += f"&city={location}"

        try:
            response = requests.get(api_url)
            response.raise_for_status()
            data = response.json()
            raw_events = data.get("_embedded", {}).get("events", [])

            for event in raw_events:
                processed_event = {
                    "id": event.get("id", ""),
                    "name": event.get("name", "Unknown Event"),
                    "date": event.get("dates", {}).get("start", {}).get("localDate", "TBA"),
                    "venue": event.get("_embedded", {}).get("venues", [{}])[0].get("name", "Unknown Venue"),
                    "city": event.get("_embedded", {}).get("venues", [{}])[0].get("city", {}).get("name", ""),
                    "image": event.get("images", [{}])[0].get("url", ""),
                    "source": "ticketmaster"
                }
                events.append(processed_event)
        except requests.exceptions.RequestException as e:
            print("Request failed:", e)
        except ValueError as e:
            print("JSON decoding failed:", e)

    local_events = WorkEvent.objects.all()
    if query:
        local_events = local_events.filter(title__icontains=query)
    if location:
        local_events = local_events.filter(location__icontains=location)

    for work_event in local_events:
        processed_local_event = {
            "id": work_event.id,
            "name": work_event.title,
            "date": (
                    work_event.timed_start.strftime("%Y-%m-%d")
                    if work_event.event_type == "timed"
                    else work_event.all_day_start.strftime("%Y-%m-%d")
                ),
            "venue": work_event.location,
            "city": work_event.location,
            "image": work_event.image_url if work_event.image else "",
            "source": "workevent"
        }
        events.append(processed_local_event)

    return render(request, "search_results.html", {
        "query": query,
        "location": location,
        "events": events,
    })

# TICKETMASTER EVENT DETAILS
def event_details(request, event_id):
    url = f"{API_URL}{event_id}.json?apikey={API_KEY}"
    response = requests.get(url)
    
    if response.status_code == 200:
        event_data = response.json()
    else:
        event_data = {"error": "Event not found"}

    return render(request, "event_details.html", {"event": event_data})

def logout_user(request):
    logout(request)
    return redirect("/")

def help(request):
    return render(request, 'help.html')

def calendar(request):
    return render(request, 'calendar.html')

def event_discovery(request):
    return render(request, 'event_discovery.html')

def calculate_profile_completion(user):
    fields = [
        user.first_name,
        user.last_name,
        user.email,
        user.bio,
        user.phone_number,
        user.date_of_birth,
        user.profile_picture,
    ]
    filled_fields = sum(1 for field in fields if field)
    return round((filled_fields / len(fields)) * 100)

@login_required
def account(request):
    user = request.user

    context = {
        'profile_completion': calculate_profile_completion(user),
    }

    if user.is_work_user:
        follower_count = User.objects.filter(following=user).count()
        hosted_events = WorkEvent.objects.filter(planner=user)
        total_events = hosted_events.count()

        event_ids = [f'work-{event.id}' for event in hosted_events]
        interests = EventInterest.objects.filter(event_id__in=event_ids)

        going_count = interests.filter(status='going').count()
        interested_count = interests.filter(status='interested').count()

        context.update({
            'follower_count': follower_count,
            'hosted_events': hosted_events,
            'going_count': going_count,
            'interested_count': interested_count,
        })
    else:
        context.update({
            'friends_list': user.friends.all(),
            'attending_events': user.attending_events.all(),
            'work_users_followed_count': user.following.filter(is_work_user=True).count() if hasattr(user, "following") else 0
        })

    if not request.user.is_work_user:
        context['profile_completion'] = calculate_profile_completion(request.user)

    return render(request, 'account.html', context)

import requests
from django.http import JsonResponse
from django.conf import settings

@login_required
def my_work_events(request):
    events = WorkEvent.objects.filter(planner=request.user).order_by('timed_start')
    return render(request, 'my_work_events.html', {'events': events})

login_required
def delete_work_event(request, event_id):
    event = get_object_or_404(WorkEvent, id=event_id, planner=request.user)
    event.delete()
    return redirect('my_work_events')


@login_required
def work_dashboard(request):
    now_time = now()

    upcoming_events = WorkEvent.objects.filter(
        planner=request.user
    ).filter(
        Q(timed_start__gte=now_time) |
        Q(all_day_start__gte=now_time)
    ).order_by('timed_start')

    past_events = WorkEvent.objects.filter(
        planner=request.user
    ).filter(
        Q(timed_start__lt=now_time) |
        Q(all_day_start__lt=now_time)
    ).order_by('-timed_start')

    total_events = WorkEvent.objects.filter(planner=request.user).count()
    follower_count = User.objects.filter(following=request.user).count()

    return render(request, 'workhome.html', {
        'upcoming_events': upcoming_events,
        'past_events': past_events,
        'total_events': total_events,
        'follower_count': follower_count,
    })


def fetch_events(request):
    base_url = "https://app.ticketmaster.com/discovery/v2/events"
    params = {
        "apikey": settings.TICKETMASTER_API_KEY,
        "size": 50,
    }

    print("Query Parameters:", request.GET)

    if 'classificationName' in request.GET:
        params['classificationName'] = request.GET['classificationName']
    if 'city' in request.GET:
        params['city'] = request.GET['city']
    if 'startDateTime' in request.GET:
        params['startDateTime'] = request.GET['startDateTime']
    if 'endDateTime' in request.GET:
        params['endDateTime'] = request.GET['endDateTime']

    response = requests.get(base_url, params=params)
    if response.status_code == 200:
        tm_data = response.json()
        tm_events = tm_data.get('_embedded', {}).get('events', [])

        for e in tm_events:
            e['url']  = reverse('tm_event_details', args=[e['id']])
            e['type'] = 'ticketmaster_event'

        work_events = WorkEvent.objects.filter(is_discoverable=True)
        serialized_work_events = []

        for we in work_events:
            serialized = {
                'id': f'work-{we.id}',
                'name': we.title,
                'dates': {
                    'start': {
                        'localDate': we.all_day_start.strftime("%Y-%m-%d") if we.event_type == 'all_day' 
                                else we.timed_start.strftime("%Y-%m-%d"),
                        'localTime': None if we.event_type == 'all_day' 
                                else we.timed_start.strftime("%H:%M:%S")
                    },
                    'end': {
                        'localDate': we.all_day_end.strftime("%Y-%m-%d") if we.event_type == 'all_day' 
                                else we.timed_end.strftime("%Y-%m-%d"),
                        'localTime': None if we.event_type == 'all_day' 
                                else we.timed_end.strftime("%H:%M:%S")
                    }
                },
                '_embedded': {
                    'venues': [{'name': we.location}]
                },
                'priceRanges': [{
                    'min': we.price,
                    'max': we.price,
                    'currency': we.currency
                }] if we.price else [],
                'images': [{'url': we.image.url}] if we.image else [{'url': ''}],
                'type': 'work_event',
                'url':  reverse('work_event_details', args=[f'work-{we.id}'])
            }
            serialized_work_events.append(serialized)
        
        # Combine both event sources
        combined_events = serialized_work_events + tm_events
        tm_data['_embedded']['events'] = combined_events
        
        return JsonResponse(tm_data, safe=False)
    else:
        return JsonResponse({'error': 'Unable to fetch events'}, status=response.status_code)


# CALENDAR DISPLAY
@login_required
def calendar_view(request, user_id=None):
    # check if we're viewing another user's calendar
    if user_id:
        viewing_user = User.objects.get(id=user_id)
    else:
        viewing_user = request.user  # default to the logged-in user

    # fetch events created by the viewed user (self or another)
    user_events = Event.objects.filter(user=viewing_user)

    # fetch accepted invitations for the viewed user
    accepted_invites = Event.objects.filter(
        invitations__recipient=viewing_user,  # Recipient is the viewed user
        invitations__status='accepted'  # Only accepted invitations
    )

    # Fetch events where the viewed user is attending (events they've accepted or joined)
    attending_events = Event.objects.filter(
        attendees=viewing_user  # User is attending the event
    )

    # Combine and deduplicate the events: user's own events, accepted invitations, and attending events
    all_events = (user_events | accepted_invites | attending_events).distinct().order_by('start_time')

    # Prepare the event data for rendering the calendar, including attendees
    event_data = []
    for event in all_events:
        local_start = localtime(event.start_time)
        local_end = localtime(event.end_time)

        # get the list of attendees (including the owner of the event)
        attendees = [event.user] + list(event.attendees.all())  # Include event owner as an attendee

        # if private, only show details to owner of event
        # check if user is in attendees (owner is already included)
        mask = event.is_private and (request.user not in attendees)
        display_title = event.title if not mask else 'Busy'
        display_location = event.location if not mask else 'No Location Available'
        display_attendees = ['N/A'] if mask else [att.username for att in attendees]

        # prepare event data to be passed to the frontend, including attendees
        event_data.append({
            'id': event.id,
            'title': display_title,
            'start': local_start.isoformat(),
            'end':   local_end.isoformat(),
            'backgroundColor': '#f2c054' if event.user == viewing_user else '#8ecae6',
            'attendees': display_attendees,
            'extendedProps': {
                'attendees': [att.username for att in attendees],
                'category': display_location,
                'is_owner': event.user == request.user,  # track actual ownership
                'is_viewing_own_calendar': (viewing_user == request.user)  # new property
            }
        })
        
            # 'attendees': [att.username for att in attendees],

    # fetch the friends list for the viewed user (if needed)
    # friends_list = viewing_user.friends.all()

    # only show invitations if viewing own calendar
    invitations = []
    if not user_id or viewing_user == request.user:
        invitations = EventInvitation.objects.filter(
            recipient=request.user,
            status='pending'
        ).select_related('event', 'sender')

    # render the calendar view
    return render(request, 'calendar.html', {
        'events': json.dumps(event_data),
        'friends_list': viewing_user.friends.all(),
        'viewing_user': viewing_user,
        'invitations': invitations
    })


# CREATE EVENT FOR USER
@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, user=request.user)
        if form.is_valid():
            cd = form.cleaned_data
            event_type = cd.get("event_type")
            title = cd.get("title")
            location = cd.get("location")
            repeat_frequency = cd.get("repeat_frequency")
            repeat_end_date = cd.get("repeat_end_date")
            is_private = cd.get("is_private")

            # define repeat intervals in days for both event types
            repeat_map = {
                'daily': 1,
                'weekly': 7,
                'monthly': 30,   # approximately
                'yearly': 365
            }

            # use zoneinfo for europe/dublin timezone
            from zoneinfo import ZoneInfo
            dublin_tz = ZoneInfo("Europe/Dublin")
            
            if event_type == "timed":
                # datetime fields for timed events
                start_time = cd.get("timed_start")
                end_time = cd.get("timed_end")

                # make sure start time and end time are timezone aware
                if timezone.is_naive(start_time):
                    start_time = start_time.replace(tzinfo=dublin_tz)
                else:
                    start_time = start_time.astimezone(dublin_tz)

                if timezone.is_naive(end_time):
                    end_time = end_time.replace(tzinfo=dublin_tz)
                else:
                    end_time = end_time.astimezone(dublin_tz)

                # create the initial timed event.
                event = Event.objects.create(
                    title=title,
                    location=location,
                    start_time=start_time,
                    end_time=end_time,
                    all_day=False,
                    repeat_frequency=repeat_frequency,
                    repeat_end_date=repeat_end_date,
                    user=request.user,
                    is_private=is_private,
                )
                
                # NOT-ALL-DAY EVENTS (TIMED)
                if repeat_frequency != 'none' and repeat_end_date:
                    duration = end_time - start_time

                    # create a datetime from repeat_end_date and start_time's time.
                    repeat_end_datetime = datetime.combine(repeat_end_date, start_time.time())
                    # make sure it's timezone aware
                    repeat_end_datetime = repeat_end_datetime.replace(tzinfo=dublin_tz)
                    
                    # initialize next_start based on the start_time
                    if repeat_frequency == "daily":
                        next_start = start_time + timedelta(days=1)
                    elif repeat_frequency == "weekly":
                        next_start = start_time + timedelta(weeks=1)
                    elif repeat_frequency == "monthly":
                        next_start = (start_time + relativedelta(months=1)).replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second)
                    elif repeat_frequency == "yearly":
                        next_start = (start_time + relativedelta(years=1)).replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second)
                    else:
                        next_start = start_time + timedelta(days=repeat_map.get(repeat_frequency, 0))
                    
                    # loop to create repeated events until repeat_end_datetime
                    while next_start <= repeat_end_datetime:
                        # calculate the new end time using the same duration as the original event
                        new_end = next_start + duration

                        # ensure next_start and new_end are in Dublin timezone
                        next_start = next_start.astimezone(dublin_tz)
                        new_end = new_end.astimezone(dublin_tz)

                        # create the repeated event
                        Event.objects.create(
                            title=title,
                            location=location,
                            start_time=next_start,
                            end_time=new_end,
                            all_day=False,
                            repeat_frequency='none',  # mark repeated events as standalone.
                            user=request.user,
                            is_private=is_private,
                            parent_event=event
                        )

                        # update next_start by adding the appropriate interval
                        if repeat_frequency == "daily":
                            next_start += timedelta(days=1)
                        elif repeat_frequency == "weekly":
                            next_start += timedelta(weeks=1)
                        elif repeat_frequency == "monthly":
                            next_start = (next_start + relativedelta(months=1)).replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second)
                        elif repeat_frequency == "yearly":
                            next_start = (next_start + relativedelta(years=1)).replace(hour=start_time.hour, minute=start_time.minute, second=start_time.second)
                        else:
                            next_start += timedelta(days=repeat_map.get(repeat_frequency, 0))
                        
            elif event_type == "all_day":
                # for all-day events, we work with date fields.
                # get all-day start and end dates
                start_date = cd.get("all_day_start")
                end_date = cd.get("all_day_end")

                # convert to datetime format with midnight time
                start_time = datetime.combine(start_date, time.min)  # 00:00 of the start date
                end_time = datetime.combine(end_date, time.max)  # 23:59 of the end date

                # ensure timezone awareness for all-day events too
                start_time = start_time.replace(tzinfo=dublin_tz)
                end_time = end_time.replace(tzinfo=dublin_tz)
                
                # create the initial all-day event.
                event = Event.objects.create(
                    title=title,
                    location=location,
                    start_time=start_time,
                    end_time=end_time,
                    all_day=True,
                    repeat_frequency=repeat_frequency,
                    repeat_end_date=repeat_end_date,
                    user=request.user,
                    is_private=is_private,
                )
                
                # ALL-DAY EVENTS
                if repeat_frequency != 'none' and repeat_end_date:
                    interval = repeat_map.get(repeat_frequency, 0)
                    duration = end_time - start_time  # calculate event duration (as a date)
                    next_start = start_time + timedelta(days=interval)
                    
                    while next_start.date() <= repeat_end_date:
                        new_end = next_start + duration
                        Event.objects.create(
                            title=title,
                            location=location,
                            start_time=next_start,
                            end_time=new_end,
                            all_day=True,
                            repeat_frequency='none',
                            user=request.user,
                            is_private=is_private,
                            parent_event=event
                        )
                        next_start += timedelta(days=interval)
            
            # Send invitations to selected friends
            invited_friends = form.cleaned_data.get('invited_friends', [])
            for friend in invited_friends:
                invitation = EventInvitation.objects.create(
                    event=event,
                    sender=request.user,
                    recipient=friend,
                    status='pending'
                )

                # create a chat message
                message_content = (
                    f"You've been invited to the event '{event.title}' "
                    f"on {event.start_time.strftime('%b %d, %Y at %I:%M %p')}. "
                    "Check your invitations on the calendar page to respond."
                )
                Message.objects.create(
                    sender=request.user,
                    receiver=friend,
                    content=message_content
                )
                        
            return redirect('calendar')
    else:
        # form = EventForm()
        form = EventForm(user=request.user)

    # Fetch the list of friends for the user
    friends_list = request.user.friends.all()
    
    return render(request, "create_event.html", {"form": form, "friends_list": friends_list})

# DELETE EVENT
@require_POST
@login_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)

    if event.user != request.user:
        return HttpResponseForbidden("You are not allowed to delete this event.")
    
    event.delete()
    return redirect('calendar')

# EDIT EVENT
@login_required
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, user=request.user)

    if request.method == 'POST':
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, "Event updated successfully!")
            return redirect('account')
    else:
        form = EventForm(instance=event)

    return render(request, 'edit_event.html', {'form': form, 'event': event})

# ATTENDEES LEAVE AN EVENT
@require_POST
@login_required
def leave_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    event.attendees.remove(request.user)
    return JsonResponse({'status': 'success'})


# ADD TICKETMASTER EVENT TO CALENDAR

# fetch the specific event using event ID
def fetch_ticketmaster_event(event_id):
    API_KEY = settings.TICKETMASTER_API_KEY
    url = f"https://app.ticketmaster.com/discovery/v2/events/{event_id}.json"
    params = {
        'apikey': API_KEY
    }

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return response.json()
    return None

# adding fetched event to the calendar
@login_required
def tm_add_to_calendar(request, event_id):
    if request.method == "POST":
        # fetch event details from ticketmaster using event id
        event_data = fetch_ticketmaster_event(event_id)

        if not event_data:
            return redirect('tm_event_details', event_id=event_id)

        # extract details
        title = event_data.get("name", "Ticketmaster Event")
        venue = event_data.get("_embedded", {}).get("venues", [{}])[0]
        location = venue.get("name", "Unknown Location")

        # parse the start and end datetime strings
        start_str = event_data.get("dates", {}).get("start", {}).get("dateTime")
        end_str = event_data.get("dates", {}).get("end", {}).get("dateTime")

        if start_str:
            start_time = parse_datetime(start_str)
        else:
            start_time = timezone.now()

        if end_str:
            end_time = parse_datetime(end_str)
        else:
            # fallback: 2-hour event if no end time
            end_time = start_time + timedelta(hours=2)

        # save to user's calendar
        Event.objects.create(
            title=title,
            location=location,
            start_time=start_time,
            end_time=end_time,
            all_day=False,
            user=request.user
        )

        messages.success(request, f"'{title}' was added to your calendar!")
        return redirect('calendar')

    return redirect('tm_event_details', event_id=event_id)

User = get_user_model()

# TICKETMASTER AND WORK EVENT HANDLE GOING
@csrf_exempt
@login_required
def tm_event_going(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_id = data.get("event_id")

            if not event_id:
                return JsonResponse({"success": False, "message": "Missing event_id."}, status=400)

            # handle work event
            if event_id.startswith('work-'):
                work_event_id = event_id.split('work-')[1]
                try:
                    work_event = WorkEvent.objects.get(id=work_event_id)

                    # handle recurring events
                    if work_event.repeat_frequency != 'none' and work_event.repeat_end_date:

                        if work_event.event_type == 'all_day':
                            # all-day recurring events
                            start_date = work_event.all_day_start
                            end_date = work_event.all_day_end
                            duration_days = (end_date - start_date).days + 1
                            current_start = start_date
                            repeat_end = work_event.repeat_end_date

                            while current_start <= repeat_end:
                                current_end = current_start + timedelta(days=duration_days - 1)
                                Event.objects.create(
                                    title=work_event.title,
                                    location=work_event.location,
                                    start_time=datetime.combine(current_start, time.min).replace(tzinfo=timezone.utc),
                                    end_time=datetime.combine(current_end, time.max).replace(tzinfo=timezone.utc),
                                    all_day=True,
                                    user=request.user
                                )
                                # update current_start based on frequency
                                if work_event.repeat_frequency == 'daily':
                                    current_start += timedelta(days=1)
                                elif work_event.repeat_frequency == 'weekly':
                                    current_start += timedelta(weeks=1)
                                elif work_event.repeat_frequency == 'monthly':
                                    current_start += relativedelta(months=1)
                                elif work_event.repeat_frequency == 'yearly':
                                    current_start += relativedelta(years=1)
                        else:
                            # timed recurring events
                            start = work_event.timed_start
                            end = work_event.timed_end
                            duration = end - start
                            repeat_end = datetime.combine(
                                work_event.repeat_end_date, 
                                start.time()
                            ).replace(tzinfo=start.tzinfo)
                            
                            current_start = start
                            while current_start <= repeat_end:
                                Event.objects.create(
                                    title=work_event.title,
                                    location=work_event.location,
                                    start_time=current_start,
                                    end_time=current_start + duration,
                                    all_day=False,
                                    user=request.user
                                )
                                # update current_start based on frequency
                                if work_event.repeat_frequency == 'daily':
                                    current_start += timedelta(days=1)
                                elif work_event.repeat_frequency == 'weekly':
                                    current_start += timedelta(weeks=1)
                                elif work_event.repeat_frequency == 'monthly':
                                    current_start += relativedelta(months=1)
                                elif work_event.repeat_frequency == 'yearly':
                                    current_start += relativedelta(years=1)
                    else:
                        # single event // timezone aware
                        if work_event.event_type == 'all_day':
                            start = datetime.combine(work_event.all_day_start, time.min)
                            end = datetime.combine(work_event.all_day_end, time.max)
                        else:
                            start = work_event.timed_start
                            end = work_event.timed_end
                        
                        Event.objects.create(
                            title=work_event.title,
                            location=work_event.location,
                            start_time=start,
                            end_time=end,
                            all_day=(work_event.event_type == 'all_day'),
                            user=request.user
                        )

                except WorkEvent.DoesNotExist:
                    return JsonResponse({"success": False, "message": "WorkEvent not found."}, status=404)

            # handle Ticketmaster event
            else:
                event_data = fetch_ticketmaster_event(event_id)
                if not event_data:
                    return JsonResponse({"success": False, "message": "Event not found."}, status=404)

                # extract event details
                title = event_data.get("name", "Ticketmaster Event")
                venue = event_data.get("_embedded", {}).get("venues", [{}])[0]
                location = venue.get("name", "Unknown Location")

                # parse start and end times
                start_str = event_data.get("dates", {}).get("start", {}).get("dateTime")
                end_str = event_data.get("dates", {}).get("end", {}).get("dateTime")

                start_time = parse_datetime(start_str) if start_str else timezone.now()
                end_time = parse_datetime(end_str) if end_str else start_time + timedelta(hours=2)

                # create calendar event
                Event.objects.create(
                    title=title,
                    location=location,
                    start_time=start_time,
                    end_time=end_time,
                    all_day=False,
                    user=request.user
                )
            
            # update EventInterest status for WorkEvent and ticketmaster
            EventInterest.objects.update_or_create(
                user=request.user,
                event_id=event_id,
                defaults={"status": "going"}
            )
            return JsonResponse({"success": True, "message": "Event added to calendar and marked as going."})

        except Exception as e:
            print(f"Error: {str(e)}")
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

@login_required
def find_friends(request):
    query = request.GET.get('q', '')

    friends_list = request.user.friends.all()
    friend_ids = friends_list.values_list('id', flat=True)

    received_requests = FriendRequest.objects.filter(to_user=request.user, is_active=True)
    sent_requests = FriendRequest.objects.filter(from_user=request.user, is_active=True)

    # Combine all users to exclude from "People You May Know"
    excluded_ids = set(friend_ids) | \
                   set(received_requests.values_list('from_user_id', flat=True)) | \
                   set(sent_requests.values_list('to_user_id', flat=True)) | \
                   {request.user.id}

    potential_friends = User.objects.exclude(id__in=excluded_ids)

    following_orgs = request.user.following.filter(is_work_user=True)

    featured_orgs = User.objects.filter(is_work_user=True) \
                                .exclude(id__in=following_orgs.values_list('id', flat=True))


    if query:
        potential_friends = potential_friends.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query)
        )

    context = {
        'query': query,
        'potential_friends': potential_friends,
        'received_requests': received_requests,
        'sent_requests': sent_requests,
        'friends_list': friends_list,
        'following_orgs': following_orgs,
        'featured_orgs' : featured_orgs,
    }


    return render(request, 'find_friends.html', context)

@login_required
def cancel_friend_request(request, user_id):
    friend_request = FriendRequest.objects.filter(from_user=request.user, to_user__id=user_id, is_active=True).first()
    if friend_request:
        friend_request.delete()
        messages.success(request, "Friend request cancelled.")
    else:
        messages.warning(request, "No active friend request found.")
    return redirect('find_friends')


@login_required
def send_friend_request(request, user_id):
    to_user = get_object_or_404(User, id=user_id)
    existing_request = FriendRequest.objects.filter(from_user=request.user, to_user=to_user, is_active=True)
    if not existing_request.exists() and request.user != to_user:
        FriendRequest.objects.create(from_user=request.user, to_user=to_user)
        messages.success(request, f"Friend request sent to {to_user.username}.")
    else:
        messages.warning(request, "Friend request already sent or invalid.")
    return redirect('find_friends')


@login_required
def handle_friend_request(request, request_id, action):
    friend_request = get_object_or_404(FriendRequest, id=request_id, to_user=request.user)

    if request.method == "POST":
        if action == "accept":
            # Add each other as friends
            request.user.friends.add(friend_request.from_user)
            friend_request.from_user.friends.add(request.user)
            friend_request.delete()
        elif action == "reject":
            friend_request.delete()
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'account')

@login_required
def unfriend(request, user_id):
    other_user = get_object_or_404(User, id=user_id)

    # Remove from user.friends if you're using a ManyToMany field
    request.user.friends.remove(other_user)
    other_user.friends.remove(request.user)

    # Also delete the Friendship model object (if used)
    friendship = Friendship.objects.filter(
        Q(user1=request.user, user2=other_user) |
        Q(user1=other_user, user2=request.user)
    ).first()
    if friendship:
        friendship.delete()

    messages.info(request, f"You are no longer friends with {other_user.username}.")

    # Redirect back to the referring page
    referer = request.META.get('HTTP_REFERER')
    return redirect(referer if referer else 'account')


# FRIENDS EVENTS FOR CALENDAR
@login_required
def get_friend_events(request, friend_id):
    friend = get_object_or_404(User, id=friend_id)
    
    # fetch events created by the friend
    user_events = Event.objects.filter(user=friend)

    # fetch events where the friend has accepted invitations
    accepted_invites = Event.objects.filter(
        invitations__recipient=friend,
        invitations__status='accepted'
    )

    # fetch events where the friend is an attendee
    attending_events = Event.objects.filter(attendees=friend)

    # make sure the friend is actually a friend (this shouldnt happen but just in case)
    if friend not in request.user.friends.all():
        return JsonResponse({'error': 'Not authorized to view this user\'s events'}, status=403)

    # combine and deduplicate
    all_events = (user_events | accepted_invites | attending_events).distinct().order_by('start_time')
    
    # list of 10 random colors (to differentiate from each person)
    friend_colors = [
        "#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", 
        "#33FFF5", "#F5FF33", "#FF8C33", "#8C33FF", "#33FFA1"
    ]

    # assign a color based on friend's ID (modulo ensures we stay within 10 colors)
    assigned_color = friend_colors[int(friend_id) % len(friend_colors)]

    # get events the friend owns, attends, OR is invited to
    events = Event.objects.filter(
        Q(user=friend) | 
        Q(attendees=friend) |
        Q(invitations__recipient=friend)  # includes pending/accepted invites
    ).prefetch_related('attendees', 'invitations').distinct()

    event_data = []
    for event in all_events:
            # for all-day events, assume the model uses start_date/end_date; for timed events use start_time/end_time
            if event.all_day:
                start = event.start_date.isoformat() if hasattr(event, 'start_date') else event.start_time.isoformat()
                end = event.end_date.isoformat() if hasattr(event, 'end_date') else event.end_time.isoformat()
            else:
                start = event.start_time.isoformat()
                end = event.end_time.isoformat()

            attendees_list = [event.user] + list(event.attendees.all())

            # and if the logged-in user is viewing a friend's calendar (not the friend themselves)
            # and they are not already in the attendee list, check if they have accepted the invitation
            if request.user != friend and request.user not in attendees_list:
                if EventInvitation.objects.filter(event=event, recipient=request.user, status='accepted').exists():
                    attendees_list.append(request.user)

            attendee_usernames = [user.username for user in attendees_list]
            
            local_start = localtime(event.start_time)
            local_end = localtime(event.end_time)
            attendees = [event.user] + list(event.attendees.all())

            # only mask if it's private and i'm not the owner
            mask = event.is_private and (request.user not in attendees_list)
            display_title = event.title if not mask else 'Busy'
            display_location = event.location if not mask else 'No Location Available'
            display_attendees = ['N/A'] if mask else [user.username for user in attendees_list]

            event_data.append({
                'id': event.id,
                'title': display_title,
                'start': start,
                'end':   end,
                'allDay': event.all_day,
                'backgroundColor': assigned_color, # friend's unique colour (up to 10)
                'attendees': display_attendees,
                'extendedProps': {
                    'attendees': display_attendees,
                    'category': display_location,
                    'is_owner': event.user == request.user,  # actual ownership
                    'is_viewing_own_calendar': False  # always false for friend's events
                }
            })

    return JsonResponse(event_data, safe=False)

# TICKET MASTER EVENT DETAILS
def tm_event_details(request, event_id):
    # fetch event details and show friends who are interested or going
    
    # fetch event data from Ticketmaster API
    url = f"{API_URL}{event_id}.json?apikey={API_KEY}"
    response = requests.get(url)

    event = None
    if response.status_code == 200:
        event_data = response.json()
        
        # make sure venues data is available
        venues = event_data.get('_embedded', {}).get('venues', [])
        event_data['venues'] = venues  # add venues directly to the event_data dictionary
        event = event_data  # assign the cleaned event data to 'event'
    else:
        event = {"error": "Event not found"}  # handle API failure

    # fetch friends who marked interest or going
    user = request.user
    friends_interested = []
    friends_going = []

    if user.is_authenticated:
        friends = user.friends.all()  # get user's friends
        
        friends_interested = EventInterest.objects.filter(
            user__in=friends, event_id=event_id, status="interested"
        )

        friends_going = EventInterest.objects.filter(
            user__in=friends, event_id=event_id, status="going"
        )
    
    user_status = None
    if request.user.is_authenticated:
        try:
            user_interest = EventInterest.objects.get(user=request.user, event_id=event_id)
            user_status = user_interest.status
        except EventInterest.DoesNotExist:
            user_status = None

    context = {
        "event": event,
        "friends_interested": friends_interested,
        "friends_going": friends_going,
        "user_status": user_status,
    }

    return render(request, "tm_event_details.html", context)

# TICKETMASTER EVENT INTEREST

@csrf_exempt
@login_required
def event_status(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_id = data.get("event_id")
            status = data.get("status")

            if not event_id:
                return JsonResponse({"success": False, "message": "Missing event_id."}, status=400)

            # handle work events
            if event_id.startswith('work-'):
                work_event_id = event_id.replace("work-", "")
                if not WorkEvent.objects.filter(id=work_event_id).exists():
                    return JsonResponse({"success": False, "message": "Event not found"}, status=404)
            else:
                # must verify through API for tm events
                event_data = fetch_ticketmaster_event(event_id)
                if not event_data:
                    return JsonResponse({"success": False, "message": "Event not found"}, status=404)
                
            if status not in ["interested", "going"]:
                return JsonResponse({"success": False, "message": "Invalid status."}, status=400)

            event_interest, created = EventInterest.objects.update_or_create(
                user=request.user,
                event_id=event_id,
                defaults={"status": status}
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method."}, status=405)

# WORK EVENT DETAILS
def work_event_details(request, event_id):
    try:
        # remove the work- prefix
        work_event_id = event_id.replace('work-', '')
        event = WorkEvent.objects.get(id=work_event_id)
        
        # get user's friends
        friends = request.user.friends.all()

        # filter interest/going by friends
        friends_interested = EventInterest.objects.filter(
            event_id=f'work-{event.id}',
            status='interested',
            user__in=friends
        ).select_related('user')
        
        friends_going = EventInterest.objects.filter(
            event_id=f'work-{event.id}',
            status='going',
            user__in=friends
        ).select_related('user')
        
        # get user status
        user_status = None
        if request.user.is_authenticated:
            try:
                user_interest = EventInterest.objects.get(
                    user=request.user,
                    event_id=f'work-{event.id}'
                )
                user_status = user_interest.status
            except EventInterest.DoesNotExist:
                pass
        
        # get user's status
        user_status = None
        if request.user.is_authenticated:
            try:
                user_interest = EventInterest.objects.get(
                    user=request.user,
                    event_id=f'work-{event.id}'
                )
                user_status = user_interest.status
            except EventInterest.DoesNotExist:
                pass
        
        context = {
            'event': event,
            'friends_interested': friends_interested,
            'friends_going': friends_going,
            'user_status': user_status
        }
        
        return render(request, 'work_event_details.html', context)

    except WorkEvent.DoesNotExist:
            return render(request, 'work_event_details.html', {'error': 'Event not found'})


@login_required
def create_event_router(request):
    if request.user.is_work_user:
        # Use Work Event form and template
        form = WorkEventForm(request.POST or None)
        template = 'create_work_event.html'
    else:
        # Use Normal Event form and template
        form = EventForm(request.POST or None)
        template = 'create_event.html'

    if request.method == 'POST' and form.is_valid():
        event = form.save(commit=False)
        event.user = request.user  # or event.planner for WorkEvent
        if hasattr(event, 'planner'):  # For WorkEvent
            event.planner = request.user
        event.save()
        return redirect('calendar')  # or wherever you want

    return render(request, template, {'form': form})



# INVITATION LOGIC
@login_required
def respond_to_invitation(request, invitation_id):
    invitation = get_object_or_404(EventInvitation, id=invitation_id)

    # ensure the invitation is for the current user
    if invitation.recipient != request.user:
        return redirect('calendar')

    if request.method == 'POST':
        action = request.POST.get('action')

        # if the action is to accept the invitation
        if action == 'accept':
            invitation.status = 'accepted'
            invitation.save()
            # add the user to the event's attendees (attending_events)
            # invitation.event.attendees.add(request.user)

            # add to parent + children events
            all_events = Event.objects.filter(
                Q(id=invitation.event.id) |  # original event
                Q(parent_event=invitation.event) |  # child event
                Q(id=invitation.event.parent_event_id)  # parent event
            ).distinct()

            # include original event
            # all_events = related_events | Event.objects.filter(id=invitation.event.id)
            
            # add user to all related events
            for event in all_events:
                event.attendees.add(request.user)

            # sibling_events = Event.objects.filter(parent_event=invitation.event)

        # if the action is to decline the invitation
        elif action == 'decline':
            invitation.status = 'declined'
            invitation.save()

        # redirect to the calendar page after responding
        return redirect('calendar')

    return HttpResponse(status=400)  # if the request method is not POST

# only for work users
@login_required
def create_work_event(request):
    if not request.user.is_work_user:
        return HttpResponseForbidden("Access denied")
    
    if request.method == 'POST':
        form = WorkEventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.planner = request.user
            event.save()
            return redirect('event_discovery')
    else:
        form = WorkEventForm()
    
    return render(request, "create_work_event.html", {'form': form})


def discover_events(request):
    events = WorkEvent.objects.filter(is_discoverable=True).order_by('-created_at')
    return render(request, 'discover_events.html', {'events': events})



# display interested or going under every event in event discovery page
# GET EVENT INTEREST INFO
@csrf_exempt
def get_event_interest_data(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            event_ids = data.get("event_ids", [])
            user = request.user

            if not user.is_authenticated:
                return JsonResponse({"success": True, "data": {}})

            friends = user.friends.all()
            response_data = {}

            # handles ticketmaster and workevent IDs
            for event_id in event_ids:
                # only include EventInterest objects from friends
                interest_query = EventInterest.objects.filter(
                    event_id=event_id,
                    user__in=friends
                )

                interested_users = list(interest_query.filter(status='interested')
                                  .values_list('user__username', flat=True))
                going_users = list(interest_query.filter(status='going')
                                .values_list('user__username', flat=True))

                response_data[event_id] = {
                    "interested": interested_users,
                    "going": going_users,
                }

            return JsonResponse({"success": True, "data": response_data})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)}, status=500)

    return JsonResponse({"success": False, "message": "Invalid request method"}, status=405)

@login_required
def edit_profile(request):
    if request.method == 'POST':
        form = EditProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('account')  # redirect to the profile page
    else:
        form = EditProfileForm(instance=request.user)
    
    return render(request, 'edit_profile.html', {'form': form})




@login_required
def inbox(request):
    user = request.user
    friends_list = user.friends.all()
    groups = Group.objects.filter(members=user)

    # Count unread messages per friend
    unread_counts = (
        Message.objects
        .filter(receiver=user, is_read=False)
        .values('sender')
        .annotate(count=Count('id'))
    )
    unread_map = {item['sender']: item['count'] for item in unread_counts}

    attending_events = Event.objects.filter(
        Q(user=user) |
        Q(attendees=user) |
        Q(invitations__recipient=user, invitations__status='accepted')
    ).distinct().order_by('start_time')

    context = {
        'friends_list': friends_list,
        'groups': groups,
        'unread_map': unread_map,
        'attending_events': attending_events,
    }

    return render(request, 'inbox.html', context)


def start_chat(request, friend_id):
    user = request.user
    friend = User.objects.get(id=friend_id)

    chat = Chat.objects.filter(participants=user).filter(participants=friend).first()
    Message.objects.filter(sender=friend, receiver=request.user, is_read=False).update(is_read=True)
    unread_messages = Message.objects.filter(receiver=request.user, is_read=False)

    unread_map = {}
    for msg in unread_messages:
        sender_id = msg.sender.id  # FIXED: use `.id` not the object
        unread_map[sender_id] = unread_map.get(sender_id, 0) + 1

    if not chat:
        chat = Chat.objects.create(name=f"{user.username}-{friend.username}")
        chat.participants.add(user, friend)

    messages = Message.objects.filter(
        (Q(sender=user) & Q(receiver=friend)) |
        (Q(sender=friend) & Q(receiver=user))
    ).order_by('timestamp')

    attending_events = Event.objects.filter(
        Q(user=user) |
        Q(attendees=user) |
        Q(invitations__recipient=user, invitations__status='accepted')
    ).distinct().order_by('start_time')

    context = {
    'selected_friend': friend,
    'chat': chat,
    'messages': messages,
    'friends_list': user.friends.all(),
    'unread_map': unread_map,
    'attending_events': attending_events,
}

    return render(request, 'inbox.html', context)

from django.views.decorators.http import require_POST

@require_POST
@login_required
def send_message(request, friend_id):
    content = request.POST.get('content')
    friend = get_object_or_404(User, id=friend_id)

    if content:
        Message.objects.create(sender=request.user, receiver=friend, content=content)

    return redirect('start_chat', friend_id=friend.id)

@login_required
def chat_with_user(request, user_id):
    other_user = User.objects.get(pk=user_id)
    messages = Message.objects.filter(
        sender__in=[request.user, other_user],
        receiver__in=[request.user, other_user]
    ).order_by('timestamp')
    
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=request.user, receiver=other_user, content=content)
            return redirect('chat_with_user', user_id=other_user.id)
    
    return render(request, 'inbox.html', {
        'messages': messages,
        'other_user': other_user
    })


@login_required
def create_group_chat(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        member_ids = request.POST.getlist('members')
        group = Group.objects.create(name=name)
        group.members.add(*member_ids)
        group.members.add(request.user)
        return redirect('group_chat', group_id=group.id)
    return redirect('inbox')

@login_required
def group_chat(request, group_id):
    group = get_object_or_404(Group, id=group_id, members=request.user)
    messages = group.messages.all().order_by('timestamp')
    
    attending_events = Event.objects.filter(
        Q(user=request.user) |
        Q(attendees=request.user) |
        Q(invitations__recipient=request.user, invitations__status='accepted')
    ).distinct().order_by('start_time')

    context = {
        'selected_group': group,
        'group_messages': messages,
        'friends_list': request.user.friends.all(),
        'groups': Group.objects.filter(members=request.user),
        'attending_events': attending_events,
    }
    return render(request, 'inbox.html', context)

@require_POST
@login_required
def send_group_message(request, group_id):
    group = get_object_or_404(Group, id=group_id, members=request.user)
    content = request.POST.get('content')
    
    if content:
        GroupMessage.objects.create(group=group, sender=request.user, content=content)

    return redirect('group_chat', group_id=group.id)

@login_required
def follow_work_user(request, user_id):
    target = get_object_or_404(User, id=user_id, is_work_user=True)
    request.user.following.add(target)
    
    # Optional: add notification logic here
    Notification.objects.create(
        user=target,
        message=f"{request.user.username} is now following you."
    )

    return redirect('find_friends')


@login_required
def work_user_statistics(request):
    user = request.user
    if not user.is_work_user:
        return HttpResponseForbidden("Access restricted to work users only.")

    follower_count = User.objects.filter(following=user).count()
    work_events = WorkEvent.objects.filter(planner=user)
    total_events = work_events.count()

    event_ids = [f'work-{event.id}' for event in work_events]
    interests = EventInterest.objects.filter(event_id__in=event_ids)

    going_count = interests.filter(status='going').count()
    interested_count = interests.filter(status='interested').count()

    # Engagement per event
    event_stats = []
    for event in work_events:
        full_event_id = f'work-{event.id}'
        going = interests.filter(event_id=full_event_id, status='going').count()
        interested = interests.filter(event_id=full_event_id, status='interested').count()
        event_stats.append({'title': event.title, 'going': going, 'interested': interested})

    # Simulate time-series data
    today = now().date()
    last_7_days = [today - timedelta(days=i) for i in reversed(range(7))]
    def count_per_day(queryset, date_field):
        daily_counts = defaultdict(int)
        for day in last_7_days:
            count = queryset.filter(**{f"{date_field}__date": day}).count()
            daily_counts[str(day)] = count
        return [daily_counts[str(d)] for d in last_7_days]

    followers_ts = count_per_day(User.objects.filter(following=user), 'date_joined')  # Needs date_joined of follower
    events_ts = count_per_day(work_events, 'created_at')  # Needs a created_at on WorkEvent
    interested_ts = count_per_day(interests.filter(status='interested'), 'timestamp')
    going_ts = count_per_day(interests.filter(status='going'), 'timestamp')

    context = {
        'follower_count': follower_count,
        'total_events': total_events,
        'going_count': going_count,
        'interested_count': interested_count,
        'work_events': work_events,
        'event_stats': event_stats,
        'labels': [str(d) for d in last_7_days],
        'followers_ts': followers_ts,
        'events_ts': events_ts,
        'interested_ts': interested_ts,
        'going_ts': going_ts,
    }
    return render(request, 'statistics.html', context)


# FIND TIMES WHEN FRIENDS ARE FREE AND GIVE EVENT SUGGESTIONS

@login_required
def get_suggested_times(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid method'}, status=400)

    friend_ids = json.loads(request.body).get('friends', [])
    friends = User.objects.filter(id__in=friend_ids)
    
    # get busy intervals for user and friends
    busy_intervals = get_busy_intervals(request.user)
    for friend in friends:
        busy_intervals += get_busy_intervals(friend)
    
    # find free time slots
    free_slots = find_free_slots(busy_intervals)
    
    # find matching events
    suggested_events = []
    for slot in free_slots:
        events = find_events_in_slot(slot['start'], slot['end'])
        if events:  # only include slots with events
            suggested_events.append({
                'start': slot['start'].isoformat(),
                'end': slot['end'].isoformat(),
                'events': events,
            })

    return JsonResponse({'suggestions': suggested_events})

# get when users are busy
def get_busy_intervals(user):
    events = Event.objects.filter(
        Q(user=user) | Q(attendees=user) | Q(invitations__recipient=user)
    ).distinct()
    return [(e.start_time, e.end_time) for e in events]

def find_free_slots(busy_intervals):
    # filter out past events and make timezone aware
    now = timezone.now()
    busy_intervals = [
        (max(start, now), end)
        for start, end in busy_intervals
        if end > now
    ]
    
    # merge intervals with 30 minutes between events
    merged = []
    for start, end in sorted(busy_intervals, key=lambda x: x[0]):
        if not merged:
            merged.append((start, end))
        else:
            last_start, last_end = merged[-1]
            # add 30 minutes between events
            if start <= last_end + timedelta(minutes=30):
                merged[-1] = (min(start, last_start), max(end, last_end))
            else:
                merged.append((start, end))
    
    # find slots for at least 1 hour
    free_slots = []
    previous_end = now
    for start, end in merged:
        if (start - previous_end) >= timedelta(hours=1):
            free_slots.append({
                'start': previous_end,
                'end': start
            })
        previous_end = max(previous_end, end)
    
    # final slot check
    if (timezone.now() + timedelta(days=14) - previous_end) >= timedelta(hours=1):
        free_slots.append({
            'start': previous_end,
            'end': timezone.now() + timedelta(days=14)
        })
    
    return free_slots

def find_events_in_slot(slot_start, slot_end):
    # ensure slot is at least 1 hour
    if (slot_end - slot_start) < timedelta(hours=1):
        return []

    # fetch ticketmaster events
    utc_start = slot_start.astimezone(timezone.utc)
    utc_end   = slot_end.astimezone(timezone.utc)

    tm_params = {
        'apikey': settings.TICKETMASTER_API_KEY,
        'city': 'Dublin',
        'countryCode': 'IE',
        'startDateTime': utc_start.isoformat(),
        'endDateTime': utc_end.isoformat(),
        'size': 5,
        'sort': 'date,asc'
    }

    try:
        resp = requests.get(API_URL, params=tm_params)
        resp.raise_for_status()
        tm_events = resp.json().get('_embedded', {}).get('events', [])
    except Exception:
        tm_events = []

    # fetch WorkEvents
    work_events = WorkEvent.objects.filter(
        is_discoverable=True
    ).filter(
        # timed events
        Q(event_type='timed', timed_start__lt=slot_end, timed_end__gt=slot_start) |
        # all‑day events (compare dates)
        Q(event_type='all_day',
          all_day_start__lte=slot_end.date(),
          all_day_end__gte=slot_start.date())
    ).distinct()

    # serialise both
    results = []

    # ticketmaster
    for e in tm_events:
        if time_in_slot(e, slot_start, slot_end):
            # parse start
            dt = e['dates']['start'].get('dateTime') or e['dates']['start'].get('localDate')
            # ensure ISO string
            t_iso = (parse_datetime(dt) if 'dateTime' in e['dates']['start']
                    else datetime.strptime(dt, '%Y-%m-%d')).isoformat()
            results.append({
                'title': e['name'],
                'time': t_iso,
                'source': 'Ticketmaster',
                'url': reverse('tm_event_details', args=[e['id']])
            })

    # workevents
    for we in work_events:
        if we.event_type == 'timed':
            start_dt = we.timed_start
        else:
            # all‑day, push to midnight
            start_dt = datetime.combine(we.all_day_start, time.min, tzinfo=timezone.get_current_timezone())
        results.append({
            'title':  we.title,
            'time':   start_dt.isoformat(),
            'source': 'BusyBee Event',
            'url':    reverse('work_event_details', args=[f'work-{we.id}'])
        })

    return results


def time_in_slot(event_data, slot_start, slot_end):
    try:
        # handle start time
        if 'localDate' in event_data['dates']['start']:
            naive_start = datetime.strptime(
                event_data['dates']['start']['localDate'], 
                '%Y-%m-%d'
            )
            event_start = timezone.make_aware(naive_start)
        else:
            event_start = parse_datetime(event_data['dates']['start']['dateTime'])
            if timezone.is_naive(event_start):
                event_start = timezone.make_aware(event_start, timezone.utc)
            event_start = event_start.astimezone(timezone.get_current_timezone())

        # handle end time because ticketmaster doesn't provide end dates sometimes
        if 'end' not in event_data['dates']:
            # default to 2 hours after start if theres no end time
            event_end = event_start + timedelta(hours=2)
        else:
            if 'localDate' in event_data['dates']['end']:
                naive_end = datetime.strptime(
                    event_data['dates']['end']['localDate'], 
                    '%Y-%m-%d'
                ).replace(hour=23, minute=59, second=59)
                event_end = timezone.make_aware(naive_end)
            elif 'dateTime' in event_data['dates']['end']:
                event_end = parse_datetime(event_data['dates']['end']['dateTime'])
                if timezone.is_naive(event_end):
                    event_end = timezone.make_aware(event_end, timezone.utc)
                event_end = event_end.astimezone(timezone.get_current_timezone())
            else:
                event_end = event_start + timedelta(hours=2)

        # convert slots to local timezone
        slot_start = slot_start.astimezone(timezone.get_current_timezone())
        slot_end = slot_end.astimezone(timezone.get_current_timezone())

        # calculate the overlap
        overlap_start = max(event_start, slot_start)
        overlap_end = min(event_end, slot_end)
        return (overlap_end - overlap_start) >= timedelta(hours=1)
        
    except KeyError as e:
        logger.error(f"Missing key in event data: {e}")
        return False
    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        return False
