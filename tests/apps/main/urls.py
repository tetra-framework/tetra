from django.urls import path, include

urlpatterns = [
    path("", include("tetra.tests.urls")),
]
