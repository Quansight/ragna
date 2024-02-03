from __future__ import annotations

from typing import Callable, Literal, Optional, cast

import panel as pn
import param
from panel.reactive import ReactiveHTML

from ragna._compat import anext

from . import styles as ui

# TODO : move all the CSS rules in a dedicated file

message_stylesheets = [
    """ 
            :host .right, :host .center {
                    width:100% !important;
            }
    """,
    """ 
            :host .left {
                height: unset !important;
                min-height: unset !important;
            }
    """,
    """
            :host div.bk-panel-models-layout-Column:not(.left) { 
                    width:100% !important;
            }
    """,
    """
            :host .message {
                width: calc(100% - 15px);
                box-shadow: unset;
                font-size: unset;
                background-color: unset;
            }
    """,
    """
            :host .avatar {
                margin-top:0px;
                box-shadow: unset;
            }
    """,
]


class CopyToClipboardButton(ReactiveHTML):
    title = param.String(default=None, doc="The title of the button ")
    value = param.String(default=None, doc="The text to copy to the clipboard.")

    _template = """
        <div type="button" 
                id="copy-button"
                onclick="${script('copy_to_clipboard')}"
                class="container"
                style="cursor: pointer;"
        >
            <svg xmlns="http://www.w3.org/2000/svg" class="icon icon-tabler icon-tabler-clipboard" width="16" height="16" 
                    viewBox="0 0 24 24" stroke-width="2" stroke="gray" fill="none" stroke-linecap="round" stroke-linejoin="round">
                <path stroke="none" d="M0 0h24v24H0z" fill="none"/>
                <path d="M9 5h-2a2 2 0 0 0 -2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2 -2v-12a2 2 0 0 0 -2 -2h-2" />
                <path d="M9 3m0 2a2 2 0 0 1 2 -2h2a2 2 0 0 1 2 2v0a2 2 0 0 1 -2 2h-2a2 2 0 0 1 -2 -2z" />
            </svg>
            <span>${title}</span>
        </div>            
        """

    _scripts = {
        "copy_to_clipboard": """navigator.clipboard.writeText(`${data.value}`);"""
    }

    _stylesheets = [
        """ div.container { 
                            
                            display:flex;
                            flex-direction: row;
                            margin: 7px 10px;
                    
                            color:gray;
                        } 
                    
                        svg {
                            margin-right:5px;
                        }

                    """
    ]


class RagnaChatMessage(pn.chat.ChatMessage):
    role: str = param.Selector(objects=["system", "user", "assistant"])
    sources = param.List(allow_None=True)
    on_click_source_info_callback = param.Callable(allow_None=True)

    def __init__(
        self,
        content: str,
        *,
        role: Literal["system", "user", "assistant"],
        user: str,
        sources: Optional[list[dict]] = None,
        on_click_source_info_callback: Optional[Callable] = None,
        timestamp=None,
        show_timestamp=True,
    ):
        css_class = f"message-content-{self.role}"
        self.content_pane = pn.pane.Markdown(
            content,
            css_classes=["message-content", css_class],
            stylesheets=ui.stylesheets(
                (
                    "table",
                    {"margin-top": "10px", "margin-bottom": "10px"},
                )
            ),
        )

        if role == "assistant":
            assert sources is not None
            css_class = "message-content-assistant-with-buttons"
            object = pn.Column(
                self.content_pane,
                self._copy_and_source_view_buttons(),
                css_classes=[css_class],
            )
        else:
            object = self.content_pane

        object.stylesheets.extend(
            ui.stylesheets(
                (
                    f":host(.{css_class})",
                    {"background-color": "rgb(243, 243, 243) !important"}
                    if role == "user"
                    else {
                        "background-color": "none",
                        "border": "rgb(234, 234, 234)",
                        "border-style": "solid",
                        "border-width": "1.2px",
                        "border-radius": "5px",
                    },
                )
            ),
        )

        super().__init__(
            object=object,
            role=role,
            user=user,
            sources=sources,
            on_click_source_info_callback=on_click_source_info_callback,
            timestamp=timestamp,
            show_timestamp=show_timestamp,
            show_reaction_icons=False,
            show_user=False,
            show_copy_icon=False,
            css_classes=[f"message-{role}"],
        )
        self._stylesheets.extend(message_stylesheets)

    def _copy_and_source_view_buttons(self) -> pn.Row:
        # I have tried to style this button using modifiers, but it doesn't work.
        # If you inspect the HTML code for this button, none of the CSS files are
        # added. Leaving this as this is for now.
        source_info_button = pn.widgets.Button(
            name="Source Info",
            icon="info-circle",
            stylesheets=[
                """     :host(.solid) .bk-btn.bk-btn-default {
                                background-color: transparent;
                                color: gray;
                            }

                            .bk-btn {
                                border-radius: 0;
                                padding: 0;
                                font-size: 14px;
                            }
                    """
            ],
            on_click=lambda event: self.on_click_source_info_callback(
                event, self.sources
            ),
        )

        return pn.Row(
            CopyToClipboardButton(
                value=self.content_pane.object,
                title="Copy",
            ),
            source_info_button,
        )

    def avatar_lookup(self, user: str) -> str:
        if self.role == "system":
            return "imgs/ragna_logo.svg"
        elif self.role == "user":
            return "👤"

        try:
            organization, model = user.split("/")
        except ValueError:
            organization = ""
            model = user

        if organization == "Ragna":
            return "imgs/ragna_logo.svg"
        elif organization == "OpenAI":
            if model.startswith("gpt-3"):
                return "https://upload.wikimedia.org/wikipedia/commons/thumb/0/04/ChatGPT_logo.svg/1024px-ChatGPT_logo.svg.png?20230318122128"
            elif model.startswith("gpt-4"):
                return "https://upload.wikimedia.org/wikipedia/commons/a/a4/GPT-4.png"
        elif organization == "Anthropic":
            return "https://upload.wikimedia.org/wikipedia/commons/1/14/Anthropic.png"

        return model[0].upper()


