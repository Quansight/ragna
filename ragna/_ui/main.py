import contextlib
import uuid
from datetime import datetime, timedelta, timezone

import openai
import panel as pn
import param

from ragna._backend import Document
from ragna._ui import AppComponents, AppConfig, js, style
from .chat_data import ChatData

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


def get_default_chat_name(timezone_offset=None):
    if timezone_offset is None:
        return f"Chat {datetime.now():%m/%d/%Y %I:%M %p}"
    else:
        tz = timezone(offset=timedelta(minutes=timezone_offset))
        return f"Chat {datetime.now().astimezone(tz=tz):%m/%d/%Y %I:%M %p}"


class ModalConfiguration(pn.viewable.Viewer):
    chat_data = param.ClassSelector(ChatData)
    start_button_callback = param.Callable()
    cancel_button_callback = param.Callable()

    def __init__(self, chat_data, **params):
        super().__init__(chat_data=chat_data, **params)

        param.String(default=get_default_chat_name())
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

        self.main_column = None

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

        self.main_column = pn.Column(
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
            pn.pane.HTML("<b>Model</b>"),
            divider(),
            self.advanced_config_ui,
            divider(),
            self.upload_files_label,
            self.upload_row,
            pn.Row(self.cancel_button, self.start_chat_button),
            min_width=800,
            sizing_mode="stretch_both",
            height_policy="max",
        )

        return self.main_column

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
                        self.chat_data.param.source_storage,
                        name="Document DB Name",
                        width_policy="max",
                        stylesheets=[style.LABEL_STYLE],
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.chat_data.param.chunk_size,
                        name="Chunk Size",
                        bar_color=style.MAIN_COLOR,
                        stylesheets=[style.LABEL_STYLE],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.chat_data.param.chunk_overlap,
                        name="Chunk Overlap",
                        bar_color=style.MAIN_COLOR,
                        stylesheets=[style.LABEL_STYLE],
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
                        self.chat_data.param.llm,
                        name="LLM Name",
                        stylesheets=[style.MULTI_SELECT_STYLE, style.LABEL_STYLE],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.chat_data.param.max_context_tokens,
                        bar_color=style.MAIN_COLOR,
                        stylesheets=[style.LABEL_STYLE],
                        width_policy="max",
                    ),
                    pn.widgets.IntSlider.from_param(
                        self.chat_data.param.max_new_tokens,
                        bar_color=style.MAIN_COLOR,
                        stylesheets=[style.LABEL_STYLE],
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
            stylesheets=[style.ADVANCED_UI_CARD],
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
            stylesheets=["button.bk-btn { color: #004812; }"],
        )

        toggle_button.on_click(toggle_card)

        toggle_button.js_on_click(
            args={"card": card},
            code=js.TOGGLE_CARD,
        )

        return pn.Column(toggle_button, card)

    @param.depends("document_uploader.param", watch=True)
    def upload_documents(self):
        raise NotImplementedError
        # with self.loading_mode():
        #     self.chat_data.documents = [
        #         load_document(name, content)
        #         for name, content in zip(
        #             self.document_uploader.filename, self.document_uploader.value
        #         )
        #     ]

    @contextlib.contextmanager
    def loading_mode(self):
        self.upload_row.append(self.spinner_upload)
        self.start_chat_button.disabled = True

        try:
            yield
        finally:
            self.upload_row.remove(self.spinner_upload)
            self.start_chat_button.disabled = False

        # likely not needed.
        # @param.depends("model_toggle.param", watch=True)
        # def _toggle_gpt_model(self):
        #     self.chat_data.llm_name = f"OpenAI/{self.model_toggle.value}"

        def update_browser_info(new_browser_info):
            if "timezone_offset" in new_browser_info and not self.got_timezone:
                self.got_timezone = True
                # we pass the negative of the timezone because the value in `timezone_offset`
                # is actually the difference *from* the browser *to* the server.
                # Hence, using a broswer in Paris in Summer, and running the app
                # from London, yields a timezone_offset of -120.
                # Down the road what we want is to offset dt.now() by 120min.
                self.chat_name = get_default_chat_name(
                    -new_browser_info["timezone_offset"]
                )

        sync = lambda *events: update_browser_info(  # noqa: E731
            {e.name: e.new for e in events}
        )
        pn.state.browser_info.param.watch(sync, list(pn.state.browser_info.param))

    def check_before_start(self, event):
        if self.document_uploader.value is None:
            self.upload_files_label.object = (
                "<span style='color:red;'><b>Upload files</b> (required)</span>"
            )
            return

        if self.chat_name.strip() == "":
            # enforce a default chat name
            self.chat_name = get_default_chat_name()

        if self.on_start is not None:
            self.on_start(event)


