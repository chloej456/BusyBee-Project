# asgi.py

import os
from channels.routing import get_default_application
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')

import django
django.setup()

from busybee.routing import application  # use this routing
