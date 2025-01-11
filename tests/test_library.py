from django.apps import apps

from tetra import Library


def test_create_library(current_app):
    """simply create a library and make sure it exists"""
    lib = Library("default", app=current_app)
    assert lib is not None


def test_create_library_twice(current_app):
    """creates a library twice and makes sure they are the same instance"""
    lib = Library("default", app=current_app)
    samelib = Library("default", app=current_app)
    assert lib is samelib

    otherlibname = Library("other", app=current_app)
    assert lib is not otherlibname

    otherlibapp = Library("other", app=apps.get_app_config("another_app"))
    assert lib is not otherlibapp
