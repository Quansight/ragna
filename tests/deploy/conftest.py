import contextlib
import json

import httpx
import pytest


@pytest.fixture(scope="package", autouse=True)
def enhance_raise_for_status(package_mocker):
    raise_for_status = httpx.Response.raise_for_status

    def enhanced_raise_for_status(self):
        __tracebackhide__ = True

        try:
            return raise_for_status(self)
        except httpx.HTTPStatusError as error:
            content = None
            with contextlib.suppress(Exception):
                content = error.response.read()
                content = content.decode()
                content = "\n" + json.dumps(json.loads(content), indent=2)

            if content is None:
                raise error

            message = f"{error}\nResponse content: {content}"
            raise httpx.HTTPStatusError(
                message, request=error.request, response=error.response
            ) from None

    yield package_mocker.patch(
        ".".join(
            [
                httpx.Response.__module__,
                httpx.Response.__name__,
                raise_for_status.__name__,
            ]
        ),
        new=enhanced_raise_for_status,
    )
