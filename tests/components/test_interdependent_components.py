import pytest
from django.apps import apps
from tetra.component_register import find_component_libraries
from tetra.library import Library
from tetra.components.base import BasicComponent
import tetra.state


def test_interdependent_components_manual_simulation():
    """
    Simulates the interdependent component loading without re-scanning the whole project.
    We define classes inside the test to ensure they are defined while loading_libraries=True.
    """

    # Save original state
    orig_loading = tetra.state.loading_libraries
    orig_to_compile = BasicComponent._to_compile
    BasicComponent._to_compile = []

    try:
        tetra.state.loading_libraries = True

        test_lib = Library("test_simulation", "main")

        # Declaration and registering order matters. This will fail when tetra would
        # not postpone template rendering to after all components are registered:

        # first, declare the parent which includes anot yet available Child component
        class SimulationParent(BasicComponent):
            template = (
                """<div class="parent">{% test_simulation.SimulationChild / %}</div>"""
            )

        # then declare the child
        class SimulationChild(BasicComponent):
            template = """<div class="child">Child</div>"""

        # first, register the Parent
        test_lib.register(SimulationParent)
        # then the Child
        test_lib.register(SimulationChild)

        # Both should be in _to_compile and NOT have _template yet
        assert SimulationChild in BasicComponent._to_compile
        assert SimulationParent in BasicComponent._to_compile
        assert not hasattr(SimulationChild, "_template")
        assert not hasattr(SimulationParent, "_template")

        # Now finalize loading
        tetra.state.loading_libraries = False
        BasicComponent._compile_all_templates()

        # Now they should have templates
        assert hasattr(SimulationChild, "_template")
        assert hasattr(SimulationParent, "_template")

        # And Parent should be able to render Child
        from django.test import RequestFactory
        from tetra.middleware import TetraDetails
        from django.contrib.sessions.backends.cache import SessionStore
        from django.template import RequestContext
        from django.contrib.auth.models import AnonymousUser

        factory = RequestFactory()
        request = factory.get("/")
        request.session = SessionStore()
        request.session.create()
        request.user = AnonymousUser()
        request.tetra = TetraDetails(request)

        parent_instance = SimulationParent(request)
        context = RequestContext(request, {"component": parent_instance})
        rendered = parent_instance.render()

        assert '<div class="parent">' in rendered
        assert '<div class="child">Child</div>' in rendered

    finally:
        # Restore original state
        tetra.state.loading_libraries = orig_loading
        BasicComponent._to_compile = orig_to_compile
        # Clean up the library from registry to avoid side effects
        if "main" in Library.registry and "test_simulation" in Library.registry["main"]:
            del Library.registry["main"]["test_simulation"]


def test_interdependent_components_actual_load():
    """
    Verifies that the components in the 'spa' library (which are interdependent)
    were correctly loaded and compiled by the initial find_component_libraries call.
    """
    from tetra.library import Library
    import tetra.state
    from tetra.component_register import find_component_libraries

    # If registry was cleared by another test, we don't try to re-load it here
    # as it's too risky and complicated.
    # Instead we skip this part if it's not there.
    if "main" not in Library.registry or "spa" not in Library.registry["main"]:
        pytest.skip("Library registry was cleared by another test.")

    assert "main" in Library.registry
    assert "spa" in Library.registry["main"]

    spa_library = Library.registry["main"]["spa"]
    app_cls = spa_library.components["app"]
    input_button_cls = spa_library.components["input_button"]

    assert hasattr(app_cls, "_template")
    assert hasattr(input_button_cls, "_template")

    from django.test import RequestFactory
    from tetra.middleware import TetraDetails
    from django.contrib.sessions.backends.cache import SessionStore
    from django.template import RequestContext

    from django.contrib.auth.models import AnonymousUser

    factory = RequestFactory()
    request = factory.get("/")
    request.session = SessionStore()
    request.session.create()
    request.user = AnonymousUser()
    request.tetra = TetraDetails(request)

    app_instance = app_cls(request)
    context = RequestContext(request, {"component": app_instance})
    rendered = app_instance._template.render(context)

    assert "<h1>App Component</h1>" in rendered
    assert '<button @click="click()">Click Me</button>' in rendered
