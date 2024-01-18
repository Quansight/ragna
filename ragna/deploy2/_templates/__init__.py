from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent)


def template_response():
    pass


TemplateResponse = templates.TemplateResponse
