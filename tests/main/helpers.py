from django.template import Template, Context


def render_component_tag(request, component_string):
    """Helper function to return a full html document with loaded Tetra stuff."""
    context = Context()
    context.request = request
    return Template(
        "{% load tetra %}<!doctype html>"
        "<html><head>"
        "{% tetra_styles %}"
        "{% tetra_scripts include_alpine=True %}"
        "</head><body>"
        f"{component_string}"
        "</body></html>"
    ).render(context)
