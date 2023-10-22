from pathlib import Path

from urllib.parse import urlsplit

import panel as pn
import param

import ragna.ui.styles as ui

from ragna._utils import get_origins
from ragna.core import Config

from ragna.ui.api_wrapper import ApiWrapper
from ragna.ui.main_page import MainPage

pn.extension(
    loading_spinner="dots",
    loading_color=ui.MAIN_COLOR,
    layout_compatibility="error",
)
pn.config.browser_info = True


HERE = Path(__file__).parent
# CSS = HERE / "css"
IMGS = HERE / "imgs"
RES = HERE / "resources"


class App(param.Parameterized):
    def __init__(self, *, url, api_url):
        super().__init__()
        self.url = url
        self.api_url = api_url

        # TODO : build the Api Wrapper after we have the user's name,
        # and replace the default "User" here
        self.api_wrapper = ApiWrapper(api_url=self.api_url)

    def index_page(self):
        main_page = MainPage(api_wrapper=self.api_wrapper)
        return main_page.page()

    def health_page(self):
        return pn.pane.HTML("<h1>Ok</h1>")

    def serve(self):
        # logging.init(log_level=args.log_level)

        all_pages = {"/": self.index_page, "/health": self.health_page}
        titles = {"/": "Home"}

        pn.serve(
            all_pages,
            titles=titles,
            port=urlsplit(self.url).port,
            admin=True,
            start=True,
            location=True,
            show=False,
            keep_alive=30 * 1000,  # 30s
            autoreload=True,
            profiler="pyinstrument",
            allow_websocket_origin=[
                urlsplit(origin).netloc for origin in get_origins(self.url)
            ],
            static_dirs={"imgs": str(IMGS), "resources": str(RES)},  # "css": str(CSS),
        )


def app(config: Config) -> App:
    return App(url=config.ui.url, api_url=config.api.url)
