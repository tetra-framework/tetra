from django.core.checks import Error, Warning, register, Tags
from django.conf import settings


@register(Tags.compatibility)
def check_websocket_support(app_configs, **kwargs):
    """
    Check if WebSocket support is properly configured for Tetra reactive components.

    The checks are only executed if there is demand for websockets - if any app
    declares a ReactiveComponent.
    """
    errors = []

    from tetra.globals import has_reactive_components

    # Only check if reactive components are being used
    if not has_reactive_components():
        return errors

    # Check if Channels is installed
    try:
        import channels
    except ImportError:
        errors.append(
            Error(
                "Django Channels is required for Tetra reactive components.",
                hint="Install channels: pip install channels",
                id="tetra.E001",
            )
        )
        return errors

    # Check ASGI_APPLICATION setting
    if not hasattr(settings, "ASGI_APPLICATION"):
        errors.append(
            Error(
                "ASGI_APPLICATION setting is required for WebSocket support.",
                hint="Add ASGI_APPLICATION = 'your_project.asgi.application' to settings.py",
                id="tetra.E002",
            )
        )
        return errors

    # Check if ASGI application exists and supports WebSockets
    asgi_app_path = getattr(settings, "ASGI_APPLICATION", None)
    if not asgi_app_path:
        errors.append(
            Error(
                "ASGI_APPLICATION setting is empty.",
                id="tetra.E003",
            )
        )
        return errors

    try:
        from django.utils.module_loading import import_string

        asgi_app = import_string(asgi_app_path)

        if not _has_websocket_support(asgi_app):
            errors.append(
                Warning(
                    "ASGI application does not appear to support WebSockets.",
                    hint="Ensure your ASGI application includes WebSocket routing for Tetra.",
                    id="tetra.W001",
                )
            )
    except (ImportError, AttributeError) as e:
        errors.append(
            Error(
                f"Cannot import ASGI application: {e}",
                hint=f"Check that '{asgi_app_path}' is correct and importable.",
                id="tetra.E004",
            )
        )

    # Check channel layer configuration
    try:
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            errors.append(
                Error(
                    "No channel layer configured.",
                    hint="Configure CHANNEL_LAYERS in settings.py for WebSocket support.",
                    id="tetra.E005",
                )
            )
    except Exception as e:
        errors.append(
            Warning(
                f"Channel layer configuration issue: {e}",
                id="tetra.W003",
            )
        )

    return errors


def _has_websocket_support(asgi_app) -> bool:
    """Check if an ASGI application supports WebSockets."""
    from channels.routing import ProtocolTypeRouter, URLRouter

    # Direct ProtocolTypeRouter check
    if isinstance(asgi_app, ProtocolTypeRouter):
        return "websocket" in asgi_app.application_mapping

    # Check for wrapped applications
    if hasattr(asgi_app, "application") or hasattr(asgi_app, "app"):
        wrapped_app = getattr(asgi_app, "application", None) or getattr(
            asgi_app, "app", None
        )
        if wrapped_app and wrapped_app != asgi_app:
            return _has_websocket_support(wrapped_app)

    return False
