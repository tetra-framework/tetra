import logging
import warnings

from django import template
from django.template.loader_tags import BlockNode, BLOCK_CONTEXT_KEY
from django.utils.safestring import mark_safe, SafeString
from uuid import uuid4
import re
import copy
from threading import local

from ..exceptions import ComponentError, ComponentNotFound
from ..component_register import resolve_component

logger = logging.getLogger(__name__)


class TetraTemplateTagException(Exception):
    pass


thread_local = local()
register = template.Library()


def get_nodes_by_type_deep(obj, node_type):
    thread_local.geting_nodes_by_type_deep = True
    node_list = obj.get_nodes_by_type(node_type)
    thread_local.geting_nodes_by_type_deep = False
    return node_list


@register.simple_tag(takes_context=True, name="tetra_scripts")
def scripts_placeholder_tag(context, include_alpine=False):
    placeholder = f"<!-- tetra scripts {uuid4()} -->"
    try:
        context.request.tetra_scripts_placeholder_string = placeholder.encode()
        context.request.tetra_scripts_placeholder_include_alpine = include_alpine
    except AttributeError:
        raise TetraTemplateTagException(
            '{% tetra_scripts %} tag requires "request" in the template context.'
        )
    return mark_safe(placeholder)


@register.simple_tag(takes_context=True, name="tetra_styles")
def styles_placeholder_tag(context):
    placeholder = f"<!-- tetra styles {uuid4()} -->"  #
    try:
        context.request.tetra_styles_placeholder_string = placeholder.encode()
    except AttributeError:
        raise TetraTemplateTagException(
            '{% tetra_styles %} tag requires "request" in the template context.'
        )
    return mark_safe(placeholder)


ALL_CONTEXT = object()


def token_attr(bit, parser):
    if "=" not in bit:
        return {}
    name, value = bit.split("=", 1)
    return {name: parser.compile_filter(value)}


