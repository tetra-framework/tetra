"""
ASGI config for demosite project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.0/howto/deployment/asgi/
"""

import os
import asyncio
from pathlib import Path
from channels.security.websocket import AllowedHostsOriginValidator

from django.core.asgi import get_asgi_application

from demo.tasks import send_breaking_news_to_channel

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "demosite.settings")
BASE_DIR = Path(__file__).parent


class TetraASGIApplication:
    """Custom ASGI application that starts background tasks"""

    def __init__(self, application):
        self.application = application
        self._background_tasks_started = False

    async def __call__(self, scope, receive, send):
        # Start background tasks only once when first request comes in
        if not self._background_tasks_started:
            self._background_tasks_started = True
            # Create the background task
            asyncio.create_task(send_breaking_news_to_channel())

        return await self.application(scope, receive, send)


# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import WebSocket routing after Django initialization
try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from channels.auth import AuthMiddlewareStack
    from tetra.routing import websocket_urlpatterns

    # Configure ASGI application with WebSocket support
    application = TetraASGIApplication(
        ProtocolTypeRouter(
            {
                "http": django_asgi_app,
                "websocket": AllowedHostsOriginValidator(
                    AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
                ),
            }
        )
    )

except ImportError:
    # Channels not installed - fall back to HTTP-only ASGI app
    print(
        "Warning: Django Channels not installed. Push notifications will not be available."
    )
    print("Install with: pip install -e tetra[realtime]")
    application = django_asgi_app
