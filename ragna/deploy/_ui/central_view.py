import uuid

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


class RagnaChatCopyIcon(ReactiveHTML):
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
    msg_data = param.Dict(default={})
    on_click_source_info_callback = param.Callable(default=None)

    def __init__(self, msg_data, user, on_click_source_info_callback=None, **kwargs):
        self.role = msg_data["role"]

        params = {
            "msg_data": msg_data,
            # user is the name of the assistant (eg 'Ragna/DemoAssistant')
            # or the name of the user, depending on the role
            "user": user,
            "on_click_source_info_callback": on_click_source_info_callback,
            "object": msg_data["content"],
            "renderers": [
                lambda txt: RagnaChatMessage.chat_entry_value_renderer(
                    txt, role=self.role
                )
            ],
            "show_timestamp": False,
            "show_reaction_icons": False,
            "show_copy_icon": False,
            "show_user": False,
        }

        params["avatar"] = RagnaChatMessage.get_avatar(self.role, user)

        super().__init__(**(params | kwargs))

        self.update_css_classes()
        self.chat_copy_icon.visible = False

        if self.role == "assistant":
            source_info_button = pn.widgets.Button(
                name="Source Info",
                icon="info-circle",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
            )

            source_info_button.on_click(self.trigger_on_click_source_info_callback)

            copy_button = RagnaChatCopyIcon(
                value=self.object,
                title="Copy",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
            )

            self._composite[1].append(pn.Row(copy_button, source_info_button, height=0))

    def trigger_on_click_source_info_callback(self, event):
        if self.on_click_source_info_callback is not None:
            self.on_click_source_info_callback(event, self)

    def update_css_classes(self):
        role = self.msg_data["role"] if "role" in self.msg_data else None
        self.css_classes = ["chat-entry", f"chat-entry-{role}"]

    @classmethod
    def get_avatar(cls, role, user) -> str:
        if role == "system":
            return "imgs/ragna_logo.svg"
        elif role == "user":
            # FIXME: user needs to be dynamic based on the username that was logged in with
            return "👤"
        elif role == "assistant":
            # FIXME: This needs to represent the assistant somehow
            if user == "Ragna/DemoAssistant":
                return "imgs/ragna_logo.svg"
            elif user.startswith("OpenAI/gpt-3.5"):
                return pn.chat.message.GPT_3_LOGO
            elif user == "OpenAI/gpt-4":
                return pn.chat.message.GPT_4_LOGO

            return "🤖"

        # should never happen
        return "?"

    @classmethod
    def chat_entry_value_renderer(cls, txt, role):
        markdown_css_classes = []
        if role is not None:
            markdown_css_classes = [
                f"chat-entry-{role}",
            ]

        return pn.pane.Markdown(
            txt,
            css_classes=markdown_css_classes,
            stylesheets=[markdown_table_stylesheet],
        )


class RagnaChatInterface(pn.chat.ChatInterface):
    def __init__(self, *objects, **params):
        super().__init__(*objects, **params)

    @param.depends("placeholder_text", watch=True, on_init=True)
    def _update_placeholder(self):
        loading_avatar = RagnaChatMessage.get_avatar("system", None)

        self._placeholder = RagnaChatMessage(
            {
                "role": "system",
                "content": ui.message_loading_indicator,
            },
            user=" ",
            show_timestamp=False,
            avatar=loading_avatar,
            reaction_icons={},
            show_copy_icon=False,
        )


