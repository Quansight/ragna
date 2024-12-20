from datetime import datetime, timedelta, timezone
from typing import AsyncIterator

import panel as pn
import param

from ragna.deploy import _schemas as schemas

from . import js
from . import styles as ui
from .components.metadata_filters_builder import NO_CORPUS_KEY, MetadataFiltersBuilder

USE_CORPUS_LABEL = "Use existing corpus"
USE_UPLOAD_LABEL = "Upload new documents"


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
        default=2000,
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

    corpus_or_upload = param.Selector(
        objects=[USE_CORPUS_LABEL, USE_UPLOAD_LABEL], default=USE_CORPUS_LABEL
    )

    error = param.Boolean(default=False)

    def __init__(
        self, api_wrapper, components, corpus_names, corpus_metadata, **params
    ):
        super().__init__(chat_name=get_default_chat_name(), **params)

        self.api_wrapper = api_wrapper

        self.corpus_names = corpus_names
        self.corpus_metadata = corpus_metadata

        self.chat_name_input = pn.widgets.TextInput.from_param(
            self.param.chat_name, name=""
        )
        self.document_uploader = pn.widgets.FileInput(
            multiple=True,
            css_classes=["file-input"],
            accept=",".join(self.api_wrapper.get_components().documents),
        )

        # Most widgets (including those that use from_param) should be placed after the super init call
        self.cancel_button = pn.widgets.Button(
            name="Cancel", button_type="default", min_width=375
        )
        self.cancel_button.on_click(self.cancel_button_callback)

        self.corpus_name_input = pn.widgets.TextInput(
            name="",
            value="default",
            placeholder="Enter name of corpus to upload data to (optional)",
            width=335,
        )

        self.start_chat_button = pn.widgets.Button(
            name="Start Conversation", button_type="primary", min_width=375
        )
        self.start_chat_button.on_click(self.did_click_on_start_chat_button)

        self.upload_files_label = pn.pane.HTML()

        self.upload_row = pn.Row(
            self.document_uploader,
            sizing_mode="stretch_width",
            css_classes=["modal_configuration_upload_row"],
        )

        self.got_timezone = False

        self.corpus_or_upload_radiobutton = pn.widgets.RadioButtonGroup.from_param(
            self.param.corpus_or_upload,
            button_style="outline",
            button_type="primary",
        )

        self.metadata_filter_rows_title = pn.pane.HTML(
            "<b>Available Corpuses</b> (required)"
        )
        self.metadata_filter_rows = None

        self.change_upload_files_label()

        self.create_config(components)

    async def did_click_on_start_chat_button(self, event):
        if self.corpus_or_upload == USE_UPLOAD_LABEL:
            if not self.document_uploader.value:
                self.change_upload_files_label("missing_file")
                return

            self.start_chat_button.disabled = True
            documents = self.api_wrapper._engine.register_documents(
                user=self.api_wrapper._user,
                document_registrations=[
                    schemas.DocumentRegistration(name=name)
                    for name in self.document_uploader.filename
                ],
            )

            if self.api_wrapper._engine.supports_store_documents:

                def make_content_stream(data: bytes) -> AsyncIterator[bytes]:
                    async def content_stream() -> AsyncIterator[bytes]:
                        yield data

                    return content_stream()

                await self.api_wrapper._engine.store_documents(
                    user=self.api_wrapper._user,
                    ids_and_streams=[
                        (document.id, make_content_stream(data))
                        for document, data in zip(
                            documents, self.document_uploader.value
                        )
                    ],
                )

            input = [str(document.id) for document in documents]
            corpus_name = self.corpus_name_input.value

        else:  # self.corpus_or_upload == USE_CORPUS_LABEL:
            if not self.metadata_filter_rows:
                return

            if self.metadata_filter_rows.corpus_names_select.value == NO_CORPUS_KEY:
                self.change_upload_files_label("no_corpus_available")
                return

            self.start_chat_button.disabled = True

            input = self.metadata_filter_rows.construct_metadata_filters()
            corpus_name = self.metadata_filter_rows.corpus_names_select.value

        await self.did_finish_upload(input, corpus_name)

    async def did_finish_upload(self, input, corpus_name=None):
        if corpus_name is None:
            corpus_name = self.corpus_name_input.value

        try:
            new_chat_id = await self.api_wrapper.start_and_prepare(
                name=self.chat_name,
                input=input,
                corpus_name=corpus_name,
                source_storage=self.config.source_storage_name,
                assistant=self.config.assistant_name,
                params=self.config.to_params_dict(),
            )

            self.start_chat_button.disabled = False

            if self.new_chat_ready_callback is not None:
                await self.new_chat_ready_callback(new_chat_id)

        except Exception as exc:
            import traceback

            print(
                "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
            )
            self.change_upload_files_label("upload_error")
            self.document_uploader.loading = False
            self.start_chat_button.disabled = False

    def change_upload_files_label(self, mode="normal"):
        self.error = False
        if mode == "upload_error":
            self.upload_files_label.object = "<b>Upload files</b> (required)<span style='color:red;padding-left:100px;'><b>An error occured. Please try again or contact your administrator.</b></span>"
            self.error = True
        elif mode == "missing_file":
            self.upload_files_label.object = (
                "<span style='color:red;'><b>Upload files</b> (required)</span>"
            )
            self.error = True
        elif mode == "no_corpus_available":
            self.error = True
        else:
            self.upload_files_label.object = "<b>Upload files</b> (required)"

    def create_config(self, components):
        if self.config is None:
            # Retrieve the components from the API and build a config object
            components = self.api_wrapper.get_components()
            # TODO : use the components to set up the default values for the various params

            config = ChatConfig()
            config.allowed_documents = components.documents

            assistants = [assistant["title"] for assistant in components.assistants]

            config.param.assistant_name.objects = assistants
            config.assistant_name = assistants[0]

            source_storages = [
                source_storage["title"] for source_storage in components.source_storages
            ]
            config.param.source_storage_name.objects = source_storages
            config.source_storage_name = source_storages[0]

            # Now that the config object is set, we can assign it to the param.
            # This will trigger the update of the advanced_config_ui section
            self.config = config

    def model_section(self):
        return pn.Row(
            pn.Column(
                pn.pane.HTML("<b>Assistants</b>"),
                pn.widgets.Select.from_param(
                    self.config.param.assistant_name,
                    name="",
                ),
            ),
            pn.Column(
                pn.pane.HTML("<b>Source storage</b>"),
                pn.widgets.Select.from_param(
                    self.config.param.source_storage_name,
                    name="",
                ),
            ),
        )

    def make_corpus_card(self):
        disabled_assistant = self.config.is_assistant_disabled()

        assistant_css_classes = [
            "modal_configuration_int_slider",
            *(["disabled"] if disabled_assistant else []),
        ]
        return pn.Card(
            pn.widgets.IntSlider.from_param(
                self.config.param.max_new_tokens,
                bar_color=ui.MAIN_COLOR,
                css_classes=assistant_css_classes,
                disabled=disabled_assistant,
                margin=(0, 0, 0, 11),
            ),
            collapsed=self.advanced_config_collapsed,
            collapsible=True,
            hide_header=True,
            css_classes=["modal_configuration_advanced_card"],
        )

    def make_documents_card(self):
        disabled_assistant = self.config.is_assistant_disabled()
        disabled_source_storage = self.config.is_source_storage_disabled()

        source_storage_css_classes = [
            "modal_configuration_int_slider",
            *(["disabled"] if disabled_source_storage else []),
        ]

        assistant_css_classes = [
            "modal_configuration_int_slider",
            *(["disabled"] if disabled_assistant else []),
        ]
        return pn.Card(
            pn.Row(
                pn.Column(
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_size,
                        name="Chunk Size",
                        bar_color=ui.MAIN_COLOR,
                        css_classes=source_storage_css_classes,
                        width_policy="max",
                        disabled=disabled_source_storage,
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.chunk_overlap,
                        name="Chunk Overlap",
                        bar_color=ui.MAIN_COLOR,
                        css_classes=source_storage_css_classes,
                        width_policy="max",
                        disabled=disabled_source_storage,
                    ),
                    width_policy="max",
                ),
                pn.Column(
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_context_tokens,
                        bar_color=ui.MAIN_COLOR,
                        css_classes=source_storage_css_classes,
                        width_policy="max",
                        disabled=disabled_source_storage,
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.config.param.max_new_tokens,
                        bar_color=ui.MAIN_COLOR,
                        css_classes=assistant_css_classes,
                        width_policy="max",
                        disabled=disabled_assistant,
                    ),
                    width_policy="max",
                    height_policy="max",
                    styles={
                        "border-left": "1px solid var(--neutral-stroke-divider-rest)"
                    },
                ),
                width=ui.CONFIG_MODAL_WIDTH,
            ),
            collapsed=self.advanced_config_collapsed,
            collapsible=True,
            hide_header=True,
            css_classes=["modal_configuration_advanced_card"],
        )

    def advanced_config(self, is_corpus=False):
        card = self.make_corpus_card() if is_corpus else self.make_documents_card()

        if is_corpus:
            toggle_button = pn.widgets.Button(
                name="Advanced Configuration of Assistants   ▶",
                button_type="light",
                css_classes=["modal_configuration_toggle_button"],
            )
        else:
            toggle_button = pn.widgets.Button(
                name="Advanced Configuration of Assistants and Source Storages   ▶",
                button_type="light",
                css_classes=["modal_configuration_toggle_button"],
            )

        if card.collapsed:
            toggle_button.name = toggle_button.name.replace("▼", "▶")
        else:
            toggle_button.name = toggle_button.name.replace("▶", "▼")

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

        toggle_button.on_click(toggle_card)

        return pn.Column(toggle_button, card)

    @pn.depends(
        "corpus_or_upload",
        "config",
        "config.assistant_name",
        "config.source_storage_name",
    )
    def corpus_or_upload_config(self):
        if self.corpus_or_upload == USE_CORPUS_LABEL:
            return self.advanced_config(is_corpus=True)
        else:
            return self.advanced_config(is_corpus=False)

    @pn.depends("advanced_config_collapsed", watch=True)
    def shrink_upload_container_height(self):
        if self.advanced_config_collapsed:
            self.document_uploader.height_upload_container = ui.FILE_CONTAINER_HEIGHT
        else:
            self.document_uploader.height_upload_container = (
                ui.FILE_CONTAINER_HEIGHT_REDUCED
            )

    @pn.depends("error", watch=True)
    def add_error_message(self):
        if self.error:
            text = "<b>Available Corpuses</b> (required)<span style='color:red;padding-left:100px;'><b>There are no available corpuses to chat with.</b></span>"
            self.metadata_filter_rows_title.object = text
        else:
            self.metadata_filter_rows_title.object = (
                "<b>Available Corpuses</b> (required)"
            )

    @pn.depends(
        "corpus_or_upload",
        "config.source_storage_name",
    )
    def corpus_or_upload_row(self):
        if self.corpus_or_upload == USE_CORPUS_LABEL:
            if self.config.source_storage_name in self.corpus_names:
                corpus_names = self.corpus_names[self.config.source_storage_name]
            else:
                corpus_names = []

            if self.config.source_storage_name in self.corpus_metadata:
                corpus_metadata = self.corpus_metadata[self.config.source_storage_name]
            else:
                corpus_metadata = {}

            self.metadata_filter_rows = MetadataFiltersBuilder(
                corpus_names=corpus_names, corpus_metadata=corpus_metadata
            )

            if len(corpus_names) > 0:
                data = pn.Column(
                    self.metadata_filter_rows_title, self.metadata_filter_rows
                )
            else:
                data = pn.Column(self.metadata_filter_rows)

            self.error = False
            return data

        else:
            return pn.Column(
                pn.pane.HTML("<b>Corpus Name</b>"),
                self.corpus_name_input,
                self.upload_files_label,
                self.upload_row,
            )

    def __panel__(self):
        return pn.Column(
            pn.pane.HTML(
                f"""<h2 style="margin-bottom: 5px;">Start a new chat</h2>
                         <script>{js.set_modal_size(ui.CONFIG_MODAL_WIDTH, ui.CONFIG_MODAL_HEIGHT)}</script>
                         """,
            ),
            self.corpus_or_upload_radiobutton,
            ui.divider(),
            pn.pane.HTML("<b>Chat name</b>"),
            self.chat_name_input,
            ui.divider(),
            self.model_section,
            ui.divider(),
            self.corpus_or_upload_config,
            ui.divider(),
            self.corpus_or_upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_height=ui.CONFIG_MODAL_HEIGHT,
            min_width=ui.CONFIG_MODAL_WIDTH,
            styles={"overflow-y": "hidden"},
        )
