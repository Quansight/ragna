import socket
import time
from multiprocessing import Process

import httpx
import panel as pn
import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from ragna._utils import timeout_after
from ragna.deploy import Config
from ragna.deploy._api import app as api_app
from ragna.deploy._ui import app as ui_app

from ..utils import TestAssistant


def get_available_port():
    with socket.socket() as s:
        s.bind(("", 0))
        return s.getsockname()[1]


@pytest.fixture(scope="session")
def headed_mode(pytestconfig):
    return pytestconfig.getoption("headed") or False


@pytest.fixture
def config(tmp_local_root):
    ui_port = get_available_port()
    api_port = get_available_port()
    return Config(
        local_root=tmp_local_root,
        assistants=[TestAssistant],
        ui=dict(port=ui_port),
        api=dict(port=api_port),
    )


class ApiServer:
    def __init__(self, config):
        self.config = config

    def start_server(self):
        uvicorn.run(
            api_app(
                config=self.config,
                ignore_unavailable_components=True,
            ),
            host=self.config.api.hostname,
            port=self.config.api.port,
        )

    def server_up(self):
        try:
            return httpx.get(self.config.api.url).is_success
        except httpx.ConnectError:
            return False

    @timeout_after(5)
    def start(self):
        self.proc = Process(target=self.start_server, args=(), daemon=True)
        self.proc.start()

        while not self.server_up():
            time.sleep(1)

    def stop(self):
        self.proc.terminate()


@pytest.fixture
def api_server(config):
    server = ApiServer(config)
    try:
        server.start()
        yield server
    finally:
        server.stop()


@pytest.fixture
def base_ui_url(config):
    return f"http://{config.ui.hostname}:{config.ui.port}"


@pytest.fixture
def page(config, api_server, headed_mode):
    server = ui_app(config=config, open_browser=False)

    with sync_playwright() as playwright:
        server.serve()
        browser = playwright.chromium.launch(headless=not headed_mode)
        context = browser.new_context()
        page = context.new_page()

        yield page

        context.close()
        browser.close()
        pn.state.kill_all_servers()


def test_health(base_ui_url, page) -> None:
    health_url = base_ui_url + "/health"
    page.goto(health_url)
    expect(page.get_by_role("heading", name="Ok")).to_be_visible()


def test_index_with_blank_credentials(base_ui_url, page) -> None:
    # Index page, no auth
    index_url = base_ui_url
    page.goto(index_url)
    expect(page.get_by_role("button", name="Sign In")).to_be_visible()

    # Authorize with no credentials
    page.get_by_role("button", name="Sign In").click()

    expect(page.get_by_role("button", name=" New Chat")).to_be_visible()


@pytest.mark.skip(reason="TODO: figure out best locators")
def test_new_chat(config, page) -> None:
    index_url = config.ui.origins[0]
    page.goto(index_url)
    expect(page.get_by_role("button", name="Sign In")).to_be_visible()
    page.get_by_role("button", name="Sign In").click()

    expect(page.get_by_role("button", name=" New Chat")).to_be_visible()
    page.get_by_role("button", name=" New Chat").click()

    expect(page.locator("#fileUpload-p4447")).to_be_visible()
    page.locator("#fileUpload-p4447").click()

    page.locator("#fileUpload-p4447").set_input_files()
    page.get_by_role("button", name="Start Conversation").click()
    page.get_by_text("How can I help you with the").click()
    page.get_by_placeholder("Ask a question about the").click()
    page.get_by_placeholder("Ask a question about the").fill(
        "Tell me about the documents"
    )
    page.get_by_role("button", name="").click()
    page.get_by_role("button", name=" Source Info").click()
    page.locator("#main div").filter(has_text="Source Info ¶ This response").nth(
        3
    ).click()
