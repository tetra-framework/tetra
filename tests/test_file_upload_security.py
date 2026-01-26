import os
import pytest
from django.conf import settings
from django.test import RequestFactory
from tetra import Library, public
from tetra.utils import to_json, from_json, NamedTemporaryUploadedFile
from tetra.components.base import Component, FormComponent
from django import forms
from tetra.state import encode_component

my_lib = Library("reproduce", "main")


class SimpleForm(forms.Form):
    my_file = forms.FileField()


@my_lib.register
class FileComponent(FormComponent):
    form_class = SimpleForm
    template = "<div>{{ form.my_file }}</div>"


from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.models import AnonymousUser


@pytest.mark.django_db
def test_reproduce_file_leak():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()

    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()

    # 1. Simulate User A uploading a file
    file_a = NamedTemporaryUploadedFile(
        name="user_a_private.txt", content_type="text/plain", size=13, charset="utf-8"
    )
    with open(file_a.file.name, "wb") as f:
        f.write(b"hello user a")
    path_a = file_a.file.name

    # 2. User B (attacker) starts their own session
    comp_b = FileComponent(request)
    # Initial state for User B
    encrypted_state_b = encode_component(comp_b)

    # 3. User B sends a malicious request claiming User A's file
    # They craft the 'data' part of the component state
    malicious_data = {
        "my_file": {
            "__type": "file",
            "name": "user_a_private.txt",
            "size": 13,
            "content_type": "text/plain",
            "temp_path": path_a,
        },
        "key": comp_b.key,
    }

    component_state = {"encrypted": encrypted_state_b, "data": malicious_data}

    # Now simulate Component.from_state which is called in views.py
    # We use to_json/from_json to simulate the transport
    transported_state = from_json(to_json(component_state))

    # This is what views.py does:
    resumed_comp = FileComponent.from_state(transported_state, request)

    # Check if the resumed component now has User A's file
    # IT SHOULD NOT!
    assert resumed_comp.my_file is None

    # Check if it renders the filename in the form
    rendered = resumed_comp.render()
    assert "user_a_private.txt" not in rendered


@pytest.mark.django_db
def test_legit_file_persistence():
    rf = RequestFactory()
    request = rf.get("/")
    request.user = AnonymousUser()

    # Add session
    middleware = SessionMiddleware(lambda r: None)
    middleware.process_request(request)
    request.session.save()

    # 1. User uploads a file
    file_legit = NamedTemporaryUploadedFile(
        name="legit.txt", content_type="text/plain", size=5, charset="utf-8"
    )
    with open(file_legit.file.name, "wb") as f:
        f.write(b"legit")
    path_legit = file_legit.file.name

    # 2. Component is created with this file
    comp = FileComponent(request)
    comp.my_file = file_legit
    encrypted_state = encode_component(comp)

    # 3. Next request: client sends back the state
    client_data = {
        "my_file": {
            "__type": "file",
            "name": "legit.txt",
            "size": 5,
            "content_type": "text/plain",
            # temp_path is MISSING as it's not in client JSON anymore
        },
        "key": comp.key,
    }

    component_state = {"encrypted": encrypted_state, "data": client_data}

    transported_state = from_json(to_json(component_state))
    resumed_comp = FileComponent.from_state(transported_state, request)

    # IT SHOULD PERSIST THE FILE!
    assert resumed_comp.my_file is not None
    assert resumed_comp.my_file.name == "legit.txt"
    assert resumed_comp.my_file.temporary_file_path() == path_legit
    print("SUCCESS: Legit file persistence works!")


if __name__ == "__main__":
    # This is just to allow running it directly if needed
    pass
