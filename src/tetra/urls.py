from django.urls import path
from . import views

app_name = "tetra"

urlpatterns = [
    path(
        "call/",
        views.component_method,
        name="component_call",
    ),
]
