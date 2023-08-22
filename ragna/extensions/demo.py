from typing import Any

import panel as pn
import param

from ragna.extensions import ChatConfig, Document, hookimpl, Llm, Source, SourceStorage
from ragna.extensions.page_extractor import TxtPageExtractor  # noqa: F401


class RagnaDemoSourceStorage(SourceStorage):
    @classmethod
    def display_name(cls):
        return "ragna/DemoDocDb"

    def __init__(self, app_config):
        super().__init__(app_config)
        self._document_metadatas = {}

    def store(self, documents: list[Document], chat_config) -> None:
        self._document_metadatas[self.app_config.user] = [
            document.metadata for document in documents
        ]

    def retrieve(self, prompt: str, *, num_tokens: int, chat_config) -> list[Source]:
        return [
            Source(
                document_name=metadata.name,
                page_numbers="N/A",
                text="I'm just pretending here",
                num_tokens=-1,
            )
            for metadata in self._document_metadatas[self.app_config.user]
        ]


@hookimpl(specname="ragna_source_storage")
def ragna_demo_source_storage():
    return RagnaDemoSourceStorage


class RagnaDemoLlm(Llm):
    @classmethod
    def display_name(cls):
        return "ragna/DemoLLM"

    @property
    def context_size(self) -> int:
        return 8_192

    def complete(self, prompt: str, sources: list[Source], *, chat_config) -> str:
        return "This is a demo completion"


@hookimpl(specname="ragna_llm")
def ragna_demo_llm():
    return RagnaDemoLlm


class DemoParameterized(param.Parameterized):
    source_storage_name = param.Selector()
    llm_name = param.Selector()


class DemoConfig(ChatConfig):
    parameterized: param.Parameterized

    def __init__(self, app_config):
        breakpoint()

    def __panel__(self):
        return pn.Column(
            pn.widgets.Select.from_param(self.parametrized.param.source_storage_name),
            pn.widgets.Select.from_param(self.parametrized.param.llm_name),
        )

    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        return self.source_storage_name, self.llm_name, {}