class Page(param.Parameterized):
    chat_session_ids = param.List(default=[])
    tabs = param.Parameter()
    app_config = param.ClassSelector(AppConfig)
    components = param.ClassSelector(AppComponents)

    def __init__(self, **params):
        global site_template
        super().__init__(**params)
        # self.template = template

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

        # Transient property that will hold the config object
        # currently shown in the modal
        self.current_new_chat_data = None

        # preparing the modal : it contains a simple Column
        # Due to the way Panel works, we'll update the column's objects,
        # and not the modal ones.
        site_template.modal.objects = [
            pn.Column(
                min_height=600,
                sizing_mode="stretch_both",
            )
        ]

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
        """I haven't found a better way to open the modal when the pages load,
        than simulating a click on the "New chat" button.
        - calling self.template.open_modal() doesn't work
        - calling self.on_click_new_chat doesn't work either
        - trying to schedule a call to on_click_new_chat with pn.state.schedule_task
            could have worked but my tests were yielding an unstable result.
        """
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
        self.current_new_chat_data = ChatData(
            chat_id=str(uuid.uuid1()),
            components=self.components,
            app_config=self.app_config,
        )

        site_template.modal.objects[0].objects = [
            ModalConfiguration(
                self.current_new_chat_data,
                start_button_callback=self.on_click_start_conv_button,
                cancel_button_callback=self.on_click_cancel_button,
            )
        ]
        site_template.open_modal()

    def tab_changed(self, event):
        self.hide_info_sidebar(None)

    def on_click_start_conv_button(self, event):
        #  store the bytes uploaded so that they are destroyed
        # modal should be quick... store documents in vector database when clicking start.
        #  document needs to be destroyed but document_metadata should persist for source info etc.
        global site_template
        user_config = self.components[
            "user_config"
        ]  # parameterized object with a __panel__ method
        _ = self.new_chat_session(
            chat_data=self.current_new_chat_data,
            user_config=user_config,
        )

        chat_name = self.current_new_chat_data.chat_name

        self.tabs.append(
            pn.param.ParamMethod(self.display_chat, lazy=True, name=chat_name)
        )
        self.tabs.active = len(self.tabs) - 1
        site_template.close_modal()

        self.current_new_chat_data = None

    def on_click_cancel_button(self, event):
        global site_template
        site_template.close_modal()

    def display_chat(self):
        """
        Provided with a chat id, components, and app configuration the class
        instantiates and object to represent the state of a chat session.
        Instantiating chat data when the state has been previously created/stored
        will recreate that session. Session recreation will fail if the state of the
        session includes components that are not currently available.
        """
        return self.chat_sessions[self.tabs.active]


# Orphaned... don't want to create a new session on the page class but instead transiently created within a tab on the page
# def new_chat_session(self, chat_data):
#     breakpoint()
#     self.chat_sessions.append(
#         ChatSession(
#             chat_data,
#             show_info_callback=self.show_info_sidebar,
#             show_sources_callback=self.show_sources_sidebar,
#         )
#     )
#     return self.chat_sessions[-1]


#################################################################################
class ChatTab(param.Parameterized):
    """
    This should instantiate the data from the id... with  load/store functionality
    It should focus on displaying and leave all data management to the data class.
    """

    source_storage_name = param.Selector()
    llm_name = param.Selector()

    chat_config = param.ClassSelector(ChatData)

    # This cannot be on the main page, since that would mean we persist the document
    # in memory. It has to be on a modal class which is destroyed together with the
    # modal
    documents = param.List(item_type=Document)

    def __init__(self, app_config, components):
        self.file_input = pn.widgets.FileInput(multiple=True)
        super().__init__()
        source_storage_names = list(components.source_storages.keys())
        self.param.source_storage_name.objects = source_storage_names
        self.source_storage_name = source_storage_names[0]

        llm_names = list(components.llms.keys())
        self.param.llm_name.objects = llm_names
        self.llm_name = llm_names[0]

        self.question = pn.widgets.TextInput()
        self.fake_chat_box = pn.widgets.ChatInterface(callback=callback)

    def __panel__(self):
        start_conversation_button = pn.widgets.Button(name="Start conversation")
        start_conversation_button.on_click(self.start_conversation)

        ask_button = pn.widgets.Button(name="Send")
        ask_button.on_click(self.ask)

        return pn.layout.Column(
            pn.widgets.Select.from_param(self.param.source_storage_name),
            pn.widgets.Select.from_param(self.param.llm_name),
            # self.file_input,
            # start_conversation_button,
            # pn.layout.Row(self.question, ask_button),
            self.fake_chat_box,
        )

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

    def start_conversation(self, event):
        if not self.documents:
            return

        source_storage = self.components.source_storages[self.source_storage_name]
        chat_config = ChatData(
            source_storage=source_storage,
            llm=self.components.llms[self.llm_name],
            document_metadatas=[document.metadata for document in self.documents],
        )

        source_storage.store(self.documents, chat_config=chat_config)

        chat_config.chat_log.append(f"A: Hi, I'm {self.llm_name}!")
        self.chat_config = chat_config

    @param.depends("chat_config.chat_log", watch=True)
    def answer(self):
        last = self.chat_config.chat_log[-1]
        self.fake_chat_box.append(pn.pane.HTML(last))

        if last.startswith("A"):
            return

        prompt = last.removeprefix("Q: ")

        sources = self.chat_config.source_storage.retrieve(
            prompt, num_tokens=1_000, chat_config=self.chat_config
        )
        answer = self.chat_config.llm.complete(
            prompt, sources, chat_config=self.chat_config
        )

        self.chat_config.chat_log.append(f"A: {answer}")
        self.chat_config.param.trigger("chat_log")

    def ask(self, event):
        self.chat_config.chat_log.append(f"Q: {self.question.value}")
        self.chat_config.param.trigger("chat_log")


def app(*, app_config, components):
    global site_template
    site_template.main.append(Page(app_config=app_config, components=components))
    pn.serve(
        site_template,
        port=app_config.port,
        start=True,
        show=False,
        location=True,
        autoreload=True,
        allow_websocket_origin=[app_config.url, f"{app_config.url}:{app_config.port}"],
    )


def callback(contents: str, user: str, instance: pn.widgets.ChatInterface):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": contents}],
    )
    yield response.choices[0]["value"]["content"]
