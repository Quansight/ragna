from pathlib import Path
from urllib.parse import urlsplit

import panel as pn
import param

from ragna._utils import handle_localhost_origins
from ragna.deploy import Config

from . import js
from . import styles as ui
from .api_wrapper import ApiWrapper
from .main_page import MainPage

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
    def __init__(self, *, hostname, port, api_url, origins, open_browser):
        super().__init__()
        ui.apply_design_modifiers()
        self.hostname = hostname
        self.port = port
        self.api_url = f"{api_url}/api"
        self.origins = origins
        # FIXME
        self.open_browser = open_browser

    def get_template(self):
        template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="Ragna",
            accent_base_color=ui.MAIN_COLOR,
            theme_toggle=False,
            collapsed_sidebar=True,
            # main_layout=None
            raw_css=[ui.APP_RAW],
            favicon="static/images/ragna_logo.svg",
            css_files=["https://rsms.me/inter/inter.css"],
        )

        template.modal.objects = [
            pn.Column(
                sizing_mode="stretch_both",
            )
        ]

        template.header.append(pn.pane.HTML(js.SHADOWROOT_INDEXING))
        template.header.append(pn.pane.HTML(js.MODAL_MOUSE_UP_FIX))
        template.header.append(pn.pane.HTML(js.CONNECTION_MONITOR))

        return template

    def index_page(self):
        import html
        import pprint

        return pn.pane.HTML(
            html.escape(
                "\n".join(
                    pprint.pformat(item)
                    for item in [pn.state.cookies, pn.state.headers]
                )
            )
        )

        # Unfortunately, we need to parse the cookies from a non-standard header for
        # now. See https://github.com/bokeh/bokeh/issues/13792 for details. If that is
        # resolved, we can just use pn.state.cookies here.
        cookies = dict(
            [
                cookie.strip().split("=")
                for cookie in pn.state.headers["X-Cookie"].split(";")
            ]
        )

        template = self.get_template()
        main_page = MainPage(
            api_wrapper=ApiWrapper(api_url=self.api_url, cookies=cookies),
            template=template,
        )
        template.main.append(main_page)
        return template

    def serve(self):
        print(
            [
                urlsplit(origin).netloc or urlsplit(origin).path
                for origin in self.origins
            ]
        )
        return pn.serve(
            self.index_page,
            address=self.hostname,
            port=self.port,
            threaded=True,
            start=True,
            show=False,
            allow_websocket_origin=[
                urlsplit(origin).netloc or urlsplit(origin).path
                for origin in self.origins
            ],
            # static_dirs={
            #     "/static/imgs": str(IMGS),
            #     "resources": str(RES),
            # },  # "css": str(CSS),
            verbose=True,
            liveness="/health",
        )


def app(*, config: Config, open_browser: bool) -> App:
    return App(
        hostname=config.ui.hostname,
        port=config.ui.port,
        api_url=config.api.url,
        origins=handle_localhost_origins(config.ui.origins),
        open_browser=open_browser,
    )
