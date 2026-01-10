from django.conf.urls.static import static
from django.urls import path, include
from django.conf import settings

urlpatterns = [
    path("__tetra__", include("tetra.urls")),
    path("main/", include("apps.main.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
