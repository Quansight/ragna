import platform

import pytest

skip_on_windows = pytest.mark.skipif(platform.system() == "Windows")
