from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from apps.main.helpers import render_component_tag


def simple_basic_component_with_css(request):
    # TODO this is no UI component
    return HttpResponse(
        render_component_tag(request, "{% SimpleBasicComponentWithCSS / %}")
    )


@csrf_exempt
def render_component_view(request):
    """Dynamically creates a HttpResponse from a component tag"""
    component_tag = request.GET.get("component_tag")
    return HttpResponse(render_component_tag(request, component_tag))
