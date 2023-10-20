import subprocess

from mkdocs.plugins import get_plugin_logger

logger = get_plugin_logger(__name__)


def on_startup(command, dirty):
    result = subprocess.run(["git", "status", "--porcelain"], capture_output=True)
    for line in result.stdout.decode().split("\n"):
        logger.error(line)
