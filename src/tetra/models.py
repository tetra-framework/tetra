from django.db import models
from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete
from asgiref.sync import async_to_sync
from .dispatcher import ComponentDispatcher


class ReactiveModel(models.Model):
    """
    Abstract Django model to automatically send updates to Tetra components.

    Usage:
    ```python
    class MyModel(TetraReactiveModel):
        class Tetra:
            fields = ["name"]
        name = models.Charfield(...)
        password = models.CharField(...)  # not sent!
    ```
    """

    class Meta:
        abstract = True

    __tetra_config: type = None

    def __init_subclass__(cls: type[Model], **kwargs):
        super().__init_subclass__(**kwargs)
        # Look for the Tetra inner class
        tetra_config = getattr(cls, "Tetra", None)
        if tetra_config:
            cls.__tetra_config = tetra_config
        elif not hasattr(cls, "__tetra_config"):
            # Create a default config if not present
            class DefaultTetra:
                fields = []

            cls.__tetra_config = DefaultTetra

        cls._connect_tetra_signals()

    @classmethod
    def _connect_tetra_signals(cls):
        # set a global flag to indicate that reactive components are in use
        # this is necessary for the middleware to include the websocket scripts
        from django.apps import apps
        from .utils import check_websocket_support

        if check_websocket_support():
            apps.get_app_config("tetra").has_reactive_components = True

        # Check if signals are already connected to avoid duplicates
        # Using dispatch_uid is a good way to ensure unique connections.
        uid_save = f"tetra_save_{cls.__module__}.{cls.__name__}"
        uid_delete = f"tetra_delete_{cls.__module__}.{cls.__name__}"
        post_save.connect(cls._handle_tetra_save, sender=cls, dispatch_uid=uid_save)
        post_delete.connect(
            cls._handle_tetra_delete, sender=cls, dispatch_uid=uid_delete
        )

    @classmethod
    def _handle_tetra_save(cls, sender, instance, created, **kwargs):
        channel = instance.get_tetra_channel()
        data = instance.get_tetra_update_data()
        async_to_sync(ComponentDispatcher.update_data)(channel, data)

    @classmethod
    def _handle_tetra_delete(cls, sender, instance, **kwargs):
        channel = instance.get_tetra_channel()
        async_to_sync(ComponentDispatcher.component_remove)(channel, {})

    def get_tetra_channel(self) -> str:
        """Returns the channel name to be used for this model instance."""
        # Generates "model.<model_name>.<pk>"
        app_label = self._meta.app_label
        return f"{app_label}.{self._meta.model_name}.{self.pk}"

    def get_tetra_update_data(self):
        """Returns the data to be sent to components."""
        # By default, we only include fields specified in `Tetra.fields`.
        # This is for security reasons, to avoid sending sensitive data
        # like passwords to the client.
        # If `Tetra.fields` is not defined or is empty, we return an empty dict
        # which triggers a refresh of public properties on the client.

        config = self.__tetra_config
        if not config:
            return {}

        fields = getattr(config, "fields", [])

        if fields == "__all__":
            # Send all model fields
            data = {}
            for field in self._meta.fields:
                data[field.name] = getattr(self, field.name)
            return data

        if fields:
            data = {}
            for field_name in fields:
                if hasattr(self, field_name):
                    data[field_name] = getattr(self, field_name)
            return data

        return {}
