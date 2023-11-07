"""
The tests in this module are only here as a reminder to clean up our code if an issue is
fixed upstream. If you see a test failing here, i.e. an unexpected success, feel free to
remove the offending test after you have cleaned up our code.
"""


import pytest

from ragna._compat import importlib_metadata_package_distributions


@pytest.mark.xfail
def test_pyarrow_dummy_module():
    module_names = {
        module_name
        for module_name, distribution_names in importlib_metadata_package_distributions().items()
        if "pyarrow" in distribution_names
    }
    assert "__dummy__" not in module_names
