import contextlib
import time

from fastapi.testclient import TestClient

from ragna.assistants import RagnaDemoAssistant
from ragna.deploy._auth import SessionMiddleware
from ragna.deploy._core import make_app


class TestAssistant(RagnaDemoAssistant):
    def answer(self, messages, *, multiple_answer_chunks: bool = True):
        # Simulate a "real" assistant through a small delay. See
        # https://github.com/Quansight/ragna/pull/401#issuecomment-2095851440
        # for why this is needed.
        #
        # Note: multiple_answer_chunks is given a default value here to satisfy
        # the tests in deploy/ui/test_ui.py. This can be removed if TestAssistant
        # is ever removed from that file.
        time.sleep(1e-3)
        content = next(super().answer(messages))

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
    client.get("/login", follow_redirects=True).raise_for_status()
    assert SessionMiddleware._COOKIE_NAME in client.cookies


@contextlib.contextmanager
def make_api_client(*, config, ignore_unavailable_components):
    with TestClient(
        make_api_app(
            config=config,
            ignore_unavailable_components=ignore_unavailable_components,
        )
    ) as client:
        authenticate_with_api(client)
        yield client
