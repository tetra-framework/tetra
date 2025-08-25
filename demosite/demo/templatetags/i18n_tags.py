from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag(takes_context=True)
def translate_url(context, target_language: str):
    """
    Given a language code, returns the absolute path of the current page
    in that language.
    Preserves the query string.
    """
    full_path = context["request"].get_full_path()

    # Split the path to separate the language prefix from the rest
    path_parts = full_path.lstrip("/").split("/", 1)

    # Check if the first part is a valid language code
    is_prefixed = path_parts[0] in [lang[0] for lang in settings.LANGUAGES]

    if is_prefixed:
        # The current URL is prefixed, e.g., /es/some/path/
        base_path = path_parts[1] if len(path_parts) > 1 else ""
    else:
        # The current URL is not prefixed (it's the default language)
        base_path = full_path.lstrip("/")

    if (
        target_language == settings.LANGUAGE_CODE
        and not settings.PREFIX_DEFAULT_LANGUAGE
    ):
        return "/" + base_path
    else:
        return f"/{target_language}/{base_path}"
