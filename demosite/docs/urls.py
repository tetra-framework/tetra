from django.urls import path
from docs import views

urlpatterns = [
    path("", views.doc, name="docs-home"),
    path("<slug:slug>", views.doc, name="doc"),
]
