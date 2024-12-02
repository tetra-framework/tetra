from django.db import models


class SimpleModel(models.Model):
    """Simple model for testing purposes."""

    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<SimpleModel: {self.name}, {self.created_at}>"


class AwareDateTimeModel(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return f"<AwareDateTimeModel: {self.name}, {self.created_at}>"
