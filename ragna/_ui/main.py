from datetime import datetime, timedelta, timezone

from typing import Any

import openai
import panel as pn
import param

from ragna._backend import ChatConfig, Document
from ragna._ui import AppComponents, AppConfig, js, style

pn.extension(sizing_mode="stretch_width")

site_template = pn.template.FastListTemplate(
    # We need to set a title to have it appearing on the browser's tab
    # but it means we need to hide it from the header bar
    title="Ragna",
    neutral_color=style.MAIN_COLOR,
    header_background=style.MAIN_COLOR,
    accent_base_color=style.MAIN_COLOR,
    theme_toggle=False,
    collapsed_sidebar=True,
    # main_layout=None
    raw_css=[style.APP_RAW],
)
site_template.config.css_files = ["css/global_overrides.css"]


def app(*, app_config, components, the_config):
    the_config = DemoConfig(app_config, components)
    global site_template
    site_template.main.append(
        Page(app_config=app_config, components=components, the_config=the_config)
    )
    pn.serve(
        site_template,
        port=app_config.port,
        start=True,
        show=False,
        location=True,
        autoreload=True,
        allow_websocket_origin=[app_config.url, f"{app_config.url}:{app_config.port}"],
    )


# extension targetted to developers
class DemoConfig(param.Parameterized):
    source_storage_name = param.Selector()

    def __init__(self, app_config, components):
        super().__init__(source_storage_name=list(components.source_storages.keys()))
        pass

    def __panel__(self):
        """Empty to provide no input from users"""
        return pn.Column(
            pn.widgets.Select.from_param(self.param.source_storage_name),
            # pn.widgets.Select.from_param(self.parametrized.param.llm_name),
        )

    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        return self.source_storage_name, self.llm_name, {}

    def __repr__(self) -> str:
        return "DemoConfig"


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


def new_chat_component_callback(
    contents: str, user: str, instance: pn.widgets.ChatInterface
):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": contents}],
    )
    yield response.choices[0]["value"]["content"]


class ModalConfiguration(pn.viewable.Viewer):
    chat_config = param.ClassSelector(ChatConfig)
    chat_name = param.String()
    start_button_callback = param.Callable()
    cancel_button_callback = param.Callable()
    #

    def __init__(self, app_config, components, **params):
        super().__init__(chat_name=get_default_chat_name(), **params)
        # TODO: sort out documents within this class

        self.document_uploader = pn.widgets.FileInput(
            # accept=",".join(get_supported_suffixes()),
            accept=".pdf",
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
            return pn.layout.Divider(styles={"padding": "0px 15px 0px 15px"})

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
            self.chat_config,
            divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_width=800,
            sizing_mode="stretch_both",
            height_policy="max",
        )


#     @param.depends("documents", watch=True)
#     def update_document_names(self):
#         new_docs = [document.name for document in self.documents]
#         self.document_names = new_docs + self.document_names


#     @param.depends("document_db_name", watch=True, on_init=True)
#     def load_document_db(self):
#         self.document_db = load_document_db(self.document_db_name)

#     @param.depends("document_names", watch=True)
#     def store_documents(self):
#         self.document_db.store(
#             self.documents, chunk_size=self.chunk_size, chunk_overlap=self.chunk_overlap
#         )


