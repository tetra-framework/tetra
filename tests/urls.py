from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from tests.apps.main.views import (
    simple_basic_component_with_css,
    generic_ui_component_test_view,
)


urlpatterns = [
    path("__tetra__", include("tetra.urls")),
    path(
        "simple_basic_component_with_css",
        simple_basic_component_with_css,
        name="simple_basic_component_with_css",
    ),
    path(
        "generic_ui_component_test_view/<component_name>",
        generic_ui_component_test_view,
        name="generic_ui_component_test_view",
    ),
    path("main/", include("tests.apps.main.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
