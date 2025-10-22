import os
import pytest

from unittest.mock import patch
from django import forms
from django.conf import settings
from django.forms import BaseForm
from django.urls import reverse

from tetra import Library
from tetra.components import FormComponent
from tetra.utils import NamedTemporaryUploadedFile

ui = Library("ui", "main")


class UploadForm(forms.Form):
    file = forms.FileField()


@ui.register
class UploadComponent(FormComponent):
    form_class = UploadForm
    text = ""
    uploaded_filename = ""

    def form_valid(self, form: BaseForm) -> None:
        uploaded_file: NamedTemporaryUploadedFile = self.file  # noqa
        assert isinstance(uploaded_file, NamedTemporaryUploadedFile)

        # Save the file to MEDIA
        temp_path = settings.MEDIA_ROOT / uploaded_file.name
        with open(temp_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        self.uploaded_filename = str(temp_path)
        self.text = "Uploaded successfully"

    # language=html
    template = """
    <div>
        {{ form.file }}
        <div id="errors">{{ form.file.errors }}</div>
        <button id="submit-button" @click="submit()">Upload</button>
        <div id="result">{{ text }}</div>
        <div id="filename" style="display:none;">{{ uploaded_filename }}</div>
    </div>
    """


# FIXME: if this test is run AFTER other tests with UploadComponent, playwright's
#  browser seems to persist the old file input data, causing the test to fail
#  if it is run alone or before others, it passes.
@pytest.mark.playwright
def test_component_upload_with_no_file_must_fail(page, live_server):

    with patch.object(UploadComponent, "form_invalid") as mock_form_invalid:

        page.goto(
            live_server.url
            + reverse("generic_ui_component_test_view", args=["UploadComponent"])
        )

        # Clear any existing file selection by setting empty files
        page.locator("#id_file").set_input_files("")

        # don't assign a file to the input, just click on "submit"
        page.locator("#submit-button").click()
        page.wait_for_load_state()
        mock_form_invalid.assert_called_once()

        # assert "This field is required" in page.locator("#errors").inner_html()
        # assert page.locator("#filename").inner_html() == ""


@pytest.mark.playwright
def test_upload_file_with_form_component(page, live_server):
    """Test component that provides a file upload button."""
    file_path = settings.BASE_DIR / "apps/main/assets/upload.txt"

    page.goto(
        live_server.url
        + reverse("generic_ui_component_test_view", args=["UploadComponent"])
    )
    result_div = page.locator("#result")
    assert result_div.text_content() == ""

    page.locator("#id_file").set_input_files(file_path)
    page.locator("#submit-button").click()

    # Wait for the file to be uploaded, then check if result text was changed after
    # page reload
    page.wait_for_load_state()
    assert result_div.text_content() == "Uploaded successfully"

    # Get the uploaded filename and verify content
    uploaded_filename = page.locator("#filename").text_content()
    assert os.path.exists(uploaded_filename)
    with open(uploaded_filename, "rb") as f:
        assert f.read() == b"some file content."

    # Clean up
    os.remove(uploaded_filename)

    # Clear file input to prevent state leakage to next test
    # page.locator("#id_file").set_input_files([])