class CentralView(pn.viewable.Viewer):
    current_chat = param.ClassSelector(class_=dict, default=None)
    trigger_scroll_to_latest = param.Integer(default=0)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper
        self.on_click_chat_info = None

    def on_click_chat_info_wrapper(self, event):
        if self.on_click_chat_info is not None:
            pills = "".join(
                [
                    f"""<div class='chat_document_pill'>{d['name']}</div>"""
                    for d in self.current_chat["metadata"]["documents"]
                ]
            )

            grid_height = len(self.current_chat["metadata"]["documents"]) // 3

            advanced_config_data = {
                "Chunk size": self.current_chat["metadata"]["params"]["chunk_size"],
                "Chunk overlap": self.current_chat["metadata"]["params"][
                    "chunk_overlap"
                ],
                "Max context tokens": self.current_chat["metadata"]["params"][
                    "num_tokens"
                ],
                "Max new tokens": self.current_chat["metadata"]["params"][
                    "max_new_tokens"
                ],
            }

            advanced_config_md = "\n".join(
                [f"""- **{k}**: {v}""" for k, v in advanced_config_data.items()]
            )

            markdown = [
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
                advanced_config_md,
            ]

            markdown = "\n".join(markdown)

            self.on_click_chat_info(
                event,
                "Chat Config",
                [
                    pn.pane.Markdown(
                        markdown,
                        dedent=True,
                        # debug
                        # pn.pane.Markdown(f"Chat ID: {self.current_chat['id']}"),
                        stylesheets=[
                            """ :host {  width: 100%; } 
                                                 
                                                .pills_list {
                                                    /*background-color:gold;*/
                                                    display: grid;
                                                    grid-auto-flow: row;
                                                    row-gap: 10px;
                                                    grid-template: repeat({{GRID_HEIGHT}}, 1fr) / repeat(3, 1fr);
                                                    max-height: 200px;
                                                    overflow: scroll;
                                                }
                                                 
                                                .chat_document_pill {
                                                                    background-color: rgb(241,241,241);
                                                                    
                                                                    margin-left: 5px;   
                                                                    margin-right: 5px;
                                                                    padding: 5px 15px;
                                                                    border-radius: 10px;
                                                                    color:var(--accent-color);
                                                                    width:fit-content;
                                                                    grid-column: span 1;
                                                                    
                                                                }   
                                                ul {
                                                    list-style-type: none
                                                }                                                 

                                                """.replace(
                                "{{GRID_HEIGHT}}", str(grid_height)
                            )
                        ],
                    ),
                ],
            )

    def on_click_source_info_wrapper(self, event, msg):
        if self.on_click_chat_info is not None:
            markdown = "This response was generated using the following data from the uploaded files: <br />\n"

            for i in range(len(msg.msg_data["sources"])):
                source = msg.msg_data["sources"][i]

                location = ""
                if source["location"] != "":
                    location = f": {source['location']}"
                markdown += (
                    f"""{(i+1)}. **{source['document']['name']}** {location}\n"""
                )
                markdown += "----\n"

            self.on_click_chat_info(
                event,
                "Source Info",
                [
                    pn.pane.Markdown(
                        markdown,
                        dedent=True,
                        stylesheets=[""" hr { width: 94%; height:1px;  }  """],
                    ),
                ],
            )

    def set_current_chat(self, chat):
        self.current_chat = chat

    async def chat_callback(
        self, contents: str, user: str, instance: pn.chat.ChatInterface
    ):
        self.current_chat["messages"].append({"role": "user", "content": contents})

        try:
            answer = await self.api_wrapper.answer(self.current_chat["id"], contents)

            self.current_chat["messages"].append(answer["message"])

            yield {
                "user": "Ragna",
                "avatar": "🤖",
                "value": answer["message"]["content"],
            }
        except Exception as e:
            print(e)

            yield {
                "user": "Ragna",
                "avatar": RagnaChatMessage.get_avatar("system", None),
                "value": "Sorry, something went wrong. If this problem persists, please contact your administrator.",
            }

    def get_chat_messages(self):
        chat_entries = []

        if self.current_chat is not None:
            assistant = self.current_chat["metadata"]["assistant"]
            # FIXME: user needs to be dynamic based on the username that was logged in with
            username = "User"

            for m in self.current_chat["messages"]:
                chat_entry = RagnaChatMessage(
                    m,
                    username if m["role"] == "user" else assistant,
                    on_click_source_info_callback=self.on_click_source_info_wrapper,
                )
                chat_entries.append(chat_entry)

        return chat_entries

    @pn.depends("current_chat")
    def chat_interface(self):
        if self.current_chat is None:
            return

        chat_interface = RagnaChatInterface(
            callback=self.chat_callback,
            callback_user="Ragna",
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            view_latest=True,
            sizing_mode="stretch_width",
            auto_send_types=[],
            widgets=[
                pn.widgets.TextInput(
                    placeholder="Ask Ragna...",
                    stylesheets=[
                        """:host input[type="text"] { 
                                                                border:none !important;
                                                                box-shadow: 0px 0px 6px 0px rgba(0, 0, 0, 0.2);
                                                                padding: 10px 10px 10px 15px;
                                                            }
                                                        
                                                            :host input[type="text"]:focus { 
                                                                box-shadow: 0px 0px 8px 0px rgba(0, 0, 0, 0.3);
                                                            }

                                                         """
                    ],
                )
            ],
            renderers=[
                lambda txt: RagnaChatMessage.chat_entry_value_renderer(txt, role=None)
            ],
            message_params={
                "show_reaction_icons": False,
                "show_user": False,
                "show_copy_icon": False,
                "show_timestamp": False,
                # the proper avatar for the assistant is not when replacing the default ChatMessage objects
                # with RagnaChatMessage objects.
                "avatar_lookup": lambda user: "👤" if user == "User" else None,
            },
        )

        chat_interface._card.stylesheets += [
            """ 
                                             
                                            :host { 
                                                border:none !important;
                                            }

                                            .chat-feed-log {  
                                                padding-right: 18%;
                                                margin-left: 18% ;
                                                padding-top:25px !important;
                                                
                                            }
                                             
                                            .chat-interface-input-container {
                                                margin-left:19%;
                                                margin-right:20%;
                                                margin-bottom: 20px;
                                            }


                                            """
        ]

        """
        By default, each new message is a ChatMessage object. 
        But for new messages from the AI, we want to have a RagnaChatMessage, that contains the msg data, the sources, etc.
        I haven't found a better way than to watch for the `objects` param of chat_interface, 
            and replace the ChatMessage objects with RagnaChatMessage object.
        We do it only for the new messages from the rag, not for the existing messages, neither for the messages from the user.
        """

        def messages_changed(event):
            if len(chat_interface.objects) != len(self.current_chat["messages"]):
                return

            assistant = self.current_chat["metadata"]["assistant"]
            # FIXME: user needs to be dynamic based on the username that was logged in with
            username = "User"

            needs_refresh = False
            for i in range(len(chat_interface.objects)):
                msg = chat_interface.objects[i]

                if not isinstance(msg, RagnaChatMessage) and msg.user != "User":
                    chat_interface.objects[i] = RagnaChatMessage(
                        self.current_chat["messages"][i],
                        username
                        if self.current_chat["messages"][i]["role"] == "user"
                        else assistant,
                        on_click_source_info_callback=self.on_click_source_info_wrapper,
                    )
                    msg = chat_interface.objects[i]
                    needs_refresh = True

            if needs_refresh:
                chat_interface._chat_log.param.trigger("objects")

        chat_interface.param.watch(
            messages_changed,
            ["objects"],
        )

        # Here, we build a list of RagnaChatMessages from the existing messages of this chat,
        # and set them as the content of the chat interface
        chat_interface.objects = self.get_chat_messages()

        # Now that setting all the objects is done, we can watch the change of objects,
        # ie new messages being appended to the chat. When that happens,
        # make sure we scroll to the latest msg.
        chat_interface.param.watch(
            lambda event: self.param.trigger("trigger_scroll_to_latest"),
            ["objects"],
        )

        return chat_interface

    @pn.depends("current_chat", "trigger_scroll_to_latest")
    def scroll_to_latest_fix(self):
        """
        This snippet needs to be re-rendered many times so the scroll-to-latest happens:
            - each time the current chat changes, hence the pn.depends on current_chat
            - each time a message is appended to the chat, hence the pn.depends on trigger_scroll_to_latest.
                trigger_scroll_to_latest is triggered in the chat_interface method, when chat_interface.objects changes.

        Twist : the HTML script node needs to have a different ID each time it is rendered,
                otherwise the browser doesn't re-render it / doesn't execute the JS part.
                Hence the random ID.
        """

        random_id = str(uuid.uuid4())

        return pn.pane.HTML(
            """<script id="{{RANDOM_ID}}" type="text/javascript">

                            setTimeout(() => {
                                    var chatbox_scrolldiv = $$$('.chat-feed-log')[0];
                                    chatbox_scrolldiv.scrollTop = chatbox_scrolldiv.scrollHeight;
                            }, 150);
                            
            </script>""".replace("{{RANDOM_ID}}", random_id)
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

            for doc_name in doc_names:
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

        chat_info_button = None
        if self.current_chat is not None:
            button_name = f"{self.current_chat['metadata']['assistant']} | {self.current_chat['metadata']['source_storage']}"
            chat_info_button = pn.widgets.Button(
                name=button_name, button_style="outline", icon="info-circle"
            )
            chat_info_button.stylesheets.append(
                """
                                        :host {  
                                                    margin-top:10px;
                                        }
                                        
                                    """
            )
            chat_info_button.on_click(self.on_click_chat_info_wrapper)

        return pn.Row(
            chat_name_header,
            *chat_documents_pills,
            chat_info_button,
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
            self.scroll_to_latest_fix,
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
