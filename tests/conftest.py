import asyncio
import platform

import pytest

import ragna


@pytest.fixture
def tmp_local_root(tmp_path):
    old = ragna.local_root()
    try:
        yield ragna.local_root(tmp_path)
    finally:
        ragna.local_root(old)


@pytest.fixture(scope="session", autouse=True)
def windows_event_loop_policy():
    # See https://stackoverflow.com/a/66772242
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
