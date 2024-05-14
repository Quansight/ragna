import os
import time
from multiprocessing import Process

import httpx
import panel as pn
import pytest
import uvicorn
from playwright.sync_api import expect, sync_playwright

from ragna.assistants import RagnaDemoAssistant
from ragna.core._utils import default_user
from ragna.deploy import Config
from ragna.deploy._api import app as api_app
from ragna.deploy._ui import app as ui_app


class TestAssistant(RagnaDemoAssistant):
    def answer(self, prompt, sources, *, multiple_answer_chunks: bool):
        content = next(super().answer(prompt, sources))

        if multiple_answer_chunks:
            for chunk in content.split(" "):
                yield f"{chunk} "
        else:
            yield content


@pytest.fixture(scope="session")
def headed_mode(pytestconfig):
    return pytestconfig.getoption("headed") or False


@pytest.fixture
def config(tmp_local_root):
    return Config(local_root=tmp_local_root, assistants=[TestAssistant])


TEST_UI_HOSTNAME = "http://localhost"
TEST_API_PORT = "8769"


@pytest.fixture
def api_server(config):
    def start_server():
        uvicorn.run(
            api_app(
                config=config,
                ignore_unavailable_components=True,
            ),
            host=config.api.hostname,
            port=config.api.port,
        )

    def server_up():
        try:
            return httpx.get(config.api.url).is_success
        except httpx.ConnectError:
            return False

    proc = Process(target=start_server, args=(), daemon=True)
    proc.start()

    timeout = 5
    while timeout > 0 and not server_up():
        print(f"Waiting for API server to come up on {config.api.url}")
        time.sleep(1)
        timeout -= 1

    yield proc
    proc.kill()


def auth_header(base_url):
    username = default_user()
    token = (
        httpx.post(
            base_url + "/token",
            data={
                "username": username,
                "password": os.environ.get(
                    "RAGNA_DEMO_AUTHENTICATION_PASSWORD", username
                ),
            },
        )
        .raise_for_status()
        .json()
    )

    return f"Bearer {token}"


@pytest.fixture(scope="function")
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


def test_health(config, page) -> None:
    health_url = config.ui.origins[0] + "/health"
    page.goto(health_url)
    expect(page.get_by_role("heading", name="Ok")).to_be_visible()


def test_index_with_blank_credentials(config, page) -> None:
    # Index page, no auth
    index_url = config.ui.origins[0]
    page.goto(index_url)
    expect(page.get_by_role("button", name="Sign In")).to_be_visible()

    # Authorize with no credentials
    page.get_by_role("button", name="Sign In").click()
    expect(page.get_by_role("button", name=" New Chat")).to_be_visible()


def test_index_with_auth_header(config, page) -> None:
    pn.state.headers["Authorization"] = auth_header(config.api.url)

    index_url = config.ui.origins[0]
    page.goto(index_url)
    expect(page.get_by_role("button", name=" New Chat")).to_be_visible()

    # page.locator("div").filter(
    #     has_text=re.compile(r"^Source storageChromaLanceDBRagna/DemoSourceStorage$")
    # ).get_by_role("combobox").select_option("LanceDB")
    # page.get_by_role("button", name="Advanced Configurations ▶").click()
    # page.locator("#fileUpload-p2365").click()


# def test_ui_with_auth_headers(config, ui_server, headed_mode) -> None:
#     with sync_playwright() as playwright:
#
#         browser = playwright.chromium.launch(headless=not headed_mode)
#         context = browser.new_context()
#         page = context.new_page()
#
#         # Health page
#         health_url = config.ui.origins[0] + "/health"
#         page.goto(health_url)
#         expect(page.get_by_role("heading", name="Ok")).to_be_visible()
#
#         # Index page, no auth
#         index_url = config.ui.origins[0]
#         page.goto(index_url)
#         expect(page.get_by_role("button", name="Sign In")).to_be_visible()
#
#         # Authorize with no credentials
#         page.get_by_role("button", name="Sign In").click()
#         expect(page.get_by_role("button", name=" New Chat")).to_be_visible()
#
#         # page.locator("div").filter(
#         #     has_text=re.compile(r"^Source storageChromaLanceDBRagna/DemoSourceStorage$")
#         # ).get_by_role("combobox").select_option("LanceDB")
#         # page.get_by_role("button", name="Advanced Configurations ▶").click()
#         # page.locator("#fileUpload-p2365").click()
#
#         context.close()
#         browser.close()
