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
        print("logging out")
        return pn.pane.HTML(
            r"""<script>
                // Get the current path
                var currentPath = window.location.pathname;
                    // Check if the current path contains '/logout'
                    if (currentPath.includes('/logout')) {
                      // Remove '/auth' from the current path
                      var redirectTo = currentPath.replace(/\/logout(\/)?$/, '') + '/';
                      console.log("Redirecting from logout page to home " + redirectTo)
                      // Redirect the user to the new URL
                      window.location.href = redirectTo;
                      document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${redirectTo}";
                    }

            </script>                
            """
        )
