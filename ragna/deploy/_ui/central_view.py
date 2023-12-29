from __future__ import annotations

from typing import Callable, Literal, Optional

import panel as pn
import param
from panel.reactive import ReactiveHTML

from . import styles as ui

# TODO : move all the CSS rules in a dedicated file

chat_entry_stylesheets = [
    """ 
            :host .right, :host .center, :host .chat-entry {
                    width:100% !important;
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
            }
    """,
    """
            :host .chat-entry-user {
                background-color: rgba(243, 243, 243);
                border: 1px solid rgb(238, 238, 238);
                margin-bottom: 20px;
            }
    """,
    # The padding bottom is used to give some space for the copy and source info buttons
    """
            :host .chat-entry-ragna, :host .chat-entry-system,  :host .chat-entry-assistant{
                background-color: white;
                border: 1px solid rgb(234, 234, 234);
                padding-bottom: 30px;
                margin-bottom: 20px;
            }
    """,
    """
            :host .avatar {
                margin-top:0px;
                box-shadow: unset;
            }
    """,
    """ 
            :host .left {
                height: unset !important;
                min-height: unset !important;
            }
    """,
    """ 
            :host .right {
                
            }
    """,
]
pn.chat.ChatMessage._stylesheets = (
    pn.chat.ChatMessage._stylesheets + chat_entry_stylesheets
)

markdown_table_stylesheet = """

            /* Better rendering of the markdown tables */
            table { 
                margin-top:10px;
                margin-bottom:10px;
            }
            """

# subclass pn.chat.icon.ChatCopyIcon


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
        show_timestamp=True,
    ):
        super().__init__(
            object=content,
            role=role,
            user=user,
            sources=sources,
            on_click_source_info_callback=on_click_source_info_callback,
            show_timestamp=show_timestamp,
            show_reaction_icons=False,
            show_user=False,
            show_copy_icon=False,
            renderers=[self._render],
        )

        if self.sources:
            self._update_object_pane()

    def _update_object_pane(self, event=None):
        super()._update_object_pane(event)
        if self.sources:
            self._object_panel = self._center_row[0] = pn.Column(
                self._object_panel, self._copy_and_source_view_buttons()
            )

    def _copy_and_source_view_buttons(self) -> pn.Row:
        return pn.Row(
            CopyToClipboardButton(
                value=self.object,
                title="Copy",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
            ),
            pn.widgets.Button(
                name="Source Info",
                icon="info-circle",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
                on_click=lambda event: self.on_click_source_info_callback(
                    event, self.sources
                ),
            ),
            height=0,
        )

    def avatar_lookup(self, user: str) -> str:
        if self.role == "system":
            return "imgs/ragna_logo.svg"
        elif self.role == "user":
            return user[0].upper()

        try:
            organization, model = user.split("/")
        except ValueError:
            organization = None
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
        else:
            return model[0].upper()

    def _render(self, content: str) -> pn.viewable.Viewable:
        return pn.pane.Markdown(
            content,
            css_classes=["chat-message", f"chat-message-{self.role}"],
            stylesheets=[markdown_table_stylesheet],
        )


