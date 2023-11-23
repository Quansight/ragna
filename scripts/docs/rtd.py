import os

from mkdocs.plugins import get_plugin_logger

logger = get_plugin_logger(__file__)

# https://docs.readthedocs.io/en/stable/reference/environment-variables.html
RTD_ENV_VARS = {
    (name := f"READTHEDOCS{postfix}"): os.environ.get(name)
    for postfix in [
        "",
        "_PROJECT",
        "_LANGUAGE",
        "_VERSION",
        "_VERSION_NAME",
        "_VERSION_TYPE",
        "_VIRTUALENV_PATH",
        "_OUTPUT",
        "_CANONICAL_URL",
        "_GIT_CLONE_URL",
        "_GIT_IDENTIFIER",
        "_GIT_COMMIT_HASH",
    ]
}

RTD = RTD_ENV_VARS["READTHEDOCS"] == "True"


def on_startup(command, dirty):
    if not RTD:
        return

    for name, value in RTD_ENV_VARS.items():
        logger.info(f"{name}={value}")
