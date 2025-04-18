from django.http import HttpResponse

from tests.main.helpers import render_component_tag


def simple_basic_component_with_css(request):
    return HttpResponse(
        render_component_tag(
            request, "{% @ main.default.SimpleBasicComponentWithCss / %}"
        )
    )


def component_with_return_value(request):
    return HttpResponse(
        render_component_tag(
            request, "{% @ main.default.ComponentWithMethodReturnValue / %}"
        )
    )


def download_component(request):
    return HttpResponse(
        render_component_tag(request, "{% @ main.ui.DownloadComponent / %}")
    )
