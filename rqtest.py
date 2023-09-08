import asyncio
import time


async def foo():
    await asyncio.sleep(2)
    time.sleep(2)
    return 1


async def bar():
    baz = await foo()
    print(baz)


print(bar())
