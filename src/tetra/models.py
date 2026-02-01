import asyncio

from django.db import models
from django.db.models.base import Model
from django.db.models.signals import post_save, post_delete
from asgiref.sync import async_to_sync
from .dispatcher import ComponentDispatcher
from .utils import request_id


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

    # used to resolve version conflicts by concurrent client updates
    model_version = models.PositiveBigIntegerField(default=0)

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

    def save(self, *args, **kwargs):
        """Override save to auto-increment model_version"""
        # Increment version on every save
        if self.pk:  # Only increment if updating existing object
            self.model_version += 1
        super().save(*args, **kwargs)

    @classmethod
    def _handle_tetra_save(cls, sender, instance, created, **kwargs):
        """
        Handle save event for Tetra model instances, updating the instance and collection channels.

        This is called both on `create` and `update`.
        """
        instance_channel = instance.get_tetra_instance_channel()
        collection_channel = instance.get_tetra_collection_channel()
        data = instance.get_tetra_update_data()
        # Always include model_version for deduplication
        data["model_version"] = instance.model_version
        sender_id = request_id.get()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            if created:
                loop.create_task(
                    ComponentDispatcher.component_created(
                        collection_channel, data=data, sender_id=sender_id
                    )
                )
            else:
                loop.create_task(
                    ComponentDispatcher.data_changed(
                        instance_channel, data, sender_id=sender_id
                    )
                )
        else:

            if created:
                async_to_sync(ComponentDispatcher.component_created)(
                    collection_channel, data=data, sender_id=sender_id
                )
            else:
                async_to_sync(ComponentDispatcher.data_changed)(
                    instance_channel, data, sender_id=sender_id
                )

    @classmethod
    def _handle_tetra_delete(cls, sender, instance, **kwargs):
        """
        Handle delete event for Tetra model instances, removing the instance and collection channels.
        """
        channel = instance.get_tetra_instance_channel()
        collection_channel = instance.get_tetra_collection_channel()
        sender_id = request_id.get()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        # Send data to the collection channel and the instance channel
        if loop and loop.is_running():
            loop.create_task(
                ComponentDispatcher.component_removed(
                    channel, component_id=None, sender_id=sender_id
                )
            )
            loop.create_task(
                ComponentDispatcher.component_removed(
                    collection_channel, target_group=channel, sender_id=sender_id
                )
            )
        else:
            async_to_sync(ComponentDispatcher.component_removed)(
                channel, component_id=None, sender_id=sender_id
            )
            async_to_sync(ComponentDispatcher.component_removed)(
                collection_channel, target_group=channel, sender_id=sender_id
            )

    def get_tetra_instance_channel(self) -> str:
        """Returns the channel name to be used for this model instance.

        Returns:
            as default "{app_label}.{model_name}.{pk}"
        """
        return f"{self._meta.app_label}.{self._meta.model_name}.{self.pk}"

    def get_tetra_collection_channel(self) -> str:
        """Returns the channel name for the collection of this model type.

        Returns:
            as default "{app_label}.{model_name}"
        """
        return f"{self._meta.app_label}.{self._meta.model_name}"

    def get_tetra_update_data(self):
        """Returns the data to be sent to components."""
        # By default, we only include fields specified in `Tetra.fields`.
        # This is for security reasons, to avoid sending sensitive data
        # like passwords to the client.
        # If `Tetra.fields` is not defined or is empty, we return an empty dict
        # which triggers a refresh of public properties on the client.

        config = self.__tetra_config
        data = {"id": self.pk}
        if not config:
            return data

        fields = getattr(config, "fields", [])

        if fields == "__all__":
            # Send all model fields
            for field in self._meta.fields:
                data[field.name] = getattr(self, field.name)
            return data

        if fields:
            for field_name in fields:
                if hasattr(self, field_name):
                    data[field_name] = getattr(self, field_name)
            return data

        return data
