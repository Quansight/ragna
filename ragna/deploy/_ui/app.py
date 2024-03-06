from pathlib import Path
from urllib.parse import urlsplit

import panel as pn
import param

from ragna._utils import handle_localhost_origins
from ragna.deploy import Config

from . import js
from . import styles as ui
from .api_wrapper import ApiWrapper, RagnaAuthTokenExpiredException
from .auth_page import AuthPage
from .js_utils import redirect_script
from .logout_page import LogoutPage
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
        self.api_url = api_url
        self.origins = origins
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
            favicon="imgs/ragna_logo.svg",
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
        if "auth_token" not in pn.state.cookies:
            return redirect_script(remove="", append="auth")

        try:
            api_wrapper = ApiWrapper(
                api_url=self.api_url, auth_token=pn.state.cookies["auth_token"]
            )
        except RagnaAuthTokenExpiredException:
            # If the token has expired / is invalid, we redirect to the logout page.
            # The logout page will delete the cookie and redirect to the auth page.
            return redirect_script(remove="", append="logout")

        template = self.get_template()
        main_page = MainPage(api_wrapper=api_wrapper, template=template)
        template.main.append(main_page)
        return template

    def auth_page(self):
        # If the user is already authenticated, we receive the auth token in the cookie.
        # in that case, redirect to the index page.
        if "auth_token" in pn.state.cookies:
            # Usually, we do a redirect this way :
            # >>> pn.state.location.param.update(reload=True, pathname="/")
            # But it only works once the page is fully loaded.
            # So we render a javascript redirect instead.
            return redirect_script(remove="auth")

        template = self.get_template()
        auth_page = AuthPage(api_wrapper=ApiWrapper(api_url=self.api_url))
        template.main.append(auth_page)
        return template

    def logout_page(self):
        template = self.get_template()
        logout_page = LogoutPage(api_wrapper=ApiWrapper(api_url=self.api_url))
        template.main.append(logout_page)
        return template

    def health_page(self):
        return pn.pane.HTML("<h1>Ok</h1>")

    def serve(self):
        all_pages = {
            "/": self.index_page,
            "/auth": self.auth_page,
            "/logout": self.logout_page,
            "/health": self.health_page,
        }
        titles = {"/": "Home"}

        pn.serve(
            all_pages,
            titles=titles,
            address=self.hostname,
            port=self.port,
            admin=True,
            start=True,
            location=True,
            show=self.open_browser,
            keep_alive=30 * 1000,  # 30s
            autoreload=True,
            profiler="pyinstrument",
            allow_websocket_origin=[urlsplit(origin).netloc for origin in self.origins],
            static_dirs={"imgs": str(IMGS), "resources": str(RES)},  # "css": str(CSS),
        )


def app(*, config: Config, open_browser: bool) -> App:
    return App(
        hostname=config.ui.hostname,
        port=config.ui.port,
        api_url=config.api.url,
        origins=handle_localhost_origins(config.ui.origins),
        open_browser=open_browser,
    )
