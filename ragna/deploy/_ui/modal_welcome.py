import panel as pn
import param

from . import js
from . import styles as ui


class ModalWelcome(pn.viewable.Viewer):
    close_button_callback = param.Callable()

    def __init__(self, **params):
        super().__init__(**params)

    def did_click_on_close_button(self, event):
        if self.close_button_callback is not None:
            self.close_button_callback()

    def __panel__(self):
        close_button = pn.widgets.Button(
            name="Okay, let's go",
            button_type="primary",
            stylesheets=[""" :host { width:35%; margin-left:60%; }"""],
        )
        close_button.on_click(self.did_click_on_close_button)

        return pn.Column(
            pn.pane.HTML(
                f"""<script>{js.reset_modal_size(ui.WELCOME_MODAL_WIDTH, ui.WELCOME_MODAL_HEIGHT)}</script>"""
                + """<h2>Welcome !</h2><br />
                        Ragna is a RAG Orchestration Framework.<br />
                        With its UI, select and configure LLMs, upload documents, and chat with the LLM.<br />
                        <br />
                        Use Ragna UI out-of-the-box, as a daily-life interface with your favorite AI, <br />
                        or as a reference to build custom web applications.
                        <br /><br /><br />
                """
            ),
            close_button,
            width=ui.WELCOME_MODAL_WIDTH,
            height=ui.WELCOME_MODAL_HEIGHT,
            sizing_mode="fixed",
        )
