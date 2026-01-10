from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from tetra.helpers import render_component_tag


@csrf_exempt
def render_component_view(request):
    """
    A django tester view that dynamically creates a HttpResponse from a component tag.

    This function is used by the Tetra testing framework, and can be used via the
    `component_locator` fixture.
    """
    component_tag = request.GET.get("component_tag")
    return HttpResponse(render_component_tag(request, component_tag))
