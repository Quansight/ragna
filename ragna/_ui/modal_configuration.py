from datetime import datetime, timedelta, timezone

import panel as pn
import param

from . import js
from . import styles as ui
from .components.file_uploader import FileUploader


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


class ChatConfig(param.Parameterized):
    allowed_documents = param.List(default=["TXT"])

    source_storage_name = param.Selector()
    assistant_name = param.Selector()

    chunk_size = param.Integer(
        default=500,
        step=100,
        bounds=(100, 1_000),
    )
    chunk_overlap = param.Integer(
        default=250,
        step=50,
        bounds=(50, 500),
    )

    max_context_tokens = param.Integer(
        step=500,
        bounds=(1, 8000),
        default=4000,
        doc=(
            "Maximum number of context tokens and in turn the number of document chunks "
            "pulled out of the vector database."
        ),
    )

    max_new_tokens = param.Integer(
        default=1_000,
        step=100,
        bounds=(100, 10_000),
    )

    def is_assistant_disabled(self):
        return "Ragna/Demo" in self.assistant_name

    def is_source_storage_disabled(self):
        return "Ragna/Demo" in self.source_storage_name

    def to_params_dict(self):
        result = {}
        if not self.is_assistant_disabled():
            result["max_new_tokens"] = self.max_new_tokens

        if not self.is_source_storage_disabled():
            result["chunk_overlap"] = self.chunk_overlap
            result["chunk_size"] = self.chunk_size
            result["num_tokens"] = self.max_context_tokens

        return result


