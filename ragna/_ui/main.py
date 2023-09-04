import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import dateutil
import panel as pn
import param

from ragna import __version__
from ragna._backend import Document
from ragna._ui import AppComponents, AppConfig, js, style
from ragna.utils import compute_id

pn.extension(sizing_mode="stretch_width")


def app(*, app_config, components):
    rag_page = Page(app_config=app_config, components=components)
    pn.serve(
        rag_page,
        port=app_config.port,
        start=True,
        show=False,
        location=True,
        autoreload=True,
        static_dirs={"assets": "./ragna/css"},
        allow_websocket_origin=[app_config.url, f"{app_config.url}:{app_config.port}"],
    )


class ChatData(param.Parameterized):
    # TODO: components should be passed in to methods so that they do not get serialized with this class
    # user? remove any objects that are large etc?
    #  chunk_size etc won't always exist (extra key.. chroma looks for certain keys here or uses defaults
    # middle of modal is customizable
    #  add chat_name
    # DB: user_name and chat name are sufficient to index
    chat_id = param.String(instantiate=True, per_instance=True)
    chat_name = param.String(instantiate=True, per_instance=True)
    source_storage_name = param.String(instantiate=True, per_instance=True)
    llm_name = param.String(instantiate=True, per_instance=True)
    extra = param.Dict(instantiate=True, per_instance=True)
    sources_info = param.Dict(default={}, instantiate=True, per_instance=True)
    # TODO: Chat log will likely be a different param (with new chat interface)
    # (try to see if other metadata can be stored in the chat log)
    chat_log = param.List(instantiate=True, per_instance=True)
    # TODO: not sure how this will be used (in combination with components?)
    document_metadata = param.List(instantiate=True, per_instance=True)

    def __init__(
        self,
        **params,
    ):
        super().__init__(
            **params,
        )

    def _to_dict(self):
        props = [
            name
            for name in dir(self)
            if not name.startswith("_") and name not in ["param", "chat_log"]
        ]
        output = {p: getattr(self, p) for p in props}
        output["chat_log"] = [self._entry_to_dict(entry) for entry in self.chat_log]
        return output

    def _from_dict(self, retrieved_archive):
        retrieved_archive["chat_log"] = [
            self._dict_to_entry(d) for d in retrieved_archive["chat_log"]
        ]
        return ChatData(**retrieved_archive)

    def _entry_to_dict(self, entry):
        return {
            "value": entry.value,
            "timestamp": entry.timestamp.isoformat(),
            "user": entry.user,
        }

    def _dict_to_entry(self, retrieved_dict):
        retrieved_dict["timestamp"] = dateutil.parser.parse(retrieved_dict["timestamp"])
        return pn.widgets.ChatEntry(**retrieved_dict)


# extension targetted to developers
class DemoConfig(param.Parameterized):
    # TODO: a schema should be defined for this and it can be loaded in a
    # pluggable manner... and removed here
    source_storage_name = param.Selector()
    llm_name = param.Selector()
    extra = param.Dict(default={})
    components = param.ClassSelector(AppComponents)
    app_config = param.ClassSelector(AppConfig)

    def __init__(
        self,
        *,
        components,
        source_storage_names,
        llm_names,
        extra,
    ):
        super().__init__(
            extra=extra,
        )
        self.param.source_storage_name.objects = source_storage_names
        self.source_storage_name = source_storage_names[0]
        self.param.llm_name.objects = llm_names
        self.llm_name = llm_names[0]

    def __panel__(self):
        """Could be left empty to provide no input from users"""
        return pn.Column(
            pn.widgets.Select.from_param(self.param.source_storage_name),
            pn.widgets.Select.from_param(self.param.llm_name),
        )

    def get_config(self) -> tuple[str, str, dict[str, Any]]:
        return {
            "source_storage_name": self.source_storage_name,
            "llm_name": self.llm_name,
            "extra": {},
        }

    def __repr__(self) -> str:
        return "DemoConfig"


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


