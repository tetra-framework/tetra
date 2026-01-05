from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings
from apps.main.views import (
    render_component_view,
)


urlpatterns = [
    path("__tetra__", include("tetra.urls")),
    path(
        "render_component_view",
        render_component_view,
        name="render_component_view",
    ),
    path("main/", include("apps.main.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
