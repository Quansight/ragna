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
    def __init__(self, *, url, api_url, origins):
        super().__init__()
        self.url = url
        self.api_url = api_url
        self.origins = origins

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
            css_files=["https://rsms.me/", "https://rsms.me/inter/inter.css"],
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
            print("auth_token not found in pn.state.cookies")
            return pn.pane.HTML(
                """
                <script>
                var currentPath = window.location.pathname; // Get the current path
                var redirectTo = currentPath + 'auth';
                console.log("Redirecting to auth page: " + redirectTo)
                window.location.href = redirectTo;
                </script>
                
                """
            )

        try:
            api_wrapper = ApiWrapper(
                api_url=self.api_url, auth_token=pn.state.cookies["auth_token"]
            )
        except RagnaAuthTokenExpiredException:
            # If the token has expired / is invalid, we redirect to the logout page.
            # The logout page will delete the cookie and redirect to the auth page.
            print("auth_token expired redirecting to logout page")
            return pn.pane.HTML(
                """<script>
                var currentPath = window.location.pathname; // Get the current path
                var redirectTo = currentPath + 'logout';
                console.log("Redirecting to logout page: " + redirectTo)
                window.location.href = redirectTo;
                </script>                
                """
            )

        print("all good, going to main page")
        template = self.get_template()
        main_page = MainPage(api_wrapper=api_wrapper, template=template)
        template.main.append(main_page)
        return template

    def auth_page(self):
        # If the user is already authenticated, we receive the auth token in the cookie.
        # in that case, redirect to the index page.
        if "auth_token" in pn.state.cookies:
            print("auth token found in cookies")
            # Usually, we do a redirect this way :
            # >>> pn.state.location.param.update(reload=True, pathname="/")
            # But it only works once the page is fully loaded.
            # So we render a javascript redirect instead.
            return pn.pane.HTML(
                r"""
                <script>
                var currentPath = window.location.pathname; // Get the current path

                    // Check if the current path contains '/auth'
                    if (currentPath.includes('/auth')) {
                      // Remove '/auth' from the current path
                      var redirectTo = currentPath.replace(/\/auth(\/)?$/, '') + '/';
                        console.log("redirectTo")
                        console.log(redirectTo)
                        console.log("redirectTo end")
                        console.log("Redirecting to home page " + redirectTo)
                      // Redirect the user to the new URL
                      window.location.href = redirectTo;
                    }
                </script>
                """
            )

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
            port=urlsplit(self.url).port,
            admin=True,
            start=True,
            location=True,
            show=False,
            keep_alive=30 * 1000,  # 30s
            autoreload=True,
            profiler="pyinstrument",
            allow_websocket_origin=[urlsplit(origin).netloc for origin in self.origins],
            static_dirs={"imgs": str(IMGS), "resources": str(RES)},  # "css": str(CSS),
            # prefix="/user/aktech/custom-2-ragna-36d1e87"
        )


def app(config: Config) -> App:
    return App(
        url=config.ui.url,
        api_url=config.api.url,
        origins=handle_localhost_origins(config.ui.origins),
    )
