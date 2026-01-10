from django.urls import path

from .views import render_component_view

urlpatterns = [
    path(
        "render_component_view",
        render_component_view,
        name="render_component_view",
    ),
]