class RagnaChatInterface(pn.chat.ChatInterface):
    get_user_from_role = param.Callable(allow_None=True)

    @param.depends("placeholder_text", watch=True, on_init=True)
    def _update_placeholder(self):
        self._placeholder = RagnaChatMessage(
            ui.message_loading_indicator,
            role="system",
            user=self.get_user_from_role("system"),
            show_timestamp=False,
        )

    def _build_message(self, *args, **kwargs) -> RagnaChatMessage | None:
        message = super()._build_message(*args, **kwargs)
        if message is None:
            return None

        # We only ever hit this function for user inputs, since we control the
        # generation of the system and assistant messages manually. Thus, we can
        # unconditionally create a user message here.
        return RagnaChatMessage(message.object, role="user", user=self.user)


class CentralView(pn.viewable.Viewer):
    current_chat = param.ClassSelector(class_=dict, default=None)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        # FIXME: make this dynamic from the login
        self.user = ""
        self.api_wrapper = api_wrapper
        self.chat_info_button = pn.widgets.Button(
            # The name will be filled at runtime in self.header
            name="",
            on_click=self.on_click_chat_info_wrapper,
            button_style="outline",
            icon="info-circle",
            css_classes=["chat-info-button"],
        )
        self.on_click_chat_info = None

    def on_click_chat_info_wrapper(self, event):
        if self.on_click_chat_info is None:
            return

        pills = "".join(
            [
                f"""<div class='chat_document_pill'>{d['name']}</div>"""
                for d in self.current_chat["metadata"]["documents"]
            ]
        )

        grid_height = len(self.current_chat["metadata"]["documents"]) // 3

        markdown = "\n".join(
            [
                "To change configurations, start a new chat.\n",
                "**Uploaded Files**",
                f"<div class='pills_list'>{pills}</div><br />\n\n",
                "----",
                "**Source Storage**",
                f"""<span>{self.current_chat['metadata']['source_storage']}</span>\n""",
                "----",
                "**Assistant**",
                f"""<span>{self.current_chat['metadata']['assistant']}</span>\n""",
                "**Advanced configuration**",
                *[
                    f"- **{key.replace('_', ' ').title()}**: {value}"
                    for key, value in self.current_chat["metadata"]["params"].items()
                ],
            ]
        )

        self.on_click_chat_info(
            event,
            "Chat Info",
            [
                pn.pane.Markdown(
                    markdown,
                    dedent=True,
                    css_classes=["chat_info_markdown"],
                    # The CSS rule below relies on a variable value, so we can't move it into modifers
                    stylesheets=ui.stylesheets(
                        (
                            ":host(.chat_info_markdown) .pills_list",
                            {
                                "grid-template": f"repeat({grid_height}, 1fr) / repeat(3, 1fr)",
                            },
                        ),
                    ),
                ),
            ],
        )

    def on_click_source_info_wrapper(self, event, sources):
        if self.on_click_chat_info is None:
            return

        source_infos = []
        for rank, source in enumerate(sources, 1):
            location = source["location"]
            if location:
                location = f": page(s) {location}"
            source_infos.append(
                (
                    f"<b>{rank}. {source['document']['name']}</b> {location}",
                    pn.pane.Markdown(source["content"], css_classes=["source-content"]),
                )
            )

        self.on_click_chat_info(
            event,
            "Source Info",
            [
                pn.pane.Markdown(
                    "This response was generated using the following data from the uploaded files: <br />",
                ),
                pn.layout.Accordion(
                    *source_infos,
                    header_background="transparent",
                    css_classes=["source-accordion"],
                ),
            ],
        )

    def set_current_chat(self, chat):
        self.current_chat = chat

    def get_user_from_role(self, role: Literal["system", "user", "assistant"]) -> str:
        if role == "system":
            return "Ragna"
        elif role == "user":
            return cast(str, self.user)
        elif role == "assistant":
            return cast(str, self.current_chat["metadata"]["assistant"])
        else:
            raise RuntimeError

    async def chat_callback(
        self, content: str, user: str, instance: pn.chat.ChatInterface
    ):
        try:
            answer_stream = self.api_wrapper.answer(self.current_chat["id"], content)
            answer = await anext(answer_stream)

            message = RagnaChatMessage(
                answer["content"],
                role="assistant",
                user=self.get_user_from_role("assistant"),
                sources=answer["sources"],
                on_click_source_info_callback=self.on_click_source_info_wrapper,
            )
            yield message

            async for chunk in answer_stream:
                message.content_pane.object += chunk["content"]

        except Exception:
            yield RagnaChatMessage(
                (
                    "Sorry, something went wrong. "
                    "If this problem persists, please contact your administrator."
                ),
                role="system",
                user=self.get_user_from_role("system"),
            )

    @pn.depends("current_chat")
    def chat_interface(self):
        if self.current_chat is None:
            return

        chat_interface = RagnaChatInterface(
            *[
                RagnaChatMessage(
                    message["content"],
                    role=message["role"],
                    user=self.get_user_from_role(message["role"]),
                    sources=message["sources"],
                    timestamp=message["timestamp"],
                    on_click_source_info_callback=self.on_click_source_info_wrapper,
                )
                for message in self.current_chat["messages"]
            ],
            callback=self.chat_callback,
            user=self.user,
            get_user_from_role=self.get_user_from_role,
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            view_latest=True,
            sizing_mode="stretch_width",
            # TODO: Remove the parameter when
            #  https://github.com/holoviz/panel/issues/6115 is merged and released. We
            #  currently need it to avoid sending a message when the text input is
            #  de-focussed. But this also means we can't hit enter to send.
            auto_send_types=[],
            widgets=[
                pn.widgets.TextInput(
                    placeholder="Ask a question about the documents",
                    # css_classes is forced to chat-interface-input-widget by Panel
                )
            ],
        )

        return chat_interface

    @pn.depends("current_chat")
    def header(self):
        if self.current_chat is None:
            return

        current_chat_name = ""
        if self.current_chat is not None:
            current_chat_name = self.current_chat["metadata"]["name"]

        chat_name_header = pn.pane.HTML(
            f"<p>{current_chat_name}</p>",
            sizing_mode="stretch_width",
            css_classes=["chat-name-header"],
        )

        chat_documents_pills = []
        if (
            self.current_chat is not None
            and "metadata" in self.current_chat
            and "documents" in self.current_chat["metadata"]
        ):
            doc_names = [d["name"] for d in self.current_chat["metadata"]["documents"]]

            # FIXME: Instead of setting a hard limit of 20 documents here, this should
            #  scale automatically with the width of page
            #  See https://github.com/Quansight/ragna/issues/224
            for doc_name in doc_names[:20]:
                pill = pn.pane.HTML(
                    f"""<div class="chat-document-pill">{doc_name}</div>""",
                    css_classes=["chat-document-pill"],
                )

                chat_documents_pills.append(pill)

        self.chat_info_button.name = f"{self.current_chat['metadata']['assistant']} | {self.current_chat['metadata']['source_storage']}"

        return pn.Row(
            chat_name_header,
            *chat_documents_pills,
            self.chat_info_button,
            css_classes=["central-view-header"],
        )

    def set_loading(self, is_loading):
        self.main_column.loading = is_loading

    def __panel__(self):
        self.main_column = pn.Column(
            self.header,
            self.chat_interface,
            sizing_mode="stretch_width",
            css_classes=["central-view-main-column"],
        )

        return self.main_column
