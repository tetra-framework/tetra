import pytest
from django.db import models
from django.db.models.fields.files import FieldFile
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser
from tetra import Library
from tetra.components.base import Component
from tetra.state import encode_component

my_lib = Library("test_fieldfile", "main")


class FieldFileModel(models.Model):
    file = models.FileField(upload_to="test_fieldfile/")

    class Meta:
        app_label = "main"


@my_lib.register
class FieldFileComponent(Component):
    template = "<div></div>"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.my_file = None


def get_request_with_session():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()
    return request


@pytest.mark.django_db
def test_fieldfile_serialization_cycle():
    """Verify that FieldFile can be pickled and unpickled through Tetra's state system."""
    request = get_request_with_session()

    # 1. Create a model instance and a FieldFile
    obj = FieldFileModel.objects.create()
    obj.file.name = "test_file.txt"
    obj.save()

    # 2. Setup component with FieldFile
    comp = FieldFileComponent(request)
    comp.my_file = obj.file

    # 3. Encode state (Pickling)
    encoded_state = encode_component(comp)

    # 4. Decode state (Unpickling)
    # Component.from_state handles the unpickling of the encrypted state
    state_dict = {"encrypted": encoded_state, "data": {"key": comp.key}}
    resumed_comp = FieldFileComponent.from_state(state_dict, request)

    # 5. Verify
    assert resumed_comp.my_file is not None
    assert isinstance(resumed_comp.my_file, FieldFile)
    assert resumed_comp.my_file.name == "test_file.txt"
    assert resumed_comp.my_file.instance.pk == obj.pk
    assert resumed_comp.my_file.field.name == "file"


@pytest.mark.django_db
def test_fieldfile_unpickle_deleted_instance():
    """Verify that unpickling a FieldFile for a deleted model instance returns None gracefully."""
    request = get_request_with_session()

    obj = FieldFileModel.objects.create()
    obj.file.name = "deleted.txt"
    obj.save()
    pk = obj.pk

    comp = FieldFileComponent(request)
    comp.my_file = obj.file
    encoded_state = encode_component(comp)

    # Delete the instance
    obj.delete()

    # Resume component
    state_dict = {"encrypted": encoded_state, "data": {"key": comp.key}}
    resumed_comp = FieldFileComponent.from_state(state_dict, request)

    # It should be None because the instance doesn't exist
    assert resumed_comp.my_file is None
