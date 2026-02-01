import pytest
import json
from unittest.mock import patch, AsyncMock
from apps.main.models import WatchableModel
from tetra.models import ReactiveModel
from django.db import models


@pytest.mark.django_db
def test_reactive_model_mixin_save():
    with patch(
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        # Create instance
        obj = WatchableModel.objects.create(name="Test")

        # Check if update_data was called
        # It should be called once for model.watchablemodel.{pk}
        assert mock_update_data.call_count == 1

        calls = mock_update_data.call_args_list
        group = calls[0].args[0]
        assert group == f"main.watchablemodel.{obj.pk}"
        # WatchableModel now has fields = "__all__"
        assert calls[0].args[1]["name"] == "Test"


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
        "tetra.dispatcher.ComponentDispatcher.component_remove", new_callable=AsyncMock
    ) as mock_remove:
        obj.delete()

        # Check if component_remove was called
        assert mock_remove.call_count == 1

        calls = mock_remove.call_args_list
        group = calls[0].args[0]
        assert group == f"main.watchablemodel.{pk}"
        assert calls[0].kwargs["component_id"] is None


@pytest.mark.django_db
def test_reactive_model_mixin():
    class DecoratedModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        # Instead of creating a real object, we use a mock that looks like the model
        obj = DecoratedModel(name="Test", pk=1)
        DecoratedModel._handle_tetra_save(DecoratedModel, obj, created=True)

        assert mock_update_data.call_count == 1
        group = mock_update_data.call_args[0][0]
        assert group == "main.decoratedmodel.1"

    with patch(
        "tetra.dispatcher.ComponentDispatcher.component_remove", new_callable=AsyncMock
    ) as mock_remove:
        DecoratedModel._handle_tetra_delete(DecoratedModel, obj)
        assert mock_remove.call_count == 1


@pytest.mark.django_db
def test_reactive_model_mixin_custom_channel():
    class CustomDecoratedModel(ReactiveModel, models.Model):
        name = models.CharField(max_length=100)

        def get_tetra_channel(self):
            return "custom_channel"

        class Meta:
            app_label = "main"
            managed = False

    with patch(
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        obj = CustomDecoratedModel(name="Test", pk=1)
        CustomDecoratedModel._handle_tetra_save(CustomDecoratedModel, obj, created=True)

        assert mock_update_data.call_count == 1
        group = mock_update_data.call_args[0][0]
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
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        obj = FilteredModel(name="TestUser", password="secretpassword", pk=1)
        FilteredModel._handle_tetra_save(FilteredModel, obj, created=True)

        assert mock_update_data.call_count == 1
        # Check that only 'name' is in the data, and 'password' is excluded
        data = mock_update_data.call_args[0][1]
        assert "name" in data
        assert data["name"] == "TestUser"
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
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        obj = DecoratedFilteredModel(name="Test", secret="hush", pk=1)
        DecoratedFilteredModel._handle_tetra_save(
            DecoratedFilteredModel, obj, created=True
        )

        assert mock_update_data.call_count == 1
        data = mock_update_data.call_args[0][1]
        assert "name" in data
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
        "tetra.dispatcher.ComponentDispatcher.update_data", new_callable=AsyncMock
    ) as mock_update_data:
        obj = AllFieldsModel(name="All", age=30, pk=1)
        AllFieldsModel._handle_tetra_save(AllFieldsModel, obj, created=True)

        assert mock_update_data.call_count == 1
        data = mock_update_data.call_args[0][1]
        assert data == {"id": 1, "name": "All", "age": 30, "model_version": 0}
