import pytest
from django.urls import reverse

from tetra import Component, public, Library
from selenium.webdriver.common.by import By

lib = Library("default", "main")


@lib.register
class ComponentWithMethodReturnValue(Component):
    msg = public("")

    @public
    def get_hello(self) -> str:
        # don't set the value directly, just return it
        return "Hello, World!"

    template = """<div id='component'>
    <button id="clickme" @click="msg=get_hello()">clickme</button>
    <div id="result" x-text="msg"></div>
    </div>"""


@pytest.mark.django_db
def test_basic_component_return(post_request_with_session, driver, live_server):
    """Tests a simple component with / end"""
    driver.get(live_server.url + reverse("component_with_return_value"))
    button = driver.find_element(By.ID, "clickme")
    assert driver.find_element(By.ID, "result").text == ""
    button.click()
    assert driver.find_element(By.ID, "result").text == "Hello, World!"
