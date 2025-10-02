from django.contrib import admin
from .models import ToDo


class ToDoAdmin(admin.ModelAdmin):
    list_display = ("title", "done", "added", "modified", "session_key")
    list_filter = ["session_key", "title", "done"]


admin.site.register(ToDo, ToDoAdmin)
