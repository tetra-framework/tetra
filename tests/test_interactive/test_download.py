import io
import pytest
from django.http import FileResponse
from playwright.sync_api import Page

from tetra import Library, Component, public

foo = Library("ui", "main")


@foo.register
class DownloadComponent(Component):

    @public
    def download(self):
        self.message = "goo"
        return FileResponse(
            io.BytesIO(b"Hello, World!"),
            content_type="text/plain",
            filename="foo.txt",
            as_attachment=True,
        )

    # language=html
    template = """
    <div>
      <button @click="download()" id="download_default">Download</button>
    </div>
    """


@pytest.mark.playwright
def test_component_download(page: Page, tetra_component, tmp_path):
    """
    Test component that provides a download button which starts a file download
    when clicked.
    """

    # Navigate to and click the download button
    component = tetra_component(DownloadComponent)

    # Wait for the file to be downloaded (max 0.5 seconds)
    with page.expect_download(timeout=1000) as download_info:
        # Perform the action that initiates download
        component.get_by_text("Download").click()
    download = download_info.value

    # file name must match the expected one
    assert download.suggested_filename == "foo.txt"

    # file must have been saved successfully
    path = tmp_path / download.suggested_filename
    download.save_as(path)
    assert path.exists()

    # file content must match the expected content
    with open(path, "rt") as f:
        assert f.read() == "Hello, World!"
