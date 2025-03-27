from django.urls import path

from main import views

urlpatterns = [
    path(
        "component_with_return_value/",
        views.component_with_return_value,
        name="component_with_return_value",
    )
]
