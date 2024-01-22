import panel as pn
import param

from ragna.deploy._ui.js_utils import redirect_script


class LogoutPage(pn.viewable.Viewer, param.Parameterized):
    def __init__(self, api_wrapper, **params):
        super().__init__(**params)
        self.api_wrapper = api_wrapper

        self.api_wrapper.auth_token = None

    def __panel__(self):
        # Usually, we do a redirect this way :
        # >>> pn.state.location.param.update(reload=True, pathname="/")
        # But it only works once the page is fully loaded.
        # So we render a javascript redirect instead.

        # To remove the token from the cookie, we have to force its expiry date to the past.
        return redirect_script(remove="logout", append="/", remove_auth_cookie=True)