@hookimpl(specname="ragna_chat_config")
def ragna_demo_chat_config():
    return DemoConfig

    # def advanced_config_ui(self):
    #     card = pn.Card(
    #         pn.Row(
    #             pn.Column(
    #                 pn.pane.HTML(
    #                     """<h2> Retrieval Method</h2>
    #                         <span>Adjusting these settings requires re-embedding the documents, which may take some time.
    #                         </span><br />
    #                                      """
    #                 ),
    #                 pn.widgets.Select.from_param(
    #                     self.chat_data.param.source_storage,
    #                     name="Document DB Name",
    #                     width_policy="max",
    #                     stylesheets=[style.LABEL_STYLE],
    #                 ),
    #                 pn.widgets.IntSlider.from_param(
    #                     self.chat_data.param.chunk_size,
    #                     name="Chunk Size",
    #                     bar_color=style.MAIN_COLOR,
    #                     stylesheets=[style.LABEL_STYLE],
    #                     width_policy="max",
    #                 ),
    #                 pn.widgets.IntSlider.from_param(
    #                     self.chat_data.param.chunk_overlap,
    #                     name="Chunk Overlap",
    #                     bar_color=style.MAIN_COLOR,
    #                     stylesheets=[style.LABEL_STYLE],
    #                     width_policy="max",
    #                 ),
    #                 margin=(0, 20, 0, 0),
    #                 width_policy="max",
    #             ),
    #             pn.Column(
    #                 pn.pane.HTML(
    #                     """<h2> Model Configuration</h2>
    #                         <span>Changing these parameters alters the output. This might affect accuracy and efficiency.
    #                         </span><br />
    #                                      """
    #                 ),
    #                 pn.widgets.Select.from_param(
    #                     self.chat_data.param.llm,
    #                     name="LLM Name",
    #                     stylesheets=[style.MULTI_SELECT_STYLE, style.LABEL_STYLE],
    #                     width_policy="max",
    #                 ),
    #                 pn.widgets.IntSlider.from_param(
    #                     self.chat_data.param.max_context_tokens,
    #                     bar_color=style.MAIN_COLOR,
    #                     stylesheets=[style.LABEL_STYLE],
    #                     width_policy="max",
    #                 ),
    #                 pn.widgets.IntSlider.from_param(
    #                     self.chat_data.param.max_new_tokens,
    #                     bar_color=style.MAIN_COLOR,
    #                     stylesheets=[style.LABEL_STYLE],
    #                     width_policy="max",
    #                 ),
    #                 width_policy="max",
    #                 height_policy="max",
    #                 margin=(0, 20, 0, 0),
    #                 styles={
    #                     "border-left": "1px solid var(--neutral-stroke-divider-rest)"
    #                 },
    #             ),
    #             height=350,
    #         ),
    #         collapsed=True,
    #         collapsible=True,
    #         hide_header=True,
    #         stylesheets=[style.ADVANCED_UI_CARD],
    #     )

    #     def toggle_card(event):
    #         card.collapsed = not card.collapsed
    #         toggle_button = event.obj

    #         if card.collapsed:
    #             toggle_button.name = toggle_button.name.replace("▼", "▶")
    #         else:
    #             toggle_button.name = toggle_button.name.replace("▶", "▼")

    #     toggle_button = pn.widgets.Button(
    #         name="Advanced Configurations   ▶",
    #         button_type="light",
    #         stylesheets=["button.bk-btn { color: #004812; }"],
    #     )

    #     toggle_button.on_click(toggle_card)

    #     toggle_button.js_on_click(
    #         args={"card": card},
    #         code=js.TOGGLE_CARD,
    #     )

    #     return pn.Column(toggle_button, card)

    # @param.depends("document_uploader.param", watch=True)
    # def upload_documents(self):
    #     raise NotImplementedError
    #     # with self.loading_mode():
    #     #     self.chat_data.documents = [
    #     #         load_document(name, content)
    #     #         for name, content in zip(
    #     #             self.document_uploader.filename, self.document_uploader.value
    #     #         )
    #     #     ]

    # @contextlib.contextmanager
    # def loading_mode(self):
    #     self.upload_row.append(self.spinner_upload)
    #     self.start_chat_button.disabled = True

    #     try:
    #         yield
    #     finally:
    #         self.upload_row.remove(self.spinner_upload)
    #         self.start_chat_button.disabled = False

    #     # likely not needed.
    #     # @param.depends("model_toggle.param", watch=True)
    #     # def _toggle_gpt_model(self):
    #     #     self.chat_data.llm_name = f"OpenAI/{self.model_toggle.value}"

    #     def update_browser_info(new_browser_info):
    #         if "timezone_offset" in new_browser_info and not self.got_timezone:
    #             self.got_timezone = True
    #             # we pass the negative of the timezone because the value in `timezone_offset`
    #             # is actually the difference *from* the browser *to* the server.
    #             # Hence, using a broswer in Paris in Summer, and running the app
    #             # from London, yields a timezone_offset of -120.
    #             # Down the road what we want is to offset dt.now() by 120min.
    #             self.chat_name = get_default_chat_name(
    #                 -new_browser_info["timezone_offset"]
    #             )

    #     sync = lambda *events: update_browser_info(  # noqa: E731
    #         {e.name: e.new for e in events}
    #     )
    #     pn.state.browser_info.param.watch(sync, list(pn.state.browser_info.param))

    # def check_before_start(self, event):
    #     if self.document_uploader.value is None:
    #         self.upload_files_label.object = (
    #             "<span style='color:red;'><b>Upload files</b> (required)</span>"
    #         )
    #         return

    #     if self.chat_name.strip() == "":
    #         # enforce a default chat name
    #         self.chat_name = get_default_chat_name()

    #     if self.on_start is not None:
    #         self.on_start(event)
