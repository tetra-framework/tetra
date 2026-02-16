from django.http import HttpRequest, QueryDict, HttpResponse
from django.test import RequestFactory
from django.contrib.messages import add_message, constants
from django.contrib.sessions.middleware import SessionMiddleware
from tetra.middleware import TetraDetails, TetraMiddleware
from tetra import Library
from tetra.components.base import Component, public
from unittest.mock import Mock, patch

import pytest
import json


@pytest.fixture
def request_factory():
    return RequestFactory()


@pytest.fixture
def middleware():
    """Create a TetraMiddleware instance with a mock get_response"""
    get_response = Mock(return_value=HttpResponse("<html><body>test</body></html>"))
    return TetraMiddleware(get_response)


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


# Tests for middleware efficiency optimization


def test_middleware_fast_path_without_tetra_components(request_factory):
    """Non-Tetra requests should use fast path and skip CSRF token generation"""
    request = request_factory.get("/")
    response = HttpResponse("<html><body>test</body></html>", content_type="text/html")

    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    with patch("tetra.middleware.get_token") as mock_get_token:
        result = middleware(request)

        # get_token should NOT be called for non-Tetra requests
        mock_get_token.assert_not_called()
        assert result == response


def test_middleware_full_path_with_tetra_components(request_factory):
    """Tetra requests should use full path and generate CSRF token"""
    request = request_factory.get("/")
    response = HttpResponse(
        "<html><head><!-- tetra scripts placeholder123 --><!-- tetra styles placeholder456 --></head><body>test</body></html>",
        content_type="text/html",
    )

    # Simulate that Tetra components were used
    request.tetra_components_used = {Mock()}
    request.tetra_scripts_placeholder_string = b"<!-- tetra scripts placeholder123 -->"
    request.tetra_scripts_placeholder_include_alpine = False
    request.tetra_styles_placeholder_string = b"<!-- tetra styles placeholder456 -->"

    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    with patch("tetra.middleware.get_token", return_value="test-csrf-token"):
        with patch(
            "tetra.middleware.render_scripts", return_value="<script>mocked</script>"
        ):
            with patch(
                "tetra.middleware.render_styles", return_value="<style>mocked</style>"
            ):
                result = middleware(request)

                # Result should be processed response
                assert result is not None
                assert isinstance(result, HttpResponse)


@pytest.mark.django_db
def test_middleware_messages_processed_on_fast_path(request_factory):
    """Messages should be processed even on fast path (non-Tetra requests)"""
    from django.contrib.messages.middleware import MessageMiddleware

    request = request_factory.get("/")

    # Add session and message support
    session_middleware = SessionMiddleware(lambda r: None)
    session_middleware.process_request(request)
    request.session.save()

    message_middleware = MessageMiddleware(lambda r: None)
    message_middleware.process_request(request)

    # Add a message
    add_message(request, constants.INFO, "Test message")

    response = HttpResponse("<html><body>test</body></html>", content_type="text/html")
    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    result = middleware(request)

    # Check that messages were injected into HTML
    assert b"window.__tetra_messages =" in result.content
    assert b"Test message" in result.content
    assert "T-Messages" not in result.headers


@pytest.mark.django_db
def test_middleware_messages_have_uid(request_factory):
    """Messages should have UIDs attached on both fast and full paths"""
    from django.contrib.messages.middleware import MessageMiddleware

    request = request_factory.get("/")

    # Add session and message support
    session_middleware = SessionMiddleware(lambda r: None)
    session_middleware.process_request(request)
    request.session.save()

    message_middleware = MessageMiddleware(lambda r: None)
    message_middleware.process_request(request)

    # Add messages
    add_message(request, constants.INFO, "Message 1")
    add_message(request, constants.WARNING, "Message 2")

    response = HttpResponse("<html><body>test</body></html>", content_type="text/html")
    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    result = middleware(request)

    # Check messages have UIDs in the injected script
    assert b"Message 1" in result.content
    assert b"Message 2" in result.content
    assert b'"uid":' in result.content
    assert "T-Messages" not in result.headers


def test_middleware_skips_file_response(request_factory):
    """FileResponse should be returned immediately without processing"""
    from django.http import FileResponse
    import io

    request = request_factory.get("/")
    file_content = io.BytesIO(b"file content")
    response = FileResponse(file_content)

    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    result = middleware(request)

    # Should return the FileResponse as-is
    assert result == response
    assert not hasattr(result, "headers") or "T-Messages" not in result.headers


def test_middleware_creates_tetra_details_on_every_request(request_factory):
    """TetraDetails should be created on every request (lightweight operation)"""
    request = request_factory.get("/")
    response = HttpResponse("<html><body>test</body></html>")

    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    middleware(request)

    # TetraDetails should be attached to request
    assert hasattr(request, "tetra")
    assert isinstance(request.tetra, TetraDetails)


