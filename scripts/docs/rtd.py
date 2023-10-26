import os

from mkdocs.config.defaults import MkDocsConfig


def on_config(config: MkDocsConfig):
    # Run in strict mode, i.e. fail on warnings, if we are building a non-release
    # version on ReadTheDocs
    if (
        os.environ.get("READTHEDOCS") == "True"
        and os.environ.get("READTHEDOCS_VERSION_TYPE") != "tag"
    ):
        config["strict"] = True
