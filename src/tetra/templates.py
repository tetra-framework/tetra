from django.template.base import Template, Origin
from django.template.loader_tags import BlockNode
from collections import defaultdict
import re


class InlineTemplate(Template):
    """Represents an "inline" template string within a component."""

    def get_exception_info(self, *args, **kwargs):
        ret = super().get_exception_info(*args, **kwargs)
        line_offset = self.origin.start_line - 1
        ret["top"] += line_offset
        ret["bottom"] += line_offset
        ret["line"] += line_offset
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
    nodelist = Template._tetra_original_compile_nodelist(self)
    if not hasattr(self, "blocks_by_key"):
        self.blocks_by_key = {}
        annotate_nodelist(self, nodelist, [])
    return nodelist


new_template_compile_nodelist._tetra_patched = True  # type: ignore[attr-defined]


def monkey_patch_template():
    """
    Patch the `Template` class to replace its `compile_nodelist` method with a custom function.

    This function modifies the behavior of Django's `Template` class to use a new custom-defined
    `new_template_compile_nodelist` for compiling the nodelist. It ensures the patch is applied only
    once by checking the presence of a custom `_tetra_patched` attribute. Additionally, it preserves
    the original `compile_nodelist` method by storing it in an attribute
    `_tetra_original_compile_nodelist` if it hasn't been stored already.
    """
    if not getattr(Template.compile_nodelist, "_tetra_patched", False):
        if not hasattr(Template, "_tetra_original_compile_nodelist"):
            Template._tetra_original_compile_nodelist = Template.compile_nodelist
        Template.compile_nodelist = new_template_compile_nodelist


def annotate_nodelist(template, nodelist, path, memo=None):
    from .templatetags.tetra import ComponentNode

    if memo is None:
        memo = set()

    # Recursively annotate nodes, blocks, and component subtrees
    if nodelist and id(nodelist) not in memo:
        memo.add(id(nodelist))
        node_type_counter = defaultdict(int)
        for node in nodelist:
            if isinstance(node, BlockNode):
                node_key = f"block:{node.name}:{node_type_counter['block:'+node.name]}"
                node._path_key = "/".join([*path, node_key])
                template.blocks_by_key[node._path_key] = node
                annotate_nodelist(template, node.nodelist, [*path, node_key], memo)
                node_type_counter["block:" + node.name] += 1
            elif isinstance(node, ComponentNode):
                node_key = f"comp:{node.component_name}:{node_type_counter['comp:'+node.component_name]}"
                annotate_nodelist(template, node.nodelist, [*path, node_key], memo)
                node_type_counter["comp:" + node.component_name] += 1
            elif hasattr(node, "nodelist"):
                annotate_nodelist(template, node.nodelist, path, memo)
            elif hasattr(node, "branches"):
                # Handle nodes like IfNode that have multiple branches
                for branch in node.branches:
                    annotate_nodelist(template, branch[1], path, memo)
            elif hasattr(node, "nodelist_true"):
                # Handle IfNode in older Django versions or other nodes with nodelist_true/false
                annotate_nodelist(template, node.nodelist_true, path, memo)
                if hasattr(node, "nodelist_false"):
                    annotate_nodelist(template, node.nodelist_false, path, memo)
