from tetra.templatetags.tetra import if_filter, else_filter


def test_if_filter():
    """Verify that the 'if' template filter correctly returns the value based on condition truthiness."""
    assert if_filter("string", "truthy") == "string"
    assert if_filter("string", "0") is "string"
    assert if_filter("string", "") is ""
    assert if_filter("string", None) is ""
    assert if_filter("string", False) is ""


def test_else_filter():
    """Verify that the 'else' template filter correctly returns the fallback value when the input is falsy."""
    assert else_filter("string", "else") is "string"
    assert else_filter("0", "else") == "0"
    assert else_filter("1", "else") == "1"
    assert else_filter("", "else") == "else"
    assert else_filter(None, "else") == "else"
    assert else_filter(0, "else") == "else"
    assert else_filter(False, "else") == "else"