class RagnaChatInterface(pn.chat.ChatInterface):
    @param.depends("placeholder_text", watch=True, on_init=True)
    def _update_placeholder(self):
        self._placeholder = RagnaChatMessage(
            ui.message_loading_indicator,
            role="system",
            user="system",
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
    # trigger_scroll_to_latest = param.Integer(default=0)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        # FIXME: make this dynamic from the login
        self.user = "RagnaUser"
        self.api_wrapper = api_wrapper
        self.chat_info_button = pn.widgets.Button(
            # The name will be filled at runtime in self.header
            name="",
            on_click=self.on_click_chat_info_wrapper,
            button_style="outline",
            icon="info-circle",
            stylesheets=[":host { margin-top:10px; }"],
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
                    stylesheets=ui.stylesheets(
                        (":host", {"width": "100%"}),
                        (
                            ".pills_list",
                            {
                                # "background-color": "gold",
                                "display": "grid",
                                "grid-auto-flow": "row",
                                "row-gap": "10px",
                                "grid-template": f"repeat({grid_height}, 1fr) / repeat(3, 1fr)",
                                "max-height": "200px",
                                "overflow": "scroll",
                            },
                        ),
                        (
                            ".chat_document_pill",
                            {
                                "background-color": "rgb(241,241,241)",
                                "margin-left": "5px",
                                "margin-right": "5px",
                                "padding": "5px 15px",
                                "border-radius": "10px",
                                "color": "var(--accent-color)",
                                "width": "fit-content",
                                "grid-column": "span 1",
                            },
                        ),
                        ("ul", {"list-style-type": "none"}),
                    ),
                ),
            ],
        )

    def on_click_source_info_wrapper(self, event, sources):
        if self.on_click_chat_info is None:
            return

        markdown = [
            "This response was generated using the following data from the uploaded files: <br />"
        ]
        for rank, source in enumerate(sources, 1):
            location = source["location"]
            if location:
                location = f": {location}"
            markdown.append(f"{rank}. **{source['document']['name']}**{location}")
            markdown.append("----")

        self.on_click_chat_info(
            event,
            "Source Info",
            [
                pn.pane.Markdown(
                    "\n".join(markdown),
                    dedent=True,
                    stylesheets=[""" hr { width: 94%; height:1px;  }  """],
                ),
            ],
        )

    def set_current_chat(self, chat):
        self.current_chat = chat

    async def chat_callback(
        self, content: str, user: str, instance: pn.chat.ChatInterface
    ):
        import asyncio

        await asyncio.sleep(10)
        try:
            answer = await self.api_wrapper.answer(self.current_chat["id"], content)

            yield RagnaChatMessage(
                answer["content"],
                role="assistant",
                user=self.current_chat["metadata"]["assistant"],
                sources=answer["sources"],
                on_click_source_info_callback=self.on_click_source_info_wrapper,
            )
        except Exception:
            yield RagnaChatMessage(
                (
                    "Sorry, something went wrong. "
                    "If this problem persists, please contact your administrator."
                ),
                role="system",
                user="system",
            )

    @pn.depends("current_chat")
    def chat_interface(self):
        if self.current_chat is None:
            return

        chat_interface = RagnaChatInterface(
            callback=self.chat_callback,
            user=self.user,
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            view_latest=True,
            sizing_mode="stretch_width",
            # TODO: @panel hitting enter to send a message is fine, but clicking
            #  somewhere else should not send the message.
            auto_send_types=[],
            widgets=[
                pn.widgets.TextInput(
                    placeholder="Ask a question about the documents",
                    stylesheets=ui.stylesheets(
                        (
                            ":host input[type='text']",
                            {
                                "border": "none !important",
                                "box-shadow": "0px 0px 6px 0px rgba(0, 0, 0, 0.2)",
                                "padding": "10px 10px 10px 15px",
                            },
                        ),
                        (
                            ":host input[type='text']:focus",
                            {
                                "box-shadow": "0px 0px 8px 0px rgba(0, 0, 0, 0.3)",
                            },
                        ),
                    ),
                )
            ],
        )

        # TODO: @panel ChatFeed has a card_params parameter, but this isn't used
        #  anywhere. I assume we should be able to use it here.
        chat_interface._card.stylesheets.extend(
            ui.stylesheets(
                (":host", {"border": "none !important"}),
                (
                    ".chat-feed-log",
                    {
                        "padding-right": "18%",
                        "margin-left": "18%",
                        "padding-top": "25px !important",
                    },
                ),
                (
                    ".chat-interface-input-container",
                    {
                        "margin-left": "19%",
                        "margin-right": "20%",
                        "margin-bottom": "20px",
                    },
                ),
            )
        )

        #
        # chat_interface.param.watch(
        #     messages_changed,
        #     ["objects"],
        # )
        #
        # # Here, we build a list of RagnaChatMessages from the existing messages of this chat,
        # # and set them as the content of the chat interface
        # chat_interface.objects = self.get_chat_messages()
        #
        # # Now that setting all the objects is done, we can watch the change of objects,
        # # ie new messages being appended to the chat. When that happens,
        # # make sure we scroll to the latest msg.
        # chat_interface.param.watch(
        #     lambda event: self.param.trigger("trigger_scroll_to_latest"),
        #     ["objects"],
        # )

        return chat_interface

    # @pn.depends("current_chat", "trigger_scroll_to_latest")
    # def scroll_to_latest_fix(self):
    #     """
    #     This snippet needs to be re-rendered many times so the scroll-to-latest happens:
    #         - each time the current chat changes, hence the pn.depends on current_chat
    #         - each time a message is appended to the chat, hence the pn.depends on trigger_scroll_to_latest.
    #             trigger_scroll_to_latest is triggered in the chat_interface method, when chat_interface.objects changes.
    #
    #     Twist : the HTML script node needs to have a different ID each time it is rendered,
    #             otherwise the browser doesn't re-render it / doesn't execute the JS part.
    #             Hence the random ID.
    #     """
    #
    #     random_id = str(uuid.uuid4())
    #
    #     return pn.pane.HTML(
    #         """<script id="{{RANDOM_ID}}" type="text/javascript">
    #
    #                         setTimeout(() => {
    #                                 var chatbox_scrolldiv = $$$('.chat-feed-log')[0];
    #                                 chatbox_scrolldiv.scrollTop = chatbox_scrolldiv.scrollHeight;
    #                         }, 150);
    #
    #         </script>""".replace(
    #             "{{RANDOM_ID}}", random_id
    #         )
    #     )

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
            stylesheets=[
                """ 

                        :host p {
                            max-width: 50%;
                            height:100%;

                            text-overflow: ellipsis;
                            white-space: nowrap;
                            overflow: hidden;
                            margin: 0px 0px 0px 10px;

                            font-size:20px;
                            text-decoration: underline;
                            text-underline-offset: 4px;

                            /* I don't understand why this is necessary to vertically align the text ... */
                            line-height:250%; 
                            
                        }
                        """
            ],
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
                    f"""<div class="chat_document_pill">{doc_name}</div>""",
                    stylesheets=[
                        """
                                                 :host {
                                                    background-color: rgb(241,241,241);
                                                    margin-top: 15px;
                                                    margin-left: 5px;   
                                                    margin-right: 5px;
                                                    padding: 5px 15px;
                                                    border-radius: 10px;
                                                    color:var(--accent-color);
                                                    
                                                 }   

                                                 """
                    ],
                )

                chat_documents_pills.append(pill)

        self.chat_info_button.name = f"{self.current_chat['metadata']['assistant']} | {self.current_chat['metadata']['source_storage']}"

        return pn.Row(
            chat_name_header,
            *chat_documents_pills,
            self.chat_info_button,
            stylesheets=[
                """:host {  
                                    background-color: #F9F9F9;
                                    border-bottom: 1px solid #EEEEEE;
                                    width: 100% !important;
                                    margin:0px;
                                    height:54px;
                                }

                                :host div {
                                    
                                    vertical-align: middle;
                                }
"""
            ],
        )

    def set_loading(self, is_loading):
        self.main_column.loading = is_loading

    def __panel__(self):
        """
        The ChatInterface.view_latest option doesn't seem to work.
        So to scroll to the latest message, we use some JS trick.

        There might be a more elegant solution than running this after a timeout of 200ms,
        but without it, the $$$ function isn't available yet.
        And even if I add the $$$ here, the fix itself doesn't work and the chat doesn't scroll
        to the bottom.
        """

        self.main_column = pn.Column(
            self.header,
            self.chat_interface,
            # self.scroll_to_latest_fix,
            sizing_mode="stretch_width",
            stylesheets=[
                """                    :host { 
                                            background-color: #F9F9F9;
                                            
                                            height:100%;
                                            max-width: 100%;
                                            margin-left: min(15px, 2%);
                                            border-left: 1px solid #EEEEEE;
                                            border-right: 1px solid #EEEEEE;
                                        }
                                """
            ],
        )

        return self.main_column
