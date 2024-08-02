from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

ENVIRONMENT = Environment(loader=FileSystemLoader(Path(__file__).parent))


def render(template: str, **context: Any) -> str:
    template = ENVIRONMENT.get_template(template)
    return template.render(**context)
