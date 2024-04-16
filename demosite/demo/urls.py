from django.urls import path
from .views import home, examples


urlpatterns = [
    path("", home, name="home"),
    path("examples/", examples, name="examples-home"),
    path("examples/<slug:slug>/", examples, name="examples"),
]
