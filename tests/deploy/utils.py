import os
import time

from fastapi.testclient import TestClient

from ragna.assistants import RagnaDemoAssistant
from ragna.core._utils import default_user


class TestAssistant(RagnaDemoAssistant):
    def answer(self, prompt, sources, *, multiple_answer_chunks: bool):
        # Simulate a "real" assistant through a small delay. See
        # https://github.com/Quansight/ragna/pull/401#issuecomment-2095851440
        # for why this is needed.
        time.sleep(1e-3)
        content = next(super().answer(prompt, sources))

        if multiple_answer_chunks:
            for chunk in content.split(" "):
                yield f"{chunk} "
        else:
            yield content


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
