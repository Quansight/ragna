import panel as pn
import param

import ragna.ui.styles as ui


class ModalWelcome(pn.viewable.Viewer):
    close_button_callback = param.Callable()

    def __init__(self, **params):
        super().__init__(**params)

    def did_click_on_close_button(self, event):
        if self.close_button_callback is not None:
            self.close_button_callback()

    def __panel__(self):
        close_button = pn.widgets.Button(
            name="Okay, let's go", button_type="primary", min_width=375
        )
        close_button.on_click(self.did_click_on_close_button)

        return pn.Column(
            pn.pane.HTML(
                """<h2>Welcome !</h2>
                         blablabla
                         """,
            ),
            ui.divider(),
            pn.pane.HTML(
                """<b>Ask Away !</b><br />
                         Ragna can answer questions, help you learn, write code, and much more.<br />
                         <br />
                         <b>Another info !</b><br />
                         Lorem ipsum.<br />
                         <br />
                         """
            ),
            close_button,
            min_width=ui.MODAL_WIDTH,
        )