@register.tag(name="@")
def do_component(parser, token):
    split_contents = token.split_contents()
    if len(split_contents) < 2:
        raise template.TemplateSyntaxError("Component tag requires a component name")
    component_name = split_contents[1]
    bits = split_contents[2:]

    component_name = component_name.strip("'\"")

    # If the tag ends with a / than it has no content, otherwise it does.
    has_content = True
    if (len(bits) > 0) and (bits[-1] == "/"):
        has_content = False
        bits = bits[:-1]

    # bits can be split into sections stating with one of:
    # 'args:', 'attrs:' or 'context:'
    # The fist section defaults to 'args:' if it  is unprefixed.
    bits_grouped = {
        "args:": [],
        "attrs:": [],
        "context:": [],
    }
    current_prefix = "args:"
    for bit in bits:
        if bit in bits_grouped:
            current_prefix = bit
        else:
            bits_grouped[current_prefix].append(bit)

    # Args bits:
    args = []
    kwargs = {}
    for bit in bits_grouped["args:"]:
        # First we try to extract a potential kwarg from the bit
        kwarg = template.base.token_kwargs([bit], parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = kwarg.popitem()
            if param in kwargs:
                # The keyword argument has already been supplied once
                raise template.TemplateSyntaxError(
                    f"Component '{component_name}' received multiple values for "
                    f"keyword argument '{param}'"
                )
            else:
                # All good, record the keyword argument
                kwargs[str(param)] = value
        else:
            if kwargs:
                raise template.TemplateSyntaxError(
                    f"Component '{component_name}' received some positional "
                    "argument(s) after some keyword argument(s)"
                )
            else:
                # Record the positional argument
                args.append(parser.compile_filter(bit))

    # Attrs bits:
    attrs = {}
    for bit in bits_grouped["attrs:"]:
        kwarg = token_attr(bit, parser)
        if kwarg:
            attr, value = kwarg.popitem()
            attrs[str(attr)] = value
        else:
            raise template.TemplateSyntaxError(
                f"Component '{component_name}' attrs must be prefixed by a attr name."
            )

    # Context bits:
    if "__all__" in bits_grouped["context:"]:
        if len(bits_grouped["context:"]) > 1:
            raise template.TemplateSyntaxError(
                f"__all__ and multiple context arguments are mutually exclusive in "
                f"Component '{component_name}'."
            )
        context_args = ALL_CONTEXT
    elif "**context" in bits_grouped["context:"]:
        # TODO: remove in 1.0
        if len(bits_grouped["context:"]) > 1:
            raise template.TemplateSyntaxError(
                f"Component '{component_name}' has multiple context arguments as well a "
                "**context for all context."
            )
        context_args = ALL_CONTEXT
        warnings.warn(
            f"Component '{component_name}': 'context: **context' is deprecated and "
            f"will be removed in future versions of Tetra. Please use 'context: __all__' instead.",
            DeprecationWarning,
        )
    else:
        context_args = {}
        for bit in bits_grouped["context:"]:
            # First we try to extract a potential kwarg from the bit
            kwarg = template.base.token_kwargs([bit], parser)
            if kwarg:
                # The kwarg was successfully extracted
                param, value = kwarg.popitem()
                if param in context_args:
                    # The context argument has already been supplied once
                    raise template.TemplateSyntaxError(
                        f"Component '{component_name}' received multiple values for "
                        f"context argument '{param}'"
                    )
                else:
                    # All good, record the keyword argument
                    context_args[str(param)] = value
            else:
                # Record the unprefixed argument using the var name as the context arg.
                # so my_context_var is interpreted as my_context_var=my_context_var
                context_args[bit] = parser.compile_filter(bit)

    nodelist = None
    if has_content:
        # Parse the contents of the use tag, we reset the parser.__loaded_blocks
        # so that we can reuse block names inside each individual use tag
        current_loaded_blocks = getattr(parser, "__loaded_blocks", None)
        parser.__loaded_blocks = []
        nodelist = parser.parse(("/@",))
        if current_loaded_blocks is not None:
            parser.__loaded_blocks = (
                current_loaded_blocks  # Return original __loaded_blocks
            )
        parser.delete_first_token()

    return ComponentNode(
        component_name,
        args,
        kwargs,
        attrs=attrs,
        context_args=context_args,
        nodelist=nodelist,
        origin=parser.origin,
    )


class ComponentNode(template.Node):
    def __init__(
        self,
        component_name,
        args,
        kwargs,
        attrs=None,
        context_args=None,
        nodelist=None,
        origin=None,
    ):
        self.component_name = component_name
        self.args = args
        self.kwargs = kwargs
        self.attrs = attrs
        self.context_args = context_args
        self.nodelist = nodelist
        self.blocks = None
        self.prepare_blocks(origin=origin)

    def __repr__(self):
        return f"<ComponentNode: {self.component_name}>"

    def get_nodes_by_type(self, nodetype):
        # This stops blocks leeking out of scope.
        if nodetype == BlockNode and not getattr(
            thread_local, "geting_nodes_by_type_deep", False
        ):
            return []
        else:
            return super().get_nodes_by_type(nodetype)

    def prepare_blocks(self, origin=None):
        if not self.nodelist:
            return
        default_block = False

        for node in self.nodelist:
            if isinstance(node, template.base.TextNode) and re.match(r"^\s*$", node.s):
                continue
            if not isinstance(node, BlockNode):
                default_block = True
                break

        if default_block:
            block = BlockNode("default", self.nodelist)
            block.origin = origin
            self.blocks = {"default": block}
            self.nodelist = template.base.NodeList([block])
            self.nodelist.contains_nontext = True
        else:
            self.blocks = dict(
                (n.name, n) for n in self.nodelist.get_nodes_by_type(BlockNode)
            )

    def render(self, context) -> SafeString:
        """
        :param context: The template context in which the component is being rendered.
            It must include the "request" attribute.
        :return: The rendered component as a tag string or directly rendered component
            as per the resolved state.
        """
        # when component starts with "=", assume it is a dynamic variable name
        is_dynamic = self.component_name.startswith("=")
        if is_dynamic:
            # Handle dotted paths for dynamic component names
            path = self.component_name.split(".")
            path[0] = path[0][1:]
            # traverse the context for the component name
            c = context
            for part in path:
                try:
                    c = c[part]
                except TypeError:
                    c = getattr(c, part, None)
                except KeyError:
                    c = None

                if c is None:
                    raise ComponentNotFound(
                        f"Unable to resolve dynamic component: '{self.component_name}'"
                    )
            Component = c
        else:
            Component = resolve_component(context, self.component_name)

        try:
            request = context.request
        except AttributeError:
            raise ComponentError(
                'Tetra Components require "request" in the template context.'
            )

        resolved_args = [var.resolve(context) for var in self.args]
        resolved_kwargs = {k: v.resolve(context) for k, v in self.kwargs.items()}
        resolved_attrs = {k: v.resolve(context) for k, v in self.attrs.items()}

        # check extra context arguments
        extra_context = getattr(Component, "_extra_context", [])
        if type(extra_context) is str:
            extra_context = [extra_context]

        if self.context_args == ALL_CONTEXT or "__all__" in extra_context:
            resolved_context = context
        else:
            resolved_context = template.Context()
            ctx = {}
            for k in extra_context:
                if k in context:
                    ctx[k] = context[k]
                else:
                    # this variable is nnot in context!
                    logger.warning(
                        f"Component {self} uses '{k}' in _extra_context, "
                        f"but it is not available in current context."
                    )
            if ctx:
                resolved_context.update(ctx)

        if self.context_args != ALL_CONTEXT:
            # update context with the explicitly given params. This may not
            # happen if __all__ context is requested directly on the template tag.
            resolved_context.update(
                {k: v.resolve(context) for k, v in self.context_args.items()}
            )

        # add "blocks" dict to context, to easily filter out if each block is available
        if self.blocks:
            resolved_context["blocks"] = {}
            for block in self.blocks:
                resolved_context["blocks"][block] = True

        blocks = copy.copy(self.blocks)
        if blocks and BLOCK_CONTEXT_KEY in context.render_context:
            old_block_context = context.render_context[BLOCK_CONTEXT_KEY]
            for block_name, block in blocks.items():
                expose_as = getattr(block, "expose_as", None)
                if expose_as:
                    new_block = old_block_context.get_block(expose_as)
                    if new_block:
                        blocks[block_name] = new_block

        children_state = context.get("_loaded_children_state", None)
        if "key" not in resolved_kwargs:
            resolved_kwargs["key"] = Component.full_component_name()
        if (
            children_state
            and (resolved_kwargs["key"] in children_state)
            and not is_dynamic
        ):
            component_state = children_state[resolved_kwargs["key"]]
            component = Component.from_state(
                component_state,
                request,
                *resolved_args,
                **resolved_kwargs,
                _attrs=resolved_attrs,
                _context=resolved_context,
                _blocks=blocks,
            )
            if "children" in component_state:
                component._loaded_children_state = component_state["children"]
            return component.render()
        else:
            return Component.as_tag(
                request,
                *resolved_args,
                **resolved_kwargs,
                _attrs=resolved_attrs,
                _context=resolved_context,
                _blocks=blocks,
            )


@register.tag(name="...")
def do_attr_tag(parser, token):
    split_contents = token.split_contents()
    if len(split_contents) < 2:
        raise template.TemplateSyntaxError("Attr tag requires at least one argument")
    bits = split_contents[1:]

    # Args bits:
    args = []
    for bit in bits:
        # First we try to extract a potential kwarg from the bit
        kwarg = token_attr(bit, parser)
        if kwarg:
            # The kwarg was successfully extracted
            param, value = kwarg.popitem()
            args.append({str(param): value})
        else:
            args.append(parser.compile_filter(bit))

    return AttrsNode(args)


class AttrsNode(template.Node):
    def __init__(self, args):
        self.args = args

    def arg_gen(self, context):
        for arg in self.args:
            if isinstance(arg, template.base.FilterExpression):
                resolved_arg = arg.resolve(context)
                for key, value in resolved_arg.items():
                    yield key, value
            else:
                for key, value in arg.items():
                    resolved_value = value.resolve(context)
                    yield key, resolved_value
        # add subscribed events as Alpine x-on attr

        c = self.origin.component
        if hasattr(c, "_event_subscriptions"):
            for event_name, method_name in c._event_subscriptions.items():
                yield f"x-on:{event_name}", f"{method_name}($event.detail)"

    def render(self, context):
        attrs = {}
        for key, value in self.arg_gen(context):
            if key == "class":
                # TODO: class from boolean var
                attrs.setdefault("class", set())
                attrs["class"].update(value.split())
            elif key == "style":
                # TODO: advanced style via dict or dotted path from vars
                attrs.setdefault("style", {})
                for rule in value.split(";"):
                    prop_key, prop_val = rule.split(":", 1)
                    attrs["style"][prop_key] = prop_val
            else:
                attrs[key] = value
        if "class" in attrs:
            attrs["class"] = " ".join(attrs["class"])
        if "style" in attrs:
            attrs["style"] = "; ".join(f"{k}: {v}" for k, v in attrs["style"].items())
        for key, value in list(attrs.items()):
            if value is False:
                del attrs[key]
        return " ".join(k if v is True else f'{k}="{v}"' for k, v in attrs.items())


@register.tag("block")
def do_block(parser, token):
    """
    Define a block that can be overridden by child templates.
    Based on the native Django tag but adds an extra attribute (expose_as) to the
    BlockNode indicating if it is posible to overide in an extending template and
    under what name.
    Syntax to expose a block under its own name
    {% block block_name expose %}
    Syntax to expose a block under a different name:
    {% block block_name expose as exposed_block_name %}
    """
    # token.split_contents() isn't useful here because this tag doesn't accept
    # variable as arguments.
    bits = token.contents.split()
    if len(bits) not in (2, 3, 5):
        raise template.TemplateSyntaxError(
            "'%s' tag takes one, two or four arguments" % bits[0]
        )
    if len(bits) > 2 and bits[2] != "expose":
        raise template.TemplateSyntaxError(
            "'%s' tag second argument can only be 'expose' if given" % bits[0]
        )
    if len(bits) == 5 and bits[3] != "as":
        raise template.TemplateSyntaxError(
            "'%s' tag third argument can only be 'as' if given" % bits[0]
        )

    block_name = bits[1]

    if len(bits) == 5:
        expose_as = bits[4]
    elif len(bits) == 3:
        expose_as = block_name
    else:
        expose_as = None

    # Keep track of the names of BlockNodes found in this template, so we can
    # check for duplication.
    try:
        if block_name in parser.__loaded_blocks:
            raise template.TemplateSyntaxError(
                "'%s' tag with name '%s' appears more than once" % (bits[0], block_name)
            )
        parser.__loaded_blocks.append(block_name)
    except AttributeError:  # parser.__loaded_blocks isn't a list yet
        parser.__loaded_blocks = [block_name]
    nodelist = parser.parse(("endblock",))

    # This check is kept for backwards-compatibility. See #3100.
    endblock = parser.next_token()
    acceptable_endblocks = ("endblock", "endblock %s" % block_name)
    if endblock.contents not in acceptable_endblocks:
        parser.invalid_block_tag(endblock, "endblock", acceptable_endblocks)

    node = BlockNode(block_name, nodelist)
    node.expose_as = expose_as
    node.origin = parser.origin  # Needed for persistent_id when pickeling
    return node


@register.tag(name="@v")
def live_variable(parser, token) -> template.Node:
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, format_string = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError(
            "%r tag requires a single argument" % token.contents.split()[0]
        )

    split_contents = token.split_contents()
    if len(split_contents) != 2:
        raise template.TemplateSyntaxError(
            "@v tag requires exactly one argument: the variable name"
        )
    # remove surrounding quotes, if any
    if format_string[0] == format_string[-1] and format_string[0] in ('"', "'"):
        format_string = format_string[1:-1]

    return LiveVariableNode(format_string)


class LiveVariableNode(template.Node):
    def __init__(self, var_name: str):
        self.var_name = var_name

    def __repr__(self):
        return f"<LiveVariableNode: {self.var_name}>"

    def render(self, context):
        return mark_safe(f"<span x-text='{self.var_name}'></span>")


@register.filter(name="if")
def if_filter(value, arg):
    if arg:
        return value
    else:
        return ""


@register.filter(name="else")
def if_filter(value, arg):  # noqa: F811
    if value:
        return value
    else:
        return arg
