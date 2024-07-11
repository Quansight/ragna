import os
import time

from fastapi.testclient import TestClient

from ragna.assistants import RagnaDemoAssistant
from ragna.core._utils import default_user
from ragna.deploy._core import make_app


class TestAssistant(RagnaDemoAssistant):
    def answer(self, prompt, sources, *, multiple_answer_chunks: bool = True):
        # Simulate a "real" assistant through a small delay. See
        # https://github.com/Quansight/ragna/pull/401#issuecomment-2095851440
        # for why this is needed.
        #
        # Note: multiple_answer_chunks is given a default value here to satisfy
        # the tests in deploy/ui/test_ui.py. This can be removed if TestAssistant
        # is ever removed from that file.
        time.sleep(1e-3)
        content = next(super().answer(prompt, sources))

        if multiple_answer_chunks:
            for chunk in content.split(" "):
                yield f"{chunk} "
        else:
            yield content


def make_api_app(*, config, ignore_unavailable_components):
    return make_app(
        config,
        api=True,
        ui=False,
        ignore_unavailable_components=ignore_unavailable_components,
        open_browser=False,
    )


def authenticate_with_api(client: TestClient) -> None:
    return
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
