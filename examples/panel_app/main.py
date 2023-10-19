# imports to check if the API is running
import asyncio
import contextlib
import time

import httpx
from ragna.core import Config
from ragna.ui.app import App as RagnaUI

# config = Config.builtin()
config = Config.demo()


async def check_ragna_api():
    client = httpx.AsyncClient()

    timeout = 10
    start = time.time()
    while (time.time() - start) < timeout:
        with contextlib.suppress(httpx.ConnectError):
            response = await client.get(f"{config.api.url}/")
            if response.is_success:
                break

        time.sleep(0.5)
    else:
        raise RuntimeError("Unable to connect to the Ragna REST API")

    return True


def main():
    # First, ensure the API is running
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(check_ragna_api())
    print(result)

    # Then, build and start the UI
    url, port = config.ui.url.rsplit(":", 1)
    url = url.split("//")[-1]

    # Since localhost is an alias for 127.0.0.1, we allow both so users and developers
    # don't need to worry about it.
    allowed_origins = [url, f"{url}:{port}"]
    if url == "127.0.0.1":
        allowed_origins.append("localhost")
        allowed_origins.append(f"localhost:{port}")
    elif url == "localhost":
        allowed_origins.append("127.0.0.1")
        allowed_origins.append(f"127.0.0.1:{port}")

    ragna_ui = RagnaUI(
        url=url.split("//")[-1],
        port=int(port),
        api_url=config.api.url,
        allowed_origins=allowed_origins,
    )

    ragna_ui.serve()


if __name__ == "__main__":
    main()
