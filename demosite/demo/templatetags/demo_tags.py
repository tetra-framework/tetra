from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.template.loaders.app_directories import Loader
import tetra


register = template.Library()


@register.simple_tag
def tetra_version():
    return tetra.__version__


@register.simple_tag
def include_source(file_name, start=None, end=None):
    error = None
    for origin in Loader(None).get_template_sources(file_name):
        try:
            with open(origin.name) as f:
                text = f.read()
                if (start is not None) or (end is not None):
                    text = "\n".join(text.split("\n")[start:end])
                return mark_safe(escape(text))
        except FileNotFoundError as e:
            error = e
            pass
    if error:
        raise error


@register.simple_tag
def include_source_part(file_name, part=0):
    error = None
    for origin in Loader(None).get_template_sources(file_name):
        try:
            with open(origin.name) as f:
                text = f.read().split("# SPLIT")
                text = text[part].rstrip().lstrip("\n")
                return mark_safe(escape(text))
        except FileNotFoundError as e:
            error = e
            pass
    if error:
        raise error
