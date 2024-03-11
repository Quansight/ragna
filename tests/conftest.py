import pytest

import ragna


@pytest.fixture
def tmp_local_root(tmp_path):
    old = ragna.local_root()
    try:
        yield ragna.local_root(tmp_path)
    finally:
        ragna.local_root(old)
