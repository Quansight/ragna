import platform

import pytest

skip_on_windows = pytest.mark.skipif(
    platform.system() == "Windows", reason="Test is broken skipped on Windows"
)