class Page(param.Parameterized):
    chat_session_ids = param.List(default=[])
    tabs = param.Parameter()
    app_config = param.ClassSelector(AppConfig)
    components = param.ClassSelector(AppComponents)
    modal = param.ClassSelector(ModalConfiguration)
    the_config = param.ClassSelector(param.Parameterized)

    def __init__(self, **params):
        global site_template
        super().__init__(**params)

        # self.version = pn.widgets.StaticText(
        #     name="Version",
        #     value=__version__,
        #     stylesheets=[style.VERSION_ID],
        # )
        self.new_chat_button = pn.widgets.Button(
            name="New chat",
            button_type="primary",
            stylesheets=[style.NEW_CHAT_BUTTON],
        )
        self.new_chat_button.on_click(self.on_click_new_chat)

        # preparing the modal : it contains a simple Column
        # Due to the way Panel works, we'll update the column's objects,
        # and not the modal ones.
        site_template.modal.objects = [
            pn.Column(
                min_height=600,
                sizing_mode="stretch_both",
            )
        ]
        # TODO: chat ids should likely be stored on the app_config.
        self.tabs = pn.Tabs(
            *[
                pn.param.ParamMethod(self.display_chat, lazy=True, name=chat_id)
                for chat_id in self.chat_session_ids
            ],
            tabs_location="left",
            dynamic=True,
            stylesheets=[style.TABS],
        )
        self.tabs.param.watch(self.tab_changed, ["active"], onlychanged=True)

        self.right_sidebar = pn.Column(
            pn.pane.Markdown("# Test"),
            stylesheets=[style.RIGHT_SIDEBAR_HIDDEN],
            visible=False,
        )

    def __panel__(self):
        """TODO: do not start with the modal... help user push the new chat button."""
        js_for_modal = pn.pane.HTML(
            js.SHADOWROOT_INDEXING
            + """
                         <script>   let buttons = $$$('button.bk-btn-primary');
                                    buttons.forEach(function(btn){
                                        if ( btn.innerHTML == '{new_chat_btn_name}' ){
                                            btn.click();
                                        }
                                    });
                         </script>
                         """.replace(
                "{new_chat_btn_name}", self.new_chat_button.name
            ).strip(),
            stylesheets=[":host { position:absolute; z-index:-999; }"],
        )

        return pn.Row(
            pn.Column(
                self.new_chat_button,
                js_for_modal,
                self.tabs,
                stylesheets=[style.PAIGE_DASHBOARD],
            ),
            self.right_sidebar,
            stylesheets=[style.RIGHT_SIDEBAR_EXPANDED],
        )

    def hide_info_sidebar(self, event):
        self.right_sidebar.visible = False

    def show_info_sidebar(self, content):
        close_button = pn.widgets.Button(
            icon="x",
            button_type="light",
            stylesheets=[style.CLOSE_BUTTON],
        )
        close_button.on_click(self.hide_info_sidebar)

        self.right_sidebar.objects = [
            close_button,
            content,
        ]
        self.right_sidebar.visible = True

    def show_sources_sidebar(self, content):
        self.show_info_sidebar(content)

    def on_click_new_chat(self, event):
        global site_template

        # TODO: consider whether whether deep copy is required.
        # chat_config = self.components.chat_config.copy() or DefaultChatConfig()
        # chat_config = DefaultChatConfig(self.app_config)
        chat_config = DemoConfig(self.app_config, self.components)

        self.modal = ModalConfiguration(
            self.app_config,
            self.components,
            chat_config=chat_config,
            start_button_callback=self.on_click_start_conv_button,
            cancel_button_callback=self.on_click_cancel_button,
        )
        site_template.modal.objects[0].objects = [self.modal]
        # Modal content is destroyed once the user cancels or starts a
        # conversation... any required information is propagated to ChatData.
        site_template.open_modal()

    def tab_changed(self, event):
        self.hide_info_sidebar(None)

    def on_click_start_conv_button(self, event):
        #  store the bytes uploaded so that they are destroyed
        # modal should be quick... store documents in vector database when clicking start.
        #  document needs to be destroyed but document_metadata should persist for source info etc.
        global site_template
        # TODO: needs to load docs into storage, wipe modal content, instantiate
        # chat_data, close modal, and display the chat.
        # TODO: Chat session needs to be displayed... this would typically
        # loaded dynamically from saved data. When creating afresh is there a
        # convenient way of propagating it through? Likley store it on the page
        # but that's not easily accessible here.
        breakpoint()
        # pass in doc metadata too...
        ChatData(
            app_config=self.app_config, chat_config=self.modal.chat_config.get_config()
        )
        # TODO: not sure whether to pass the user config into chat data (as extra) or session creation.
        # chat_session = new_chat_session(
        #     chat_data=self.current_new_chat_data,
        #     user_config=user_config,
        # )

        chat_name = self.current_new_chat_data.chat_name

        self.tabs.append(
            pn.param.ParamMethod(self.display_chat, lazy=True, name=chat_name)
        )
        self.tabs.active = len(self.tabs) - 1
        site_template.close_modal()

        self.current_new_chat_data = None

        # source_storage = self.components.source_storages[self.source_storage_name]
        # chat_config = ChatData(
        #     source_storage=source_storage,
        #     llm=self.components.llms[self.llm_name],
        #     document_metadatas=[document.metadata for document in self.documents],
        # )

        # source_storage.store(self.documents, chat_config=chat_config)

        # chat_config.chat_log.append(f"A: Hi, I'm {self.llm_name}!")
        # self.chat_config = chat_config

    def on_click_cancel_button(self, event):
        global site_template
        # TODO: all content should be destroyed
        site_template.close_modal()

    def display_chat(self):
        """
        TODO:

        User/chat id should be sufficient to display a chat session (panel class
        that uses chat_data)

        Visiting a chat that has been previously created/stored will recreate
        that session from stored chat data. Session recreation will fail if the
        state of the session includes components that are not currently
        available.
        """
        return self.chat_sessions[self.tabs.active]

    #################################################################################

    #################################################################################

    @param.depends("file_input.param", watch=True)
    def upload_documents(self):
        if not self.file_input.value:
            return

        self.documents = [
            Document._from_name_and_content(
                name, content, page_extractors=self.components.page_extractors.values()
            )
            for name, content in zip(self.file_input.filename, self.file_input.value)
        ]


