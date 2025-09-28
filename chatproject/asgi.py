import os
import django
from django.core.asgi import get_asgi_application

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatproject.settings')

# Initialize Django first
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator
import chat.routing

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                chat.routing.websocket_urlpatterns
            )
        )
    ),
})