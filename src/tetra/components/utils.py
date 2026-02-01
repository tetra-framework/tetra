from threading import local

_tetra_component_count = local()


def get_next_autokey():
    if not hasattr(_tetra_component_count, "count"):
        _tetra_component_count.count = 0
    _tetra_component_count.count += 1
    return f"tk_{_tetra_component_count.count}"


def reset_autokey_count():
    _tetra_component_count.count = 0
