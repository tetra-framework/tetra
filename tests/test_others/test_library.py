from django.apps import apps

from tetra import Library


def test_create_library(current_app):
    """simply create a library and make sure it exists"""
    lib = Library("lib1", app=current_app)
    assert lib is not None


def test_create_library_with_str_app(current_app):
    """create a lib and register a component manually and make sure it exists in the library"""
    lib2 = Library("lib2", current_app.label)
    assert lib2 is not None


def test_create_library_twice(current_app):
    """creates a library twice and makes sure they are the same instance"""
    lib = Library("default", app=current_app)
    samelib = Library("default", app=current_app)
    assert lib is samelib

    # create library with the same name but different app - must fail
    otherlibname = Library("other", app=current_app)
    assert lib is not otherlibname

    otherlibapp = Library("other", app=apps.get_app_config("another_app"))
    assert lib is not otherlibapp
