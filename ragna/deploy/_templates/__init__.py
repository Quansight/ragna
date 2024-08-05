import contextlib
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

ENVIRONMENT = Environment(loader=FileSystemLoader(Path(__file__).parent))


def render(template: str, **context: Any) -> str:
    with contextlib.suppress(TemplateNotFound):
        css_template = ENVIRONMENT.get_template(str(Path(template).with_suffix(".css")))
        context["__template_css__"] = css_template.render(**context)

    template = ENVIRONMENT.get_template(template)
    return template.render(**context)
