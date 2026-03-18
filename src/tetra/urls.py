from django.urls import path
from . import views

app_name = "tetra"

urlpatterns = [
    path("call/", views.component_method, name="component-call"),
    path("navigate/", views.navigate, name="navigate"),
]
