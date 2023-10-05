from pathlib import Path

import panel as pn
import param

import ragna.ui.styles as ui

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


class RagnaUI(param.Parameterized):
    def __init__(self, url="localhost", port=5007, api_url="localhost:31476"):
        super().__init__()
        self.url = url
        self.port = port
        self.api_url = api_url

        # TODO : build the Api Wrapper after we have the user's name,
        # and replace the default "User" here
        self.api_wrapper = ApiWrapper(api_url=self.api_url, user="User")

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
            port=self.port,
            admin=True,
            start=True,
            location=True,
            show=False,
            keep_alive=30 * 1000,  # 30s
            autoreload=True,
            profiler="pyinstrument",
            allow_websocket_origin=[self.url, f"{self.url}:{self.port}"],
            static_dirs={"imgs": str(IMGS)},  # "css": str(CSS),
        )
