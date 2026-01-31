from django.db import models
from tetra.models import ReactiveModel


class SimpleModel(models.Model):
    """Simple model for testing purposes."""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<SimpleModel: {self.name}, {self.created_at}>"


class WatchableModel(ReactiveModel):
    name = models.CharField(max_length=100)

    class Tetra:
        fields = "__all__"


class AwareDateTimeModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<AwareDateTimeModel: {self.name}, {self.created_at}>"
