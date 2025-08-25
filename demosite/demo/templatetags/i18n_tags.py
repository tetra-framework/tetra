from django import template
from django.urls import resolve, reverse
from django.utils.translation import activate, get_language

register = template.Library()


@register.simple_tag(takes_context=True)
def translate_url(context, language: str):
    """
    Given a language code, returns the absolute path of the current page
    in that language.
    Preserves the query string.
    """
    path = context["request"].path
    resolver_match = resolve(path)

    current_language = get_language()
    try:
        activate(language)
        url = reverse(
            resolver_match.view_name,
            args=resolver_match.args,
            kwargs=resolver_match.kwargs,
        )
    finally:
        activate(current_language)

    if context["request"].GET:
        url += "?" + context["request"].GET.urlencode()

    return url
