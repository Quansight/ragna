from datetime import datetime, timedelta, timezone

import panel as pn
import param

import ragna.ui.js as js
import ragna.ui.styles as ui
from ragna.ui.components.file_uploader import FileUploader


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


class ModalConfiguration(pn.viewable.Viewer):
    chat_name = param.String()
    start_button_callback = param.Callable()
    cancel_button_callback = param.Callable()
    #
    source_storage_name = param.Selector()
    assistant_name = param.Selector()

    def __init__(self, api_wrapper, **params):
        super().__init__(chat_name=get_default_chat_name(), **params)

        self.api_wrapper = api_wrapper

        upload_endpoints = self.api_wrapper.upload_endpoints()

        informations_endpoint = upload_endpoints["informations_endpoint"]
        upload_endpoint = upload_endpoints["upload_endpoint"]

        self.document_uploader = FileUploader(
            self.api_wrapper.user, informations_endpoint, upload_endpoint
        )

        # Most widgets (including those that use from_param) should be placed after the super init call
        self.cancel_button = pn.widgets.Button(
            name="Cancel", button_type="default", min_width=375
        )
        self.cancel_button.on_click(self.cancel_button_callback)

        self.start_chat_button = pn.widgets.Button(
            name="Start Conversation", button_type="primary", min_width=375
        )
        # self.start_chat_button.on_click(self.start_button_callback)
        self.start_chat_button.on_click(self.did_click_on_start_chat_button)

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

    def did_click_on_start_chat_button(self, event):
        def did_finish_upload(uploaded_documents):
            print("did finish upload", uploaded_documents)

        self.document_uploader.perform_upload(event, did_finish_upload)

    async def model_section(self):
        components = await self.api_wrapper.get_components_async()

        self.param.assistant_name.objects = components["assistants"]
        self.param.source_storage_name.objects = components["source_storages"]

        if len(components["assistants"]) > 0:
            self.assistant_name = components["assistants"][0]

        if len(components["source_storages"]) > 0:
            self.source_storage_name = components["source_storages"][0]

        return pn.Row(
            pn.Column(
                pn.pane.HTML("<b>Model</b>"),
                pn.widgets.Select.from_param(self.param.assistant_name, name=""),
            ),
            pn.Column(
                pn.pane.HTML("<b>Source storage</b>"),
                pn.widgets.Select.from_param(self.param.source_storage_name, name=""),
            ),
        )

    def __panel__(self):
        def divider():
            return pn.layout.Divider(styles={"padding": "0em 2em 0em 2em"})

        return pn.Column(
            pn.pane.HTML(
                f"""<h2>Start a new chat</h2>
                         Let's set up the configurations for your new chat !<br />
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
            self.model_section,
            divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_width=ui.MODAL_WIDTH,
            sizing_mode="stretch_both",
            height_policy="max",
        )
