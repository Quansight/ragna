import pathlib

import pytest
from mktestdocs import check_md_file


@pytest.mark.parametrize("path", pathlib.Path("docs").glob("**/*.md"), ids=str)
def test_files_good(mocker, path):
    mocker.patch("builtins.open", mocker.mock_open())

    # FIXME: The REST API tutorial uses await outside sync functions
    # this would work in a Jupyter Notebook, but not in a Python script
    # We'll also need to have the API running to test this properly.
    if path == pathlib.Path("docs/tutorials/rest-api.md"):
        with pytest.raises(SyntaxError, match="'await' outside function"):
            check_md_file(path, memory=True)
    else:
        check_md_file(path, memory=True)
