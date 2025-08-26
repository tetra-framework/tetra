from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns


urlpatterns = i18n_patterns(
    path("admin/", admin.site.urls),
    path("", include("demo.urls")),
    prefix_default_language=False,  # Remove the prefix for the default language
)

# The language switcher URL should not be prefixed.
urlpatterns += [
    path("i18n/", include("django.conf.urls.i18n")),
    path("tetra/", include("tetra.urls")),
]
