from django.apps import AppConfig


class AnotherAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tests.apps.another_app"
    label = "another_app"
