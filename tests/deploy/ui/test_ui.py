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
from ragna.deploy import ApiConfig, Config, UiConfig
from ragna.deploy._api import app as api_app
from ragna.deploy._ui import app as ui_app

TEST_API_PORT = "38769"
TEST_UI_PORT = "38770"


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
    return Config(
        local_root=tmp_local_root,
        assistants=[TestAssistant],
        ui=UiConfig(port=TEST_UI_PORT),
        api=ApiConfig(port=TEST_API_PORT),
    )


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


@pytest.mark.skip(reason="Need to figure out how to set the auth token")
def test_index_with_auth_token(config, page) -> None:
    auth = auth_header(config.api.url)
    assert len(auth) > len("Bearer ")

    page.set_extra_http_headers({"Authorization": auth})  # this doesn't work
    pn.state.cookies["auth_token"] = ""  # or this
    pn.state.headers["Authorization"] = auth  # or this

    index_url = config.ui.origins[0]
    page.goto(index_url)
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
