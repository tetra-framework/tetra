from django.shortcuts import render
from .utils import prepopulate_session_to_do


def home(request):
    prepopulate_session_to_do(request)
    return render(request, "index.html")
