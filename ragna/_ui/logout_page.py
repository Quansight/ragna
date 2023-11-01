import panel as pn
import param


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
        return pn.pane.HTML(
            """<script>
                            document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/";
                            window.location.href = '/'; 
                            </script> """
        )
