import json
from pathlib import Path

from fastapi.openapi.utils import get_openapi
from mkdocs.config.defaults import MkDocsConfig

from ragna._api import api
from ragna.core import Rag

HERE = Path(__file__).parent
DOCS_ROOT = HERE.parent


def on_pre_build(config: MkDocsConfig) -> None:
    app = api(Rag(load_components=False))
    openapi_json = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    with open(DOCS_ROOT / "references" / "openapi.json", "w") as file:
        json.dump(openapi_json, file)
