from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from demo import views as demo_views

urlpatterns = [
    path("", demo_views.home),
    path("docs/", include("docs.urls")),
    path("admin/", admin.site.urls),
    path("tetra/", include("tetra.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
