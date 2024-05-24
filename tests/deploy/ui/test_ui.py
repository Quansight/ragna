import socket
import subprocess
import sys
import time

import httpx
import panel as pn
import pytest
from playwright.sync_api import Page, expect

from ragna._utils import timeout_after
from ragna.deploy import Config

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
    config = Config(
        local_root=tmp_local_root,
        assistants=[TestAssistant],
        ui=dict(port=get_available_port()),
        api=dict(port=get_available_port()),
    )
    path = tmp_local_root / "ragna.toml"
    config.to_file(path)
    return config


class Server:
    def __init__(self, config):
        self.config = config
        self.base_url = f"http://{config.ui.hostname}:{config.ui.port}"

    def server_up(self):
        try:
            return httpx.get(self.base_url).is_success
        except httpx.ConnectError:
            return False

    @timeout_after(30)
    def start(self):
        self.proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "ragna",
                "ui",
                "--config",
                self.config.local_root / "ragna.toml",
                "--start-api",
                "--ignore-unavailable-components",
                "--no-open-browser",
            ],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

        while not self.server_up():
            time.sleep(1)

    def stop(self):
        self.proc.kill()
        pn.state.kill_all_servers()


@pytest.fixture
def server(config):
    server = Server(config)
    try:
        server.start()
        yield server
    finally:
        server.stop()


def test_health(server, page: Page) -> None:
    health_url = server.base_url + "/health"
    response = page.goto(health_url)
    assert response.ok


@timeout_after(30)
def get_chats(config, auth_token):
    chats_url = f"http://{config.api.hostname}:{config.api.port}/chats"
    chats = []
    while len(chats) == 0:
        chats = httpx.get(
            chats_url, headers={"Authorization": f"Bearer {auth_token}"}
        ).json()
        time.sleep(1)

    return chats


def test_index(server, config, page: Page) -> None:
    # Index page, no auth
    index_url = server.base_url
    page.goto(index_url)
    expect(page.get_by_role("button", name="Sign In")).to_be_visible()

    # Authorize with no credentials
    page.get_by_role("button", name="Sign In").click()
    expect(page.get_by_role("button", name=" New Chat")).to_be_visible()

    # expect auth token to be set
    cookies = page.context.cookies()
    assert len(cookies) == 1
    cookie = cookies[0]
    assert cookie.get("name") == "auth_token"
    auth_token = cookie.get("value")
    assert auth_token is not None

    # New page button
    new_chat_button = page.get_by_role("button", name=" New Chat")
    expect(new_chat_button).to_be_visible()
    new_chat_button.click()

    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_name = "test.txt"
    document_path = document_root / document_name
    with open(document_path, "w") as file:
        file.write("!\n")

    # File upload selector
    with page.expect_file_chooser() as fc_info:
        page.locator(".fileUpload").click()
    file_chooser = fc_info.value
    file_chooser.set_files(document_path)

    # Upload document and expect to see it listed
    file_list = page.locator(".fileListContainer")
    expect(file_list.first).to_have_text(str(document_name))

    start_chat_button = page.get_by_role("button", name="Start Conversation")
    expect(start_chat_button).to_be_visible()
    start_chat_button.click(delay=5)

    # Document should be in the database
    chats = get_chats(config, auth_token)
    assert len(chats) == 1
    chat = chats[0]
    chat_documents = chat["metadata"]["documents"]
    assert len(chat_documents) == 1
    assert chat_documents[0]["name"] == document_name

    chat_box_row = page.locator(".chat-interface-input-row")
    expect(chat_box_row).to_be_visible()

    chat_box = chat_box_row.get_by_role("textbox")
    expect(chat_box).to_be_visible()

    chat_box.fill("Tell me about the documents")

    chat_button = chat_box_row.get_by_role("button")
    expect(chat_button).to_be_visible()
    chat_button.click()
