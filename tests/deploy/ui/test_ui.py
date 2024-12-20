import contextlib
import multiprocessing
import time

import httpx
import pytest
from playwright.sync_api import expect

from ragna._cli.core import deploy as _deploy
from ragna.deploy import Config
from tests.deploy.utils import TestAssistant
from tests.utils import get_available_port


@contextlib.contextmanager
def deploy(config):
    process = multiprocessing.Process(
        target=_deploy,
        kwargs=dict(
            config=config,
            api=False,
            ui=True,
            ignore_unavailable_components=False,
            open_browser=False,
        ),
    )
    try:
        process.start()

        client = httpx.Client(base_url=config._url)

        # FIXME: create a generic utility for this
        def server_available() -> bool:
            try:
                return client.get("/health").is_success
            except httpx.ConnectError:
                return False

        while not server_available():
            time.sleep(0.1)

        yield process
    finally:
        process.terminate()
        process.join()
        process.close()


@pytest.fixture
def default_config(tmp_local_root):
    return Config(
        local_root=tmp_local_root,
        assistants=[TestAssistant],
        port=get_available_port(),
    )


@pytest.fixture
def index_page(default_config, page):
    config = default_config
    with deploy(default_config):
        page.goto(f"http://{config.hostname}:{config.port}/ui")
        yield page


def test_start_chat(index_page, tmp_path) -> None:
    # expect(page.get_by_role("button", name="Sign In")).to_be_visible()

    # # Authorize with no credentials
    # page.get_by_role("button", name="Sign In").click()
    # expect(page.get_by_role("button", name=" New Chat")).to_be_visible()
    #
    # # expect auth token to be set
    # cookies = page.context.cookies()
    # assert len(cookies) == 1
    # cookie = cookies[0]
    # assert cookie.get("name") == "auth_token"
    # auth_token = cookie.get("value")
    # assert auth_token is not None

    # New page button
    new_chat_button = index_page.get_by_role("button", name=" New Chat")
    expect(new_chat_button).to_be_visible()
    new_chat_button.click()

    # document_name = "test.txt"
    # document_path = tmp_path / document_name
    # with open(document_path, "w") as file:
    #     file.write("!\n")

    # # File upload selector
    # with index_page.expect_file_chooser() as fc_info:
    #     index_page.locator(".fileUpload").click()
    # file_chooser = fc_info.value
    # file_chooser.set_files(document_path)

    # # Upload document and expect to see it listed
    # file_list = page.locator(".fileListContainer")
    # expect(file_list.first).to_have_text(str(document_name))
    #
    # chat_dialog = page.get_by_role("dialog")
    # expect(chat_dialog).to_be_visible()
    # start_chat_button = page.get_by_role("button", name="Start Conversation")
    # expect(start_chat_button).to_be_visible()
    # time.sleep(0.5)  # hack while waiting for button to be fully clickable
    # start_chat_button.click(delay=5)
    #
    # chat_box_row = page.locator(".chat-interface-input-row")
    # expect(chat_box_row).to_be_visible()
    #
    # chat_box = chat_box_row.get_by_role("textbox")
    # expect(chat_box).to_be_visible()
    #
    # # Document should be in the database
    # chats_url = f"http://{config.api.hostname}:{config.api.port}/chats"
    # chats = httpx.get(
    #     chats_url, headers={"Authorization": f"Bearer {auth_token}"}
    # ).json()
    # assert len(chats) == 1
    # chat = chats[0]
    # chat_documents = chat["metadata"]["documents"]
    # assert len(chat_documents) == 1
    # assert chat_documents[0]["name"] == document_name
    #
    # chat_box.fill("Tell me about the documents")
    #
    # chat_button = chat_box_row.get_by_role("button")
    # expect(chat_button).to_be_visible()
    # chat_button.click()
