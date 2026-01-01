import os
from unittest.mock import patch

import pytest
from django import forms
from django.conf import settings
from django.forms import BaseForm
from django.urls import reverse
from playwright.sync_api import Page

from tetra import Library, public
from tetra.components import FormComponent
from tetra.utils import NamedTemporaryUploadedFile

ui = Library("ui", "main")


class UploadForm(forms.Form):
    file = forms.FileField()


@ui.register
class UploadComponent(FormComponent):
    form_class = UploadForm
    text = "loading"
    uploaded_filename = ""

    def form_valid(self, form: BaseForm) -> None:
        uploaded_file = getattr(self, "file", None)
        if uploaded_file is None:
            # Should normally not happen if form is valid, but let's be safe
            return
        assert isinstance(uploaded_file, NamedTemporaryUploadedFile)

        # Save the file to MEDIA by moving it there
        temp_path = settings.MEDIA_ROOT / uploaded_file.name
        with open(temp_path, "wb") as f:
            for chunk in uploaded_file.chunks():
                f.write(chunk)
        self.uploaded_filename = str(temp_path)
        self.text = "Uploaded successfully"

    @public
    def action(self):
        """just a dummy"""

    # language=html
    template = """
    <div>
      <label>{{ form.file.label }} {{ form.file }}</label>
      <div id="errors">{{ form.file.errors }}</div>
      <button id="submit-button" @click="submit()">Upload</button>
      <div id="result">{{ text }}</div>
      <div id="filename" style="display:none;">{{ uploaded_filename }}</div>
      <button id="action-button" @click="action()">Action</button>
    </div>
    """


@pytest.mark.playwright
def test_upload_file_with_submit(page: Page, tetra_component):
    """Test component that provides a file upload button.

    This test uploads a file, and checks if it was saved correctly.
    """
    file_path = settings.BASE_DIR / "apps/main/assets/upload.txt"

    component = tetra_component(UploadComponent)
    component.locator("#id_file").wait_for(state="visible")
    component.locator("#id_file").set_input_files(file_path)

    with page.expect_response(lambda response: "submit" in response.url):
        component.locator("#submit-button").click()
    expect(component.locator("#result")).to_have_text("Uploaded successfully")

    # Get the uploaded filename and verify content
    uploaded_filename = component.locator("#filename").text_content()
    assert os.path.exists(uploaded_filename)
    with open(uploaded_filename, "rb") as f:
        assert f.read() == b"some file content."

    # Clean up
    os.remove(uploaded_filename)


# FIXME: if this test is run AFTER other tests with UploadComponent, playwright's
#  browser seems to persist the old file input data, causing the test to fail
#  if it is run alone or before others, it passes.
# @pytest.mark.playwright
# def test_component_upload_with_no_file_must_fail(page: Page, component_locator):
#
#     component = component_locator(UploadComponent)
#     # Clear any existing file selection by setting empty files
#     component.locator("#id_file").set_input_files([])
#
#     # don't assign a file to the input, just click on "submit"
#     with page.expect_response(lambda response: "submit" in response.url):
#         component.locator("#submit-button").click()
#
#     expect(component.locator("#errors")).to_contain_text("This field is required")
#     # assert component.locator("#filename").inner_html() == ""


@pytest.mark.playwright
def test_upload_file_with_other_component_method(page: Page, tetra_component):
    """Test component that provides a file upload button.

    This test uploads a file, and checks if it was saved correctly.
    """
    file_path = settings.BASE_DIR / "apps/main/assets/upload.txt"

    component = tetra_component(UploadComponent)
    component.locator("#id_file").wait_for(state="visible")

    component.locator("#id_file").set_input_files(file_path)

    # Now we click on any action button that triggers a component method. Even here
    # the file must be uploaded.
    with page.expect_response(lambda response: "action" in response.url):
        component.locator("#action-button").click()
    expect(component.locator("#result")).to_have_text("Uploaded successfully")

    # Get the uploaded filename and verify content
    uploaded_filename = component.locator("#filename").text_content()
    assert os.path.exists(uploaded_filename)
    with open(uploaded_filename, "rb") as f:
        assert f.read() == b"some file content."

    # Clean up
    os.remove(uploaded_filename)


from playwright.sync_api import expect
