import pytest
import json
from unittest.mock import patch, AsyncMock
from apps.main.models import WatchableModel
from tetra.models import ReactiveModel
from django.db import models


@pytest.mark.django_db
def test_reactive_model_mixin_save():
    with (
        patch(
            "tetra.dispatcher.ComponentDispatcher.data_changed", new_callable=AsyncMock
        ) as mock_data_changed,
        patch(
            "tetra.dispatcher.ComponentDispatcher.component_created",
            new_callable=AsyncMock,
        ) as mock_component_created,
    ):
        # Create instance
        obj = WatchableModel.objects.create(name="Test")

        # Check if component_created was called once for the collection
        assert mock_component_created.call_count == 1
        assert mock_component_created.call_args[0][0] == "main.watchablemodel"

        # Now update it
        obj.name = "Updated"
        obj.save()

        # Check if data_changed was called once for the instance
        assert mock_data_changed.call_count == 1
        assert mock_data_changed.call_args[0][0] == f"main.watchablemodel.{obj.pk}"


def test_metaclass_conflict():
    # Test if we can combine ReactiveModelMixin with another model that has its own metaclass
    # or just another model in general.
    from django.db import models
    from tetra.models import ReactiveModel

    class OtherMixin(models.Model):
        class Meta:
            abstract = True

    try:

        class ComplexModel(ReactiveModel, OtherMixin):
            name = models.CharField(max_length=100)

            class Tetra:
                fields = ["name"]

            class Meta:
                app_label = "main"

    except TypeError as e:
        pytest.fail(f"Metaclass conflict detected: {e}")


@pytest.mark.django_db
def test_reactive_model_mixin_delete():
    obj = WatchableModel.objects.create(name="Test")
    pk = obj.pk

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_removed", new_callable=AsyncMock
    ) as mock_remove:
        obj.delete()

        # Check if component_removed was called twice:
        # 1. for instance channel
        # 2. for collection channel with target_group
        assert mock_remove.call_count == 2

        calls = mock_remove.call_args_list
        # Call 1: instance channel
        assert calls[0].args[0] == f"main.watchablemodel.{pk}"
        assert calls[0].kwargs["component_id"] is None

        # Call 2: collection channel with target_group
        assert calls[1].args[0] == "main.watchablemodel"
        assert calls[1].kwargs["target_group"] == f"main.watchablemodel.{pk}"


@pytest.mark.django_db
def test_reactive_model_mixin():
    class DecoratedModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)

        class Meta:
            app_label = "main"
            managed = False

    with (
        patch(
            "tetra.dispatcher.ComponentDispatcher.data_changed", new_callable=AsyncMock
        ) as mock_data_changed,
        patch(
            "tetra.dispatcher.ComponentDispatcher.component_created",
            new_callable=AsyncMock,
        ) as mock_component_created,
    ):
        # Instead of creating a real object, we use a mock that looks like the model
        obj = DecoratedModel(name="Test", pk=1)
        DecoratedModel._handle_tetra_save(DecoratedModel, obj, created=True)

        assert mock_data_changed.call_count == 0  # created=True calls component_created
        assert mock_component_created.call_count == 1
        group = mock_component_created.call_args[0][0]
        assert group == "main.decoratedmodel"

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_removed", new_callable=AsyncMock
    ) as mock_remove:
        DecoratedModel._handle_tetra_delete(DecoratedModel, obj)
        # Should be called twice (instance and collection)
        assert mock_remove.call_count == 2
        assert mock_remove.call_args_list[0].args[0] == "main.decoratedmodel.1"
        assert mock_remove.call_args_list[1].args[0] == "main.decoratedmodel"
        assert (
            mock_remove.call_args_list[1].kwargs["target_group"]
            == "main.decoratedmodel.1"
        )


@pytest.mark.django_db
def test_reactive_model_mixin_custom_channel():
    class CustomDecoratedModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)

        def get_tetra_instance_channel(self):
            return "custom_channel"

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.data_changed", new_callable=AsyncMock
    ) as mock_data_changed:
        obj = CustomDecoratedModel(name="Test", pk=1)
        CustomDecoratedModel._handle_tetra_save(
            CustomDecoratedModel, obj, created=False
        )

        assert mock_data_changed.call_count == 1
        group = mock_data_changed.call_args[0][0]
        assert group == "custom_channel"


@pytest.mark.django_db
def test_reactive_model_fields_filtering():
    class FilteredModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)
        password = models.CharField(max_length=100)

        class Tetra:
            fields = ["name"]

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_created", new_callable=AsyncMock
    ) as mock_component_created:
        obj = FilteredModel(name="TestUser", password="secretpassword", pk=1)
        FilteredModel._handle_tetra_save(FilteredModel, obj, created=True)

        assert mock_component_created.call_count == 1
        # Check that only 'name' and 'id' are in the data, and 'password' is excluded
        data = mock_component_created.call_args[1]["data"]
        assert "name" in data
        assert data["name"] == "TestUser"
        assert "id" in data
        assert data["id"] == 1
        assert "password" not in data


@pytest.mark.django_db
def test_reactive_model_mixin_fields_filtering():
    class DecoratedFilteredModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)
        secret = models.CharField(max_length=100)

        class Tetra:
            fields = ["name"]

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_created", new_callable=AsyncMock
    ) as mock_component_created:
        obj = DecoratedFilteredModel(name="Test", secret="hush", pk=1)
        DecoratedFilteredModel._handle_tetra_save(
            DecoratedFilteredModel, obj, created=True
        )

        assert mock_component_created.call_count == 1
        data = mock_component_created.call_args[1]["data"]
        assert "name" in data
        assert "id" in data
        assert data["id"] == 1
        assert "secret" not in data


@pytest.mark.django_db
def test_reactive_model_all_fields():
    class AllFieldsModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)
        age = models.IntegerField()

        class Tetra:
            fields = "__all__"

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_created", new_callable=AsyncMock
    ) as mock_component_created:
        obj = AllFieldsModel(name="All", age=30, pk=1)
        AllFieldsModel._handle_tetra_save(AllFieldsModel, obj, created=True)

        assert mock_component_created.call_count == 1
        data = mock_component_created.call_args[1]["data"]
        assert data == {"id": 1, "name": "All", "age": 30, "model_version": 0}
