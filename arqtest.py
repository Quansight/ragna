import asyncio
import time

from arq import create_pool
from arq.connections import RedisSettings
from httpx import AsyncClient


async def download_content(ctx, url):
    ctx["session"]
    await asyncio.sleep(0.5)
    # time.sleep((len(url) - 17))
    await asyncio.sleep((len(url) - 17) + 0.2)
    time.sleep(0.5)
    return len(url)


async def startup(ctx):
    ctx["session"] = AsyncClient()


async def shutdown(ctx):
    await ctx["session"].aclose()


async def main():
    queue = await create_pool(RedisSettings(), default_queue_name="ragna:queue")
    for url in ("https://facebook.com", "https://microsoft.com", "https://github.com"):
        await queue.enqueue_job("download_content", url)


# WorkerSettings defines the settings to use when creating the work,
# it's used by the arq cli.
# For a list of available settings, see https://arq-docs.helpmanual.io/#arq.worker.Worker
class WorkerSettings:
    queue_name = "ragna:queue"
    functions = [download_content]
    on_startup = startup
    on_shutdown = shutdown
    poll_delay = 0.1


if __name__ == "__main__":
    asyncio.run(main())
    # worker = Worker(
    #     functions=[download_content],
    #     on_startup=startup,
    #     on_shutdown=shutdown,
    #     poll_delay=0.1,
    # )
    # worker.run()
    # print()
