from django.http import HttpResponse

from tests.apps.main.helpers import render_component_tag


def simple_basic_component_with_css(request):
    # TODO this is no UI component
    return HttpResponse(
        render_component_tag(request, "{% SimpleBasicComponentWithCSS / %}")
    )


def generic_ui_component_test_view(request, component_name):
    """Dynamically creates a HttpResponse from ui components"""
    return HttpResponse(
        render_component_tag(request, "{% " + f"ui.{component_name}" + " / %}")
    )
