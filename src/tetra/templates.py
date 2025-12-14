from django.template.base import Template, Origin
from django.template.loader_tags import BlockNode
from collections import defaultdict
import re


original_template_compile_nodelist = Template.compile_nodelist


class InlineTemplate(Template):
    """Represents an "inline" template string within a component."""

    def get_exception_info(self, *args, **kwargs):
        ret = super().get_exception_info(*args, **kwargs)
        line_offset = self.origin.start_line - 1
        ret["top"] += line_offset
        ret["bottom"] += line_offset
        ret["line"] += line_offset
        ret["top"] += line_offset
        ret["message"] = re.sub(
            r"(line )(\d+)(:)",
            lambda m: f"{m.group(1)}{int(m.group(2))+line_offset}{m.group(3)}",
            ret["message"],
        )
        ret["source_lines"] = [
            (line + line_offset, s) for (line, s) in ret["source_lines"]
        ]
        return ret


class InlineOrigin(Origin):
    def __init__(self, start_line=0, component=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_line = start_line
        self.component = component


def new_template_compile_nodelist(self):
    nodelist = original_template_compile_nodelist(self)
    self.blocks_by_key = {}
    annotate_nodelist(self, nodelist, [])
    return nodelist


def monkey_patch_template():
    Template.compile_nodelist = new_template_compile_nodelist


def annotate_nodelist(template, nodelist, path):
    from .templatetags.tetra import ComponentNode

    if nodelist:
        node_type_counter = defaultdict(int)
        for node in nodelist:
            if isinstance(node, BlockNode):
                node_key = f"block:{node.name}:{node_type_counter['block:'+node.name]}"
                node._path_key = "/".join([*path, node_key])
                template.blocks_by_key[node._path_key] = node
                annotate_nodelist(template, node.nodelist, [*path, node_key])
                node_type_counter["block:" + node.name] += 1
            elif isinstance(node, ComponentNode):
                node_key = f"comp:{node.component_name}:{node_type_counter['block:'+node.component_name]}"
                annotate_nodelist(template, node.nodelist, [*path, node_key])
                node_type_counter["comp:" + node.component_name] += 1
            elif hasattr(node, "nodelist"):
                annotate_nodelist(template, node.nodelist, path)
