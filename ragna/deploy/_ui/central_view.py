from __future__ import annotations

import functools
from typing import Callable, Literal, Optional, cast

import panel as pn
import param
from panel.reactive import ReactiveHTML

from . import styles as ui


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

    _stylesheets = ["css/chat_interface/copybutton.css"]


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
        assistant_toolbar_visible=True,  # hide the toolbar during streaming
    ):
        css_class = f"message-content-{self.role}"
        self.content_pane = pn.pane.Markdown(
            content,
            css_classes=["message-content", css_class],
        )

        # we make this available on the instance so that we can update the value later
        self.clipboard_button = CopyToClipboardButton(
            value=self.content_pane.object, title="Copy"
        )

        # we make this available on the instance so that we can toggle the visibility
        self.assistant_toolbar = pn.Row(
            self.clipboard_button,
            pn.widgets.Button(
                name="Source Info",
                icon="info-circle",
                css_classes=["source-info-button"],
                on_click=lambda event: self.on_click_source_info_callback(
                    event, self.sources
                ),
            ),
            visible=assistant_toolbar_visible,
        )

        if role == "assistant":
            assert sources is not None
            object = pn.Column(
                self.content_pane,
                self.assistant_toolbar,
                css_classes=["message-content-assistant-with-buttons"],
            )
        else:
            object = self.content_pane

        object.css_classes.append(
            "message-content-no-border" if role == "user" else "message-content-border"
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
            avatar_lookup=functools.partial(self._ragna_avatar_lookup, role=role),
        )
        self._stylesheets.append("css/chat_interface/chatmessage.css")

    # This cannot be a bound method, because it creates a reference cycle when trying
    # to access the repr of the message. See
    # https://github.com/Quansight/ragna/issues/359 for details.
    @staticmethod
    def _ragna_avatar_lookup(user: str, *, role: str) -> str:
        if role == "system":
            return "imgs/ragna_logo.svg"
        elif role == "user":
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
                    stylesheets=[
                        ui.css(
                            ":host(.chat_info_markdown) .pills_list",
                            {
                                "grid-template": f"repeat({grid_height}, 1fr) / repeat(3, 1fr)",
                            },
                        )
                    ],
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
                assistant_toolbar_visible=False,
            )
            yield message

            async for chunk in answer_stream:
                message.content_pane.object += chunk["content"]
            message.clipboard_button.value = message.content_pane.object
            message.assistant_toolbar.visible = True

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

        return RagnaChatInterface(
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
            show_activity_dot=False,
        )

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
