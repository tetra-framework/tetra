from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from tests.main.views import simple_basic_component_with_css


urlpatterns = [
    path("__tetra__", include("tetra.urls")),
    path(
        "simple_basic_component_with_css",
        simple_basic_component_with_css,
        name="simple_basic_component_with_css",
    ),
    path("main/", include("tests.main.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
