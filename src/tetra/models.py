import asyncio
import re
from typing import Any

from django.db import models
from django.db.models.signals import post_save, post_delete, class_prepared
from asgiref.sync import async_to_sync
from .dispatcher import ComponentDispatcher
from .utils import request_id
from .registry import channels_group_registry


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

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not check_websocket_support():
            raise RuntimeError(
                f"{cls.__name__} is a reactive model, but WebSockets are not "
                f"supported. "
            )
        # Look for the Tetra inner class
        tetra_config = getattr(cls, "Tetra", None)
        if tetra_config:
            cls.__tetra_config = tetra_config
        elif not hasattr(cls, "__tetra_config"):
            # Create a default config if not present
            class DefaultTetra:
                fields = []

            cls.__tetra_config = DefaultTetra

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
        collection_channel = sender.get_tetra_collection_channel()
        data = instance.get_tetra_update_data()
        # Always include model_version for deduplication
        data["model_version"] = instance.model_version
        sender_id = request_id.get()
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
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
        except RuntimeError:

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

        # Send data to the collection channel and the instance channel
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
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
        except RuntimeError:
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

    @classmethod
    def get_tetra_collection_channel(cls) -> str:
        """Returns the channel name for the collection of this model type.

        Returns:
            as default "{app_label}.{model_name}"
        """
        return f"{cls._meta.app_label}.{cls._meta.model_name}"

    def get_tetra_update_data(self) -> dict[str, Any]:
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
        data = {"id": self.pk}

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

        return {}


# this is necessary, as ReactiveModel is an AbstractModel where __init_subclass__()
# is notworking as expected (subclasses have no access to their ._meta at this point)
def _reactivemodel_class_prepared(sender: type[ReactiveModel], **kwargs):
    if issubclass(sender, ReactiveModel) and not sender._meta.abstract:
        from django.apps import apps
        from .utils import check_websocket_support

        app_label = sender._meta.app_label
        model_name = sender._meta.model_name
        # Register collection group
        channels_group_registry.register(sender.get_tetra_collection_channel())
        # Register instance group pattern
        channels_group_registry.register(
            re.compile(rf"^{app_label}\.{model_name}\..+$")
        )

        # set a global flag to indicate that reactive components are in use
        # this is necessary for the middleware to include the websocket scripts
        if check_websocket_support():
            apps.get_app_config("tetra").has_reactive_components = True

        # Check if signals are already connected to avoid duplicates
        # Using dispatch_uid is a good way to ensure unique connections.
        uid_save = f"tetra_save_{sender.__module__}.{sender.__name__}"
        uid_delete = f"tetra_delete_{sender.__module__}.{sender.__name__}"
        post_save.connect(
            sender._handle_tetra_save, sender=sender, dispatch_uid=uid_save
        )
        post_delete.connect(
            sender._handle_tetra_delete, sender=sender, dispatch_uid=uid_delete
        )


class_prepared.connect(_reactivemodel_class_prepared)
