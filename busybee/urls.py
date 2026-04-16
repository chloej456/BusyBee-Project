from django.urls import path
from . import views
from .views import event_status
from .forms import *
from django.conf.urls.static import static
from django.conf import settings
from .views import UserLoginView


urlpatterns = [
  path('', views.index, name="index"),  # Regular homepage
  path('workhome/', views.workhome, name="workhome"),  # Work user homepage
  path('register/', views.UserSignupView.as_view(), name="register"),
  path('login/', views.UserLoginView.as_view(template_name="login.html", authentication_form=UserLoginForm), name="login"),
  path('help/', views.help, name="help"),
  path('calendar/', views.calendar_view, name="calendar"),
  path('api/events/', views.fetch_events, name='fetch_events'),
  path('create-event/', views.create_event_router, name='create_event'),
  path('create_event/', views.create_event, name="create_event"),
  path('create_work_event/', views.create_work_event, name='create_work_event'),
  path('event_discovery/', views.event_discovery, name="event_discovery"),
  path('account/', views.account, name="account"),
  path('delete_event/<int:event_id>/', views.delete_event, name="delete_event"),
  path('leave_event/<int:event_id>/', views.leave_event, name='leave_event'),
  path('send-friend-request/<int:user_id>/', views.send_friend_request, name='send_friend_request'),
  path('friend-request/<int:request_id>/<str:action>/', views.handle_friend_request, name='handle_friend_request'),
  path('handle-friend-request/<int:request_id>/<str:action>/', views.handle_friend_request, name='handle_friend_request'),
  path('logout/', views.logout_user, name="logout"),
  path('edit-profile/', views.edit_profile, name='edit_profile'),
  path('inbox/', views.inbox, name='inbox'),
  path('inbox/<int:friend_id>/', views.inbox, name='start_chat'),
  path('chat/<int:friend_id>/', views.start_chat, name='start_chat'),
  path('chat/<int:friend_id>/send/', views.send_message, name='send_message'),
  path('my-work-events/', views.my_work_events, name='my_work_events'),
  path('send/', views.send_message, name='send_message'),
  path('chat/<int:user_id>/', views.chat_with_user, name='chat_with_user'),
  path('find-friends/', views.find_friends, name='find_friends'),
  path('unfriend/<int:user_id>/', views.unfriend, name='unfriend'),
  path('cancel_request/<int:user_id>/', views.cancel_friend_request, name='cancel_friend_request'),
  path('group/create/', views.create_group_chat, name='create_group_chat'),
  path('groupchat/<int:group_id>/', views.group_chat, name='group_chat'),
  path('groupchat/send/<int:group_id>/', views.send_group_message, name='send_group_message'),
  path('events/<int:event_id>/edit/', views.edit_event, name='edit_event'),
  path('events/<int:event_id>/delete/', views.delete_event, name='delete_event'),
  path('work-follows/', views.work_follows, name='work_follows'),
  path('get_friend_events/<int:friend_id>/', views.get_friend_events, name='get_friend_events'),
  path('event/status/', event_status, name="event_status"),
  path('profile/<str:username>/', views.view_profile, name='view_profile'),
  path('work-events/delete/<int:event_id>/', views.delete_work_event, name='delete_work_event'),
  path('work/dashboard/', views.work_dashboard, name='work_dashboard'),
  path('follow/<int:user_id>/', views.follow_user, name='follow_user'),
  path('unfollow/<int:user_id>/', views.unfollow_user, name='unfollow_user'),
  path('ticketmaster/<str:event_id>/going/', views.tm_add_to_calendar, name='tm_add_to_calendar'),
  path('event/going/', views.tm_event_going, name='tm_event_going'),
  path('invitation/respond/<int:invitation_id>/', views.respond_to_invitation, name='respond_to_invitation'),
  path("api/event_interest_data/", views.get_event_interest_data, name="get_event_interest_data"),
  path('event_discovery/event_details/<str:event_id>',views.tm_event_details, name='tm_event_details'),
  path('event/work/<str:event_id>/', views.work_event_details, name='work_event_details'),
  path('follow_work_user/<int:user_id>/', views.follow_work_user, name='follow_work_user'),
  path('work_user_statistics/', views.work_user_statistics, name = 'work_user_statistics'),
  path('search_results/', views.search_results, name="search_results"),
  path('get_suggested_times/', views.get_suggested_times, name='get_suggested_times'),
  path('search_results/tm/<str:event_id>/', views.tm_event_details, name='tm_event_detail'),
  path('search_results/work/<str:event_id>/', views.work_event_details, name='work_event_detail'),
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)