import os

from fastapi.testclient import TestClient

from ragna.core._utils import default_user
from ragna.deploy._core import make_app


def make_api_app(*, config, ignore_unavailable_components):
    return make_app(
        config,
        api=True,
        ui=False,
        ignore_unavailable_components=ignore_unavailable_components,
        open_browser=False,
    )


def authenticate(client: TestClient) -> None:
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
