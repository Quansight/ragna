import panel as pn
import param

from . import styles as ui

# TODO Move this into a CSS file
login_inputs_stylesheets = """

:host {
    width:100%;
    margin-left:0px;
    margin-right:0px;
}

label {
    font-weight: 600;
    font-size: 16px;
}

input {
    background-color: white !important;
}

"""


class AuthPage(pn.viewable.Viewer, param.Parameterized):
    feedback_message = param.String(default=None)

    custom_js = param.String(default="")

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)
        self.api_wrapper = api_wrapper

        self.main_layout = None

        self.login_input = pn.widgets.TextInput(
            name="Email",
            stylesheets=[login_inputs_stylesheets, ui.BK_INPUT_GRAY_BORDER],
        )
        self.password_input = pn.widgets.PasswordInput(
            name="Password",
            stylesheets=[login_inputs_stylesheets, ui.BK_INPUT_GRAY_BORDER],
        )

    async def perform_login(self, event=None):
        self.main_layout.loading = True

        try:
            authed = await self.api_wrapper.auth(
                self.login_input.value, self.password_input.value
            )

            if authed:
                # Sets the cookie on the JS side
                self.custom_js = f""" document.cookie = "auth_token={self.api_wrapper.auth_token}; path:/";  """

        except Exception:
            authed = False

        if authed:
            # perform redirect
            pn.state.location.param.update(reload=True, pathname="/")
        else:
            self.feedback_message = "Authentication failed. Please retry."

        self.main_layout.loading = False

    @pn.depends("feedback_message")
    def display_error_message(self):
        if self.feedback_message is None:
            return None
        else:
            return pn.pane.HTML(
                f"""<div class="error">{self.feedback_message}</div>""",
                stylesheets=[
                    """
                                             :host { 
                                                width:100%;
                                                margin-left:0px;
                                                margin-right:0px;
                                             }  
                                             
                                             div.error { 
                                                width:100%; 
                                                color:red; 
                                                text-align:center;
                                                font-weight: 600;
                                                font-size: 16px;
                                             } """
                ],
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
            stylesheets=[
                """ :host { 
                                                                width:100%;
                                                                margin-left:0px;
                                                                margin-right:0px;
                                                       } """
            ],
        )
        login_button.on_click(self.perform_login)

        self.main_layout = pn.Column(
            self.wrapped_custom_js,
            pn.pane.HTML(
                "<h1>Log In</h1>",
                stylesheets=[
                    """ :host { 
                                                width:100%;
                                                margin-left:0px;
                                                margin-right:0px;
                                                text-align:center;
                                            } 
                                         h1 { 
                                            font-weight: 600;
                                            font-size: 24px;
                                         }
                                         """
                ],
            ),
            self.display_error_message,
            self.login_input,
            self.password_input,
            pn.pane.HTML("<br />"),
            login_button,
            stylesheets=[
                """ :host { 
                                    background-color:white;
                                    /*background-color:gold;*/
                                    border-radius: 5px;
                                    box-shadow: lightgray 0px 0px 10px;
                                    padding: 0 25px 0 25px;
                             
                                    width:30%;
                                    min-width:360px;
                                    max-width:430px;
                                    
                                    margin-left: auto;
                                    margin-right: auto;
                                    margin-top: 10%;

                              }
                             :host > div {
                                margin-bottom: 10px;
                                margin-top: 10px;
                             }

                             .bk-panel-models-layout-Column {
                                width:100%;
                             }
                             
                             """
            ],
        )

        return self.main_layout
