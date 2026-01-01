from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from tests.apps.main.views import (
    simple_basic_component_with_css,
    render_component_view,
)


urlpatterns = [
    path("__tetra__", include("tetra.urls")),
    path(
        "simple_basic_component_with_css",
        simple_basic_component_with_css,
        name="simple_basic_component_with_css",
    ),
    path(
        "render_component_view",
        render_component_view,
        name="render_component_view",
    ),
    path("main/", include("tests.apps.main.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
