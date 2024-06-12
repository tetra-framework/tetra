from django.db import models


class SimpleModel(models.Model):
    """Simple model for testing purposes."""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)


class AwareDateTimeModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
