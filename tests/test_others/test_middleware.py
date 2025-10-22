from django.http import HttpRequest, QueryDict
from django.test import RequestFactory
from tetra.middleware import TetraDetails

import pytest


@pytest.fixture
def request_factory():
    return RequestFactory()


def test_tetra_details_bool_false(request_factory):
    """Should return False when 'T-Request' header is not present"""
    request = request_factory.get("/")
    tetra_details = TetraDetails(request)
    assert bool(tetra_details) is False


def test_tetra_details_bool_true(request_factory):
    """Should return True when 'T-Request' header is present and set to 'true'"""
    request = request_factory.get("/", HTTP_T_REQUEST="true")
    tetra_details = TetraDetails(request)
    assert bool(tetra_details) is True


def test_tetra_details_current_url(request_factory):
    """Should return the correct current_url when 'T-Current-URL' header is present"""
    request = request_factory.get("/", HTTP_T_CURRENT_URL="https://testserver/test")
    tetra_details = TetraDetails(request)
    assert tetra_details.current_url == "https://testserver/test"


def test_tetra_details_current_url_full_path_none_when_schemes_dont_match(
    request_factory,
):
    """Should return None for current_url_full_path when schemes don't match"""
    request = request_factory.get(
        "/foo/bar/", HTTP_T_CURRENT_URL="https://testserver/test"
    )
    tetra_details = TetraDetails(request)
    assert tetra_details.current_url_full_path is None


def test_tetra_details_current_url_full_path_none_when_hosts_dont_match(
    request_factory,
):
    """Should return None for current_url_full_path when hosts don't match"""
    request = request_factory.get(
        "/foor/bar/", HTTP_T_CURRENT_URL="http://different-host.com/test"
    )
    tetra_details = TetraDetails(request)
    assert tetra_details.current_url_full_path is None


def test_tetra_details_current_url_full_path_when_schemes_and_hosts_match(
    request_factory,
):
    """Should return the correct absolute path when schemes and hosts match"""
    request = request_factory.get("/", HTTP_T_CURRENT_URL="http://testserver/test/path")
    tetra_details = TetraDetails(request)
    assert tetra_details.current_url_full_path == "/test/path"


def test_tetra_details_current_url_query_empty(request_factory):
    """Should return an empty QueryDict when current_url has no query parameters"""
    request = request_factory.get(
        "/foo/bar/", HTTP_T_CURRENT_URL="http://testserver/test"
    )
    tetra_details = TetraDetails(request)
    assert tetra_details.url_query_params == QueryDict()


def test_tetra_details_component_call_url_query_with_parameters(request_factory):
    """Should return a correct QueryDict when current_url has query parameters"""
    request = request_factory.get(
        "/foo/bar/?foo=bar&baz=qux", HTTP_T_CURRENT_URL="http://testserver/test/"
    )
    tetra_details = TetraDetails(request)
    assert tetra_details.url_query_params == QueryDict()


def test_tetra_details_current_url_query_with_parameters(request_factory):
    """Should return a correct QueryDict when current_url has query parameters"""
    request = request_factory.get(
        "/foo/bar/",
        HTTP_T_CURRENT_URL="http://testserver/test/?foo=bar&baz=qux",
    )
    tetra_details = TetraDetails(request)
    assert tetra_details.url_query_params == QueryDict("foo=bar&baz=qux")


# changing the url


def test_set_url(request_factory):
    request = request_factory.get(
        "/foo/bar/",
        HTTP_T_CURRENT_URL="http://testserver/test/?foo=bar&baz=qux",
    )
    tetra_details = TetraDetails(request)
    tetra_details.set_url("http://example.com/foo/baz/")
    assert tetra_details.current_url == "http://example.com/foo/baz/"


def test_change_path(request_factory):
    request = request_factory.get(
        "/foo/bar/",
        HTTP_T_CURRENT_URL="http://testserver/test/?foo=bar&baz=qux",
    )
    tetra_details = TetraDetails(request)
    tetra_details.set_url_path("/foo/baz/")
    assert tetra_details.current_url == "http://testserver/foo/baz/?foo=bar&baz=qux"


def test_change_query(request_factory):
    request = request_factory.get(
        "/foo/bar/",
        HTTP_T_CURRENT_URL="http://testserver/test/?foo=bar&baz=qux",
    )
    tetra_details = TetraDetails(request)
    tetra_details.set_url_query_param("foo", "new")
    assert tetra_details.current_url == "http://testserver/test/?foo=new&baz=qux"


def test_add_query(request_factory):
    request = request_factory.get(
        "/foo/bar/",
        HTTP_T_CURRENT_URL="http://testserver/test/?foo=bar&baz=qux",
    )
    tetra_details = TetraDetails(request)
    tetra_details.set_url_query_param("another", "qui")
    assert (
        tetra_details.current_url
        == "http://testserver/test/?foo=bar&baz=qux&another=qui"
    )
