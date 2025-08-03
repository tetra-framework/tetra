import os
import time
import pytest
from django.http import FileResponse
from django.urls import reverse
from selenium.webdriver.common.by import By

from tetra import Library, Component, public

foo = Library("ui", "main")


@foo.register
class DownloadComponent(Component):
    @public
    def download_default(self):
        return FileResponse(
            "Hello, World!", content_type="text/plain", filename="foo.txt"
        )

    # language=html
    template = """
               <div>
                 <button @click="download_default()"
                         id="download_default">download</button>
               </div>
               """


#
# @pytest.mark.django_db
# # FIXME: downloaded file is not found!
# def test_component_download(post_request_with_session, driver, live_server, tmp_path):
#     """Tests a simple component with download functionality"""
#     # Configure the browser to download files to our temporary test directory
#     download_dir = str(tmp_path)
#     driver.command_executor._commands["send_command"] = (
#         "POST",
#         "/session/$sessionId/chromium/send_command",
#     )
#     params = {
#         "cmd": "Page.setDownloadBehavior",
#         "params": {"behavior": "allow", "downloadPath": download_dir},
#     }
#     driver.execute("send_command", params)
#
#     # Navigate to and click the download button
#     driver.get(live_server.url + reverse("download_component"))
#     button = driver.find_element(By.ID, "download_default")
#     button.click()
#
#     # Wait for the file to be downloaded (max 10 seconds)
#     expected_filename = "foo.txt"
#     expected_file_path = os.path.join(download_dir, expected_filename)
#
#     def file_downloaded():
#         return (
#             os.path.exists(expected_file_path)
#             and os.path.getsize(expected_file_path) > 0
#         )
#
#     timeout = time.time() + 2
#     while not file_downloaded() and time.time() < timeout:
#         time.sleep(0.5)
#
#     # Verify file exists and content is correct
#     assert os.path.exists(
#         expected_file_path
#     ), f"Download file '{expected_file_path}' not found."
#
#     with open(expected_file_path, "r", encoding="utf-8") as f:
#         content = f.read()
#         assert (
#             content == "Hello, World!"
#         ), "File content does not match expected content"
