from datetime import datetime, timedelta, timezone

import panel as pn
import param

import ragna.ui.js as js


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


class ModalConfiguration(pn.viewable.Viewer):
    chat_configs = param.List()
    chat_name = param.String()
    start_button_callback = param.Callable()
    cancel_button_callback = param.Callable()
    #

    def __init__(self, **params):
        super().__init__(chat_name=get_default_chat_name(), **params)
        # TODO: sort out documents within this class

        self.document_uploader = pn.widgets.FileInput(
            # accept=",".join(get_supported_suffixes()),
            accept=".pdf,.txt",
            multiple=True,
        )

        # Most widgets (including those that use from_param) should be placed after the super init call
        self.cancel_button = pn.widgets.Button(
            name="Cancel", button_type="default", min_width=375
        )
        self.cancel_button.on_click(self.cancel_button_callback)
        self.start_chat_button = pn.widgets.Button(
            name="Start Conversation", button_type="primary", min_width=375
        )
        self.start_chat_button.on_click(self.start_button_callback)

        self.upload_files_label = pn.pane.HTML("<b>Upload files</b> (required)")

        # LoadingSpinner has a property named "visible".
        # But it we set it to visible=False by default, the spinner
        # will never appear, even if we set it to visible=True later.
        # The solution I found is to add/remove the spinner from the
        # panel page.
        self.spinner_upload = pn.indicators.LoadingSpinner(
            value=True,
            name="Uploading ...",
            size=40,
            color="success",
        )

        # Keep this as a row, we add the loading spinner in it later
        self.upload_row = pn.Row(
            self.document_uploader,
        )

        self.got_timezone = False

    def __panel__(self):
        def divider():
            return pn.layout.Divider(styles={"padding": "0em 2em 0em 2em"})

        return pn.Column(
            pn.pane.HTML(
                f"""<h2>Start a new chat</h2>
                         Setup the configurations for your new chat.<br />
                         <script>{js.MODAL_HACK}</script>
                         """,
            ),
            divider(),
            pn.pane.HTML("<b>Chat name</b>"),
            pn.Param(
                self,
                widgets={
                    "chat_name": {"widget_type": pn.widgets.TextInput, "name": ""}
                },
                parameters=["chat_name"],
                show_name=False,
            ),
            divider(),
            *self.chat_configs,
            divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_width=800,
            sizing_mode="stretch_both",
            height_policy="max",
        )
