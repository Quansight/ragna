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


supported_document_dbs = ["foo", "bar"]


def get_supported_models():
    return {"foo": ["bar", "baz"], "bar": ["foo", "baz"], "baz": ["foo", "bar"]}


class ChatConfig(param.Parameterized):
    source_storage_name = param.Selector()
    assistant_name = param.Selector()

    document_db_name = param.Selector(
        objects=supported_document_dbs,
        allow_None=False,
        default=supported_document_dbs[0],
    )

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

    llm_name = param.Selector(
        objects=[
            f"{organization}/{model}"
            for organization, models in get_supported_models().items()
            for model in models
        ],
        allow_None=False,
    )
    max_context_tokens = param.Integer(
        step=500,
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


class ModalConfiguration(pn.viewable.Viewer):
    chat_name = param.String()
    new_chat_ready_callback = param.Callable()
    cancel_button_callback = param.Callable()

    def __init__(self, api_wrapper, **params):
        super().__init__(chat_name=get_default_chat_name(), **params)

        self.api_wrapper = api_wrapper

        self.config = ChatConfig()

        upload_endpoints = self.api_wrapper.upload_endpoints()

        self.document_uploader = FileUploader(
            self.api_wrapper.token,
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

        self.upload_files_label = pn.pane.HTML("<b>Upload files</b> (required)")

        # Keep this as a row, we add the loading spinner in it later
        self.upload_row = pn.Row(
            self.document_uploader,
            sizing_mode="stretch_width",
            stylesheets=[""" :host { margin-bottom: 20px; } """],
        )

        self.got_timezone = False

    def did_click_on_start_chat_button(self, event):
        if not self.document_uploader.can_proceed_to_upload():
            self.upload_files_label.object = (
                "<span style='color:red;'><b>Upload files</b> (required)</span>"
            )
        else:
            self.start_chat_button.disabled = True
            self.document_uploader.perform_upload(event, self.did_finish_upload)

    def did_finish_upload(self, uploaded_documents):
        # at this point, the UI has uploaded the files to the API.
        # We can now start the chat
        print("did finish upload", uploaded_documents)

        new_chat_id = self.api_wrapper.start_and_prepare(
            name=self.chat_name,
            documents=uploaded_documents,
            source_storage=self.config.source_storage_name,
            assistant=self.config.assistant_name,
        )

        print("new_chat_id", new_chat_id)

        self.start_chat_button.disabled = False

        if self.new_chat_ready_callback is not None:
            self.new_chat_ready_callback(new_chat_id)

    async def model_section(self):
        components = await self.api_wrapper.get_components_async()

        assistants = [component["title"] for component in components["assistants"]]
        self.config.param.assistant_name.objects = assistants
        self.config.assistant_name = assistants[0]

        source_storages = [
            component["title"] for component in components["source_storages"]
        ]
        self.config.param.source_storage_name.objects = source_storages
        self.config.source_storage_name = source_storages[0]

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

    def advanced_config_ui(self):
        card = pn.Card(
            pn.Row(
                pn.Column(
                    pn.pane.HTML(
                        """<h2> Retrieval Method</h2>
                            <span>Adjusting these settings requires re-embedding the documents, which may take some time.
                            </span><br />
                                         """
                    ),
                    pn.widgets.Select.from_param(
                        self.config.param.document_db_name,
                        name="Document DB Name",
                        width_policy="max",
                        stylesheets=[ui.SS_LABEL_STYLE, ui.BK_INPUT_GRAY_BORDER],
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_size,
                        name="Chunk Size",
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_overlap,
                        name="Chunk Overlap",
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
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
                    pn.widgets.Select.from_param(
                        self.config.param.llm_name,
                        name="LLM Name",
                        stylesheets=[
                            ui.SS_MULTI_SELECT_STYLE,
                            ui.SS_LABEL_STYLE,
                            ui.BK_INPUT_GRAY_BORDER,
                        ],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_context_tokens,
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_new_tokens,
                        bar_color=ui.MAIN_COLOR,
                        stylesheets=[ui.SS_LABEL_STYLE],
                        width_policy="max",
                    ),
                    width_policy="max",
                    height_policy="max",
                    margin=(0, 20, 0, 0),
                    styles={
                        "border-left": "1px solid var(--neutral-stroke-divider-rest)"
                    },
                ),
                height=350,
            ),
            collapsed=True,
            collapsible=True,
            hide_header=True,
            stylesheets=[ui.SS_ADVANCED_UI_CARD],
        )

        def toggle_card(event):
            card.collapsed = not card.collapsed
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
                }""".replace(
                    "MAIN_COLOR", ui.MAIN_COLOR
                )
            ],
        )

        toggle_button.on_click(toggle_card)

        toggle_button.js_on_click(
            args={"card": card},
            code=js.JS_TOGGLE_CARD,
        )

        return pn.Column(toggle_button, card)

    def __panel__(self):
        def divider():
            return pn.layout.Divider(styles={"padding": "0em 1em"})

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
                    "chat_name": {
                        "widget_type": pn.widgets.TextInput,
                        "name": "",
                        "stylesheets": [ui.BK_INPUT_GRAY_BORDER],
                    }
                },
                parameters=["chat_name"],
                show_name=False,
            ),
            divider(),
            self.model_section,
            divider(),
            self.advanced_config_ui,
            divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_width=ui.MODAL_WIDTH,
            sizing_mode="stretch_both",
            height_policy="max",
        )
