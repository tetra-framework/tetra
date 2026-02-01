from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    custom_field = models.CharField(max_length=100, default="default")

    class Meta:
        app_label = "another_app"
