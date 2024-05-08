import os

import pytest
from fastapi.testclient import TestClient
from playwright.sync_api import expect, sync_playwright

from ragna.assistants import RagnaDemoAssistant
from ragna.core._utils import default_user
from ragna.deploy import Config
from ragna.deploy._api import app as api_app
from ragna.deploy._ui import app as ui_app


def authenticate(client: TestClient) -> None:
    username = default_user()
    token = (
        client.post(
            "/token",
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
    client.headers["Authorization"] = f"Bearer {token}"


class TestAssistant(RagnaDemoAssistant):
    def answer(self, prompt, sources, *, multiple_answer_chunks: bool):
        content = next(super().answer(prompt, sources))

        if multiple_answer_chunks:
            for chunk in content.split(" "):
                yield f"{chunk} "
        else:
            yield content


@pytest.fixture(scope="function")
def config(tmp_local_root):
    return Config(local_root=tmp_local_root, assistants=[TestAssistant])


@pytest.fixture(scope="function")
def server(config, open_browser=False):
    document_root = config.local_root / "documents"
    document_root.mkdir()
    document_path = document_root / "test.txt"
    with open(document_path, "w") as file:
        file.write("!\n")

    with TestClient(
        api_app(config=config, ignore_unavailable_components=True)
    ) as client:
        authenticate(client)

        server = ui_app(config=config, open_browser=open_browser)
        server.serve()

        yield server


def test_ui(server) -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        url = server.origins[0]
        page.goto(url)
        expect(page.get_by_role("button", name="Sign In")).to_be_visible()
        page.get_by_role("button", name="Sign In").click()
        expect(page.get_by_role("button", name=" New Chat")).to_be_visible()
        # page.locator("div").filter(
        #     has_text=re.compile(r"^Source storageChromaLanceDBRagna/DemoSourceStorage$")
        # ).get_by_role("combobox").select_option("LanceDB")
        # page.get_by_role("button", name="Advanced Configurations ▶").click()
        # page.locator("#fileUpload-p2365").click()

        # ---------------------
        context.close()
        browser.close()
