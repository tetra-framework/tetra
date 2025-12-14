
from django.urls import path
from .consumers import TetraConsumer

websocket_urlpatterns = [
    path("ws/tetra/", TetraConsumer.as_asgi()),
]
