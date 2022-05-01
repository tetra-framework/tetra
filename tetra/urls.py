from django.urls import path
from . import views

urlpatterns = [
    path(
        "<str:app_name>/<str:library_name>/<str:component_name>/<str:method_name>",
        views.component_method,
        name="tetra_public_component_method",
    ),
]
