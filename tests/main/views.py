from django.http import HttpResponse

from tests.main.helpers import render_component_tag


def simple_basic_component_with_css(request):
    return HttpResponse(
        render_component_tag(request, "{% SimpleBasicComponentWithCSS / %}")
    )


def component_with_return_value(request):
    return HttpResponse(
        render_component_tag(request, "{% ui.ComponentWithMethodReturnValue / %}")
    )


def component_with_button(request):
    return HttpResponse(render_component_tag(request, "{% ui.ComponentWithButton / %}"))


def download_component(request):
    return HttpResponse(render_component_tag(request, "{% ui.DownloadComponent / %}"))