class ChatData(param.Parameterized):
    # user? remove any objects that are large etc?
    #  chunk_size etc won't always exist (extra key.. chroma looks for certain keys here or uses defaults
    # middle of modal is customizable
    #  add chat_name
    # DB: user_name and chat name are sufficient to index
    config = param.Dict()
    chat_id = param.String()
    chat_config = param.Tuple(length=3)  # unpack these
    sources_info = param.Dict(default={})
    # TODO: Chat log will likely be a different param (with new chat interface)
    # (try to see if other metadata can be stored in the chat log)
    chat_log = param.List(
        default=[{"Model": "How can I help you with the selected sources?"}]
    )
    # TODO: not sure how this will be used (in combination with components?)
    document_metadata = param.List()
    # TODO: figure out if this is required... does it need to be
    # a parameterize object... does it need to interact with chat data?
    extra = param.Parameterized()
    # I think the Following should be in config
    # llm = param.String()
    # source_storage = param.String()
    # page_extractor = param.String()
    # TODO: components should be passed in to methods so that they do not get serialized with this class
    # components = param.ClassSelector(AppComponents)

    def __init__(
        self,
        **params,
    ):
        super().__init__(**params)
        breakpoint()


#     @param.depends("llm_name", watch=True, on_init=True)
#     def load_llm(self):
#         self.llm = load_llm(*self.llm_name.split("/"))

#     @param.depends("llm", watch=True, on_init=True)
#     def update_max_context_tokens(self):
#         # 1. We limit the default value to 8_000 tokens, because otherwise the response
#         #    time is really high for a default setting
#         # 2. We reserve at least 1_000 tokens for prompt and instruction
#         self.max_context_tokens = min(
#             (self.llm.max_context_size - 1_000) // 1_000 * 1_000, 8_000
#         )
#         # We set the bound to the actual maximum
#         self.param.max_context_tokens.bounds = (0, self.llm.max_context_size)


#     # TODO: when the value of pn.widgets.ChatBox can be properly bound to a param,
#     #  remove the return values and decorate this method with
#     #  @param.depends("chat_log", watch=True)
#     async def complete_prompt(self):
#         last_message = self.chat_log[-1]
#         prompt = last_message.get("You")
#         if not prompt:
#             return False

#         logger.info(f"User asked: {prompt}")
#         if self.document_db.contains_docs():
#             relevant_document_chunks = self.document_db.retrieve(
#                 prompt, max_tokens=self.max_context_tokens
#             )
#             logger.info(
#                 json.dumps(
#                     {
#                         "relevant_document_chunks": summarize_chunk_metadata(
#                             relevant_document_chunks
#                         )
#                     }
#                 )
#             )
#             source_info, context = zip(*relevant_document_chunks)

#             answer = self.llm(
#                 prompt,
#                 context=context,
#                 max_new_tokens=self.max_new_tokens,
#                 instructize=True,
#             )

#             self.sources_info[(len(self.chat_log), answer)] = source_info
#         else:
#             answer = "Please choose documents"
#         logger.info(f"Model responded: {answer}")

#         self.chat_log.append({self.llm_name: answer})
#         return True