class FlowComponent(Component):
    template = "<div>{{ title }}</div>"
    title = public("initial")

    @public
    def update_title(self, new_title):
        self.title = new_title
        return f"Updated to {new_title}"


@pytest.mark.django_db
def test_unified_protocol_full_flow(rf):
    """Test full flow of unified protocol through the view and middleware."""
    from tetra import Library
    from tetra.views import component_method
    from tetra.state import encode_component
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.messages.middleware import MessageMiddleware
    from collections import defaultdict

    # Setup request
    request = rf.post(
        "/tetra/call/",
        data={},
        content_type="application/json",
    )
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    MessageMiddleware(lambda r: None).process_request(request)
    request.user = AnonymousUser()

    # Create library and register component
    lib = Library("test_lib", app="main")
    lib.register(FlowComponent)

    # Prepare unified protocol request with component location metadata
    encrypted_state = encode_component(FlowComponent(request))
    request_envelope = {
        "protocol": "tetra-1.0",
        "id": "req-123",
        "type": "call",
        "payload": {
            "component_id": "test-comp-id",
            "method": "update_title",
            "args": ["new title"],
            "state": {"title": "initial"},
            "encrypted_state": encrypted_state,
            "children_state": [],
            # Add component location metadata
            "app_name": "main",
            "library_name": "test_lib",
            "component_name": "flow_component",
        },
    }
    request._body = json.dumps(request_envelope).encode("utf-8")
    request.csrf_processing_done = True
    request.tetra_components_used = {FlowComponent}

    # Add a message
    add_message(request, constants.SUCCESS, "Success message")

    # Mock the Library registry and library URLs
    with patch.object(Library, "registry", {"main": {"test_lib": lib}}):
        with patch.object(Library, "styles_url", new_callable=lambda: "/static/main/tetra/test_lib/main_test_lib.css"):
            with patch.object(Library, "js_url", new_callable=lambda: "/static/main/tetra/test_lib/main_test_lib.js"):
                response = component_method(request)

                # Check response from view
                assert response.status_code == 200
                resp_data = json.loads(response.content)
                assert resp_data["protocol"] == "tetra-1.0"
                assert resp_data["type"] == "call.response"
                assert resp_data["metadata"]["messages"][0]["message"] == "Success message"

                # Check response through middleware
                middleware = TetraMiddleware(lambda r: response)
                final_response = middleware(request)
                assert "T-Messages" not in final_response.headers
                assert final_response == response


@pytest.mark.django_db
def test_middleware_no_messages_no_header(request_factory):
    """If there are no messages, T-Messages header should not be added"""
    request = request_factory.get("/")

    # Add session support but don't add any messages
    session_middleware = SessionMiddleware(lambda r: None)
    session_middleware.process_request(request)
    request.session.save()

    response = HttpResponse("<html><body>test</body></html>")
    get_response = Mock(return_value=response)
    middleware = TetraMiddleware(get_response)

    result = middleware(request)

    # T-Messages header should not be present
    assert "T-Messages" not in result.headers


class ErrorComponent(Component):
    template = "<div></div>"

    @public
    def raise_error(self):
        raise ValueError("Test error message")


@pytest.mark.django_db
def test_unified_protocol_error_handling(rf):
    """Test unified protocol error handling when a method raises an exception."""
    from tetra import Library
    from tetra.views import component_method
    from tetra.state import encode_component
    from django.contrib.auth.models import AnonymousUser
    from django.contrib.messages.middleware import MessageMiddleware

    # Setup request
    request = rf.post(
        "/tetra/call/",
        data={},
        content_type="application/json",
    )
    SessionMiddleware(lambda r: None).process_request(request)
    request.session.save()
    MessageMiddleware(lambda r: None).process_request(request)
    request.user = AnonymousUser()

    # Create library and register component
    lib = Library("test_lib", app="main")
    lib.register(ErrorComponent)

    # Prepare unified protocol request with component location metadata
    encrypted_state = encode_component(ErrorComponent(request))
    request_envelope = {
        "protocol": "tetra-1.0",
        "id": "req-123",
        "type": "call",
        "payload": {
            "component_id": "test-comp-id",
            "method": "raise_error",
            "args": [],
            "state": {},
            "encrypted_state": encrypted_state,
            "children_state": [],
            # Add component location metadata
            "app_name": "main",
            "library_name": "test_lib",
            "component_name": "error_component",
        },
    }
    request._body = json.dumps(request_envelope).encode("utf-8")
    request.csrf_processing_done = True
    request.tetra_components_used = {ErrorComponent}

    # Mock the Library registry
    with patch.object(Library, "registry", {"main": {"test_lib": lib}}):
        response = component_method(request)

        # Check response from view
        assert response.status_code == 500
        resp_data = json.loads(response.content)
        assert resp_data["protocol"] == "tetra-1.0"
        assert resp_data["success"] is False
        assert resp_data["error"]["code"] == "ValueError"
        assert resp_data["error"]["message"] == "Test error message"
