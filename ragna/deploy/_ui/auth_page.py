import panel as pn
import param


class AuthPage(pn.viewable.Viewer, param.Parameterized):
    feedback_message = param.String(default=None)

    custom_js = param.String(default="")

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)
        self.api_wrapper = api_wrapper

        self.main_layout = None

        self.login_input = pn.widgets.TextInput(
            name="Email",
            css_classes=["auth_login_input"],
        )
        self.password_input = pn.widgets.PasswordInput(
            name="Password",
            css_classes=["auth_password_input"],
        )

    async def perform_login(self, event=None):
        self.main_layout.loading = True

        home_path = pn.state.location.pathname.rstrip("/").rstrip("auth")
        try:
            authed = await self.api_wrapper.auth(
                self.login_input.value, self.password_input.value
            )

            if authed:
                # Sets the cookie on the JS side
                self.custom_js = f""" document.cookie = "auth_token={self.api_wrapper.auth_token}; path:{home_path}";  """

        except Exception:
            authed = False

        if authed:
            # perform redirect
            pn.state.location.param.update(reload=True, pathname=home_path)
        else:
            self.feedback_message = "Authentication failed. Please retry."

        self.main_layout.loading = False

    @pn.depends("feedback_message")
    def display_error_message(self):
        if self.feedback_message is None:
            return None
        else:
            return pn.pane.HTML(
                f"""<div class="auth_error">{self.feedback_message}</div>""",
                css_classes=["auth_error"],
            )

    @pn.depends("custom_js")
    def wrapped_custom_js(self):
        return pn.pane.HTML(
            f""" 
            <script>
                {self.custom_js}
            </script
            """,
        )

    def __panel__(self):
        login_button = pn.widgets.Button(
            name="Sign In",
            button_type="primary",
            css_classes=["auth_login_button"],
        )
        login_button.on_click(self.perform_login)

        self.main_layout = pn.Column(
            self.wrapped_custom_js,
            pn.pane.HTML(
                "<h1>Log In</h1>",
                css_classes=["auth_title"],
            ),
            self.display_error_message,
            self.login_input,
            self.password_input,
            pn.pane.HTML("<br />"),
            login_button,
            css_classes=["auth_page_main_layout"],
        )

        return self.main_layout