class ModalConfiguration(pn.viewable.Viewer):
    chat_name = param.String()

    config = param.ClassSelector(class_=ChatConfig, default=None)
    new_chat_ready_callback = param.Callable()
    cancel_button_callback = param.Callable()

    advanced_config_collapsed = param.Boolean(default=True)

    def __init__(self, api_wrapper, **params):
        super().__init__(chat_name=get_default_chat_name(), **params)

        self.api_wrapper = api_wrapper

        upload_endpoints = self.api_wrapper.upload_endpoints()

        self.chat_name_input = pn.widgets.TextInput.from_param(
            self.param.chat_name,
            stylesheets=[ui.BK_INPUT_GRAY_BORDER],
        )
        self.document_uploader = FileUploader(
            [],  # the allowed documents are set in the model_section function
            self.api_wrapper.auth_token,
            upload_endpoints["informations_endpoint"],
        )

        # Most widgets (including those that use from_param) should be placed after the super init call
        self.cancel_button = pn.widgets.Button(
            name="Cancel", button_type="default", min_width=375
        )
        self.cancel_button.on_click(self.cancel_button_callback)

        self.start_chat_button = pn.widgets.Button(
            name="Start Conversation", button_type="primary", min_width=375
        )
        self.start_chat_button.on_click(self.did_click_on_start_chat_button)

        self.upload_files_label = pn.pane.HTML()
        self.change_upload_files_label()

        self.upload_row = pn.Row(
            self.document_uploader,
            sizing_mode="stretch_width",
            stylesheets=[""" :host { margin-bottom: 20px; } """],
        )

        self.got_timezone = False

    def did_click_on_start_chat_button(self, event):
        if not self.document_uploader.can_proceed_to_upload():
            self.change_upload_files_label("missing_file")
        else:
            self.start_chat_button.disabled = True
            self.document_uploader.perform_upload(event, self.did_finish_upload)

    async def did_finish_upload(self, uploaded_documents):
        # at this point, the UI has uploaded the files to the API.
        # We can now start the chat

        try:
            new_chat_id = await self.api_wrapper.start_and_prepare(
                name=self.chat_name,
                documents=uploaded_documents,
                source_storage=self.config.source_storage_name,
                assistant=self.config.assistant_name,
                params=self.config.to_params_dict(),
            )

            self.start_chat_button.disabled = False

            if self.new_chat_ready_callback is not None:
                await self.new_chat_ready_callback(new_chat_id)

        except Exception:
            self.change_upload_files_label("upload_error")
            self.document_uploader.loading = False
            self.start_chat_button.disabled = False

    def change_upload_files_label(self, mode="normal"):
        if mode == "upload_error":
            self.upload_files_label.object = "<b>Upload files</b> (required)<span style='color:red;padding-left:100px;'><b>An error occured. Please try again or contact your administrator.</b></span>"
        elif mode == "missing_file":
            self.upload_files_label.object = (
                "<span style='color:red;'><b>Upload files</b> (required)</span>"
            )
        else:
            self.upload_files_label.object = "<b>Upload files</b> (required)"

    async def model_section(self):
        # prevents re-rendering the section
        if self.config is None:
            # Retrieve the components from the API and build a config object
            components = await self.api_wrapper.get_components()
            # TODO : use the components to set up the default values for the various params

            config = ChatConfig()
            config.allowed_documents = [
                ext[1:].upper() for ext in components["documents"]
            ]

            assistants = [component["title"] for component in components["assistants"]]

            config.param.assistant_name.objects = assistants
            config.assistant_name = assistants[0]

            source_storages = [
                component["title"] for component in components["source_storages"]
            ]
            config.param.source_storage_name.objects = source_storages
            config.source_storage_name = source_storages[0]

            # Now that the config object is set, we can assign it to the param.
            # This will trigger the update of the advanced_config_ui section
            self.config = config
            self.document_uploader.allowed_documents = config.allowed_documents

        return pn.Row(
            pn.Column(
                pn.pane.HTML("<b>Assistants</b>"),
                pn.widgets.Select.from_param(
                    self.config.param.assistant_name,
                    name="",
                    stylesheets=[ui.BK_INPUT_GRAY_BORDER],
                ),
            ),
            pn.Column(
                pn.pane.HTML("<b>Source storage</b>"),
                pn.widgets.Select.from_param(
                    self.config.param.source_storage_name,
                    name="",
                    stylesheets=[ui.BK_INPUT_GRAY_BORDER],
                ),
            ),
        )

    @pn.depends("config", "config.assistant_name", "config.source_storage_name")
    def advanced_config_ui(self):
        if self.config is None:
            return

        disabled_assistant = self.config.is_assistant_disabled()
        disabled_source_storage = self.config.is_source_storage_disabled()

        card = pn.Card(
            pn.Row(
                pn.Column(
                    pn.pane.HTML(
                        """<h2> Retrieval Method</h2>
                            <span>Adjusting these settings requires re-embedding the documents, which may take some time.
                            </span><br />
                                         """
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_size,
                        name="Chunk Size",
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                        disabled=disabled_source_storage,
                        css_classes=["disabled"] if disabled_source_storage else [],
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_overlap,
                        name="Chunk Overlap",
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                        disabled=disabled_source_storage,
                        css_classes=["disabled"] if disabled_source_storage else [],
                    ),
                    margin=(0, 20, 0, 0),
                    width_policy="max",
                ),
                pn.Column(
                    pn.pane.HTML(
                        """<h2> Model Configuration</h2>
                            <span>Changing these parameters alters the output. This might affect accuracy and efficiency.
                            </span><br />
                                         """
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_context_tokens,
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                        disabled=disabled_source_storage,
                        css_classes=["disabled"] if disabled_source_storage else [],
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_new_tokens,
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                        disabled=disabled_assistant,
                        css_classes=["disabled"] if disabled_assistant else [],
                    ),
                    width_policy="max",
                    height_policy="max",
                    margin=(0, 20, 0, 0),
                    styles={
                        "border-left": "1px solid var(--neutral-stroke-divider-rest)"
                    },
                ),
                height=250,
            ),
            collapsed=self.advanced_config_collapsed,
            collapsible=True,
            hide_header=True,
            stylesheets=[ui.SS_ADVANCED_UI_CARD],
        )

        def toggle_card(event):
            if event.old < event.new:
                # This callback is triggered when the card is rerendered,
                # after changing the assistant, for example.
                # This test prevents collapsing the card when it is not needed

                card.collapsed = not card.collapsed
                self.advanced_config_collapsed = card.collapsed

            toggle_button = event.obj

            if card.collapsed:
                toggle_button.name = toggle_button.name.replace("▼", "▶")
            else:
                toggle_button.name = toggle_button.name.replace("▶", "▼")

        toggle_button = pn.widgets.Button(
            name="Advanced Configurations   ▶",
            button_type="light",
            stylesheets=[
                """button.bk-btn { 
                        font-size:13px; 
                        font-weight:600; 
                        padding-left: 0px;
                        color: MAIN_COLOR; 
                }""".replace("MAIN_COLOR", ui.MAIN_COLOR)
            ],
        )

        toggle_button.on_click(toggle_card)

        toggle_button.js_on_click(
            args={"card": card},
            code=js.JS_TOGGLE_CARD,
        )

        return pn.Column(toggle_button, card)

    def __panel__(self):
        return pn.Column(
            pn.pane.HTML(
                f"""<h2>Start a new chat</h2>
                         Let's set up the configurations for your new chat !<br />
                         <script>{js.reset_modal_size(ui.CONFIG_MODAL_WIDTH, ui.CONFIG_MODAL_MIN_HEIGHT)}</script>
                         """,
            ),
            ui.divider(),
            pn.pane.HTML("<b>Chat name</b>"),
            self.chat_name_input,
            ui.divider(),
            self.model_section,
            ui.divider(),
            self.advanced_config_ui,
            ui.divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_height=ui.CONFIG_MODAL_MIN_HEIGHT,
            min_width=ui.CONFIG_MODAL_WIDTH,
            sizing_mode="stretch_both",
            height_policy="max",
        )