class ChatStorage:
    def __init__(self, location=Path("/tmp/chat_storage"), user="unknown") -> None:
        self.location = location
        self.user = user

    def store(self, chat_data):
        archive = self.location / f"{chat_data.chat_id}.json"
        try:
            archive.write_text(json.dumps(chat_data._to_dict()))
        except TypeError:
            pass

    def retrieve(self, chat_id):
        archive = self.location / f"{chat_id}.json"

        if not archive.exists():
            raise FileNotFoundError
        retrieved = json.loads(archive.read_text())
        chat_data = ChatData()._from_dict(retrieved)
        return chat_data


class Page(param.Parameterized):
    chat_sessions = param.List(default=[("placeholder", "someid")])
    tabs = param.Parameter()
    app_config = param.ClassSelector(AppConfig)
    components = param.ClassSelector(AppComponents)
    modal = param.ClassSelector(ModalConfiguration)
    current_chat_data = param.ClassSelector(ChatData, instantiate=True)
    chat_interface = param.ClassSelector(pn.widgets.ChatInterface)

    def __init__(self, **params):
        super().__init__(**params)

        # TODO: populate these correctly
        self.components.source_storages["chat_storage"] = ChatStorage(
            self.app_config.cache_root, user=self.app_config.user
        )
        self.chat_configs = [
            DemoConfig(
                components=self.components,
                source_storage_names=["source", "source2"],
                llm_names=["gpt"],
                extra={"some config": "value", "other_config": 42},
            )
        ]

        self.version = pn.widgets.StaticText(
            name="Version",
            value=__version__,
            stylesheets=[style.VERSION_ID],
        )
        self.new_chat_button = pn.widgets.Button(
            name="New chat",
            button_type="primary",
            stylesheets=[style.NEW_CHAT_BUTTON],
        )
        self.new_chat_button.on_click(self.on_click_new_chat)

        self.get_template()
        self.site_template.modal.objects = [
            pn.Column(
                min_height=600,
                sizing_mode="stretch_both",
            )
        ]
        self.tabs = pn.Tabs(
            *[
                pn.param.ParamMethod(self.load_tab, lazy=False, name=chat_name)
                for chat_id, chat_name in self.chat_sessions
            ],
            tabs_location="left",
            dynamic=True,
            stylesheets=[style.TABS],
        )
        self.tabs.param.watch(self.load_tab, ["active"], onlychanged=True)

        self.right_sidebar = pn.Column(
            pn.pane.Markdown("# No sources found"),
            stylesheets=[style.RIGHT_SIDEBAR_HIDDEN],
            visible=False,
        )

    def __panel__(self):
        main_area = pn.Row(
            pn.Column(
                self.version,
                self.new_chat_button,
                self.tabs,
                stylesheets=[style.RAGNA_DASHBOARD],
            ),
            self.right_sidebar,
            stylesheets=[style.RIGHT_SIDEBAR_EXPANDED],
        )
        self.site_template.main.objects = [main_area]
        return self.site_template

    def callback(self, contents: str, user: str, instance: pn.widgets.ChatInterface):
        message = f"Echoing {user}: {contents}"

        return message

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
        self.modal = ModalConfiguration(
            chat_configs=self.chat_configs,
            start_button_callback=self.on_click_start_conv_button,
            cancel_button_callback=self.on_click_cancel_button,
        )
        self.site_template.modal.objects[0].objects = [self.modal]
        # Modal content is destroyed once the user cancels or starts a
        # conversation... any required information is propagated to ChatData.
        self.site_template.open_modal()

    def on_click_start_conv_button(self, event):
        #  store the bytes uploaded so that they are destroyed
        # modal should be quick... store documents in vector database when clicking start.
        #  document needs to be destroyed but document_metadata should persist for source info etc.
        # TODO: needs to load docs into storage, wipe modal content, instantiate
        # chat_data, close modal, and display the chat.
        # pass in doc metadata too...
        if self.current_chat_data:
            self.components.source_storages["chat_storage"].store(
                self.current_chat_data
            )
        chat_name = self.modal.chat_name
        chat_id = compute_id(str(datetime.now()))
        self.chat_sessions.append((chat_name, chat_id))
        self.site_template.close_modal()
        self.tabs.append(
            pn.param.ParamMethod(
                self.load_tab,
                name=chat_id,
            )
        )
        self.tabs.active = len(self.tabs) - 1

    def create_chat_data(self, chat_name, chat_id):
        all_chat_config_values = {}
        # TODO: we may want to update extra rather than overwrite it like we are doing here
        for config in self.chat_configs:
            all_chat_config_values.update(**config.get_config())
        self.current_chat_data = ChatData(**all_chat_config_values)
        self.current_chat_data = ChatData(
            chat_id=chat_id, chat_name=chat_name, **all_chat_config_values
        )

    @param.depends("tabs.active")
    def load_tab(self, *args):
        """
        This function is WIP and messy. It is messy (and not working correctly) because I am struggling to work out a
        way to usefully trigger it at the correct times. This is due to the
        behavior dynamically loaded pn.Tabs. I believe the best solution is to
        abandon pn.Tabs and simplify the logic here once reliable triggering is
        achieved via buttons instead.
        """
        if self.tabs is None:
            # page initialization
            return
        elif self.tabs.active is None:
            # shouldn't get here
            raise NotImplementedError

        elif self.tabs.active == 0 and self.chat_interface is None:
            # The first tab created... no chat interface exists and tab is being appended
            return None

        current_chat_session = self.chat_sessions[self.tabs.active]
        if True:
            # normal tab change
            # Triggered  on changing the tab... we will want to work with the current session first

            if self.current_chat_data is None:
                # first tab load
                self.create_chat_data(*current_chat_session)
            elif (
                current_chat_session[1] != self.current_chat_data.chat_id
                and self.chat_interface is not None
            ):
                # save, load, and switch chat
                self.current_chat_data.chat_log = self.chat_interface.value.copy()
                self.components.source_storages["chat_storage"].store(
                    self.current_chat_data
                )
                try:
                    self.current_chat_data = self.components.source_storages[
                        "chat_storage"
                    ].retrieve(current_chat_session[1])
                except FileNotFoundError:
                    self.create_chat_data(*current_chat_session)
                ####
                self.chat_interface = pn.widgets.ChatInterface(
                    value=self.current_chat_data.chat_log,
                    callback=self.callback,
                    callback_user="System",
                    entry_params={
                        "show_reaction_icons": False,
                        "show_avatar": False,
                    },
                )
                self.chat_interface.send(f"hello at {datetime.now()}")
                self.hide_info_sidebar(None)
                return pn.Column(
                    f"{id(datetime.now())}, {self.current_chat_data.chat_id}",
                    self.chat_interface,
                )
                ####
            elif (
                current_chat_session[1] == self.current_chat_data.chat_id
                and self.chat_interface is None
            ):
                # creation of first tab (happens above and below though)
                ####
                self.chat_interface = pn.widgets.ChatInterface(
                    value=self.current_chat_data.chat_log,
                    callback=self.callback,
                    callback_user="System",
                    entry_params={
                        "show_reaction_icons": False,
                        "show_avatar": False,
                    },
                )
                self.chat_interface.send(f"hello at {datetime.now()}")
                self.hide_info_sidebar(None)
                ####
            elif current_chat_session[1] == self.current_chat_data.chat_id:
                # should probably change interface here.
                return pn.Column(
                    f"{id(datetime.now())}, {self.current_chat_data.chat_id}",
                    self.chat_interface,
                )
                pass
            else:
                pass

    def on_click_cancel_button(self, event):
        # TODO: all content should be destroyed
        self.site_template.close_modal()

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

    def get_template(self):
        self.site_template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="Ragna",
            neutral_color=style.MAIN_COLOR,
            header_background=style.MAIN_COLOR,
            accent_base_color=style.MAIN_COLOR,
            theme_toggle=False,
            collapsed_sidebar=True,
            raw_css=[style.APP_RAW],
        )
        self.site_template.config.css_files = ["./assets/global_overrides.css"]
        self.site_template.header.append(
            pn.pane.Markdown(
                "[RAGNA](/)",
                css_classes=["title"],
                stylesheets=[style.HEADER_STYLESHEET],
            )
        )
        self.site_template.header.append(pn.pane.HTML(js.MODAL_MOUSE_UP_FIX))

        # append this to the end of the header
        self.site_template.header.append(pn.pane.HTML(js.CONNECTION_MONITOR))
