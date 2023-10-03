# imports to check if the API is running
import asyncio
import contextlib
import time

import httpx
from ragna import demo_config

# imports to run the actual UI
from ragna.ui.ragna_ui import RagnaUI


async def check_ragna_api():
    client = httpx.AsyncClient()

    timeout = 10
    start = time.time()
    while (time.time() - start) < timeout:
        with contextlib.suppress(httpx.ConnectError):
            response = await client.get(f"{demo_config.ragna_api_url}/health")
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

    ragna_ui = RagnaUI(
        # demo_config.ragna_ui_url
        url="localhost",
        port=5007,
        api_url=demo_config.ragna_api_url,
    )

    ragna_ui.serve()


if __name__ == "__main__":
    main()
