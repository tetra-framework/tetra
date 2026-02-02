import re
import logging

logger = logging.getLogger(__name__)


class ChannelGroupRegistry:
    """
    Manages and verifies membership for channel groups through exact names and
    pattern matching.

    This class allows registration of group names or regex patterns to maintain a registry of allowed
    groups. It checks if a given group name is either explicitly registered or matches any of the
    registered patterns.
    """

    def __init__(self):
        self._exact_groups = set()
        self._patterns = []

    def register(self, group_or_pattern):
        if isinstance(group_or_pattern, str):
            self._exact_groups.add(group_or_pattern)
        elif hasattr(group_or_pattern, "match"):
            self._patterns.append(group_or_pattern)
        else:
            raise TypeError("group_or_pattern must be a string or a regex pattern")

    def unregister(self, group_name):
        if group_name in self._exact_groups:
            self._exact_groups.remove(group_name)

    def is_allowed(self, group_name):
        if group_name in self._exact_groups:
            return True
        for pattern in self._patterns:
            if pattern.match(group_name):
                return True
        return False


channels_group_registry = ChannelGroupRegistry()
