import panel as pn
import param

import ragna.ui.styles as ui

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
            :host .chat-entry-ragna {
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


class RagnaChatMessage(pn.chat.ChatMessage):
    msg_data = param.Dict(default={})
    on_click_source_info_callback = param.Callable(default=None)

    def __init__(self, msg_data, on_click_source_info_callback=None):
        role = msg_data["role"] if "role" in msg_data else None

        params = {
            "msg_data": msg_data,
            "on_click_source_info_callback": on_click_source_info_callback,
            "object": msg_data["content"],
            "renderers": [
                lambda txt: RagnaChatMessage.chat_entry_value_renderer(txt, role=role)
            ],
            "show_timestamp": False,
            "show_reaction_icons": False,
            "show_copy_icon": False,
            "show_user": False,
        }

        params["user"] = "User" if role == "user" else "Ragna"
        params["avatar"] = "👤" if role == "user" else "🤖"

        super().__init__(**params)

        self.update_css_classes()
        self.chat_copy_icon.visible = False

        if role != "user":
            source_info_button = pn.widgets.Button(
                name="Source Info",
                icon="info-circle",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
            )

            source_info_button.on_click(self.trigger_on_click_source_info_callback)

            copy_button = pn.widgets.Button(
                name="Copy",
                icon="clipboard",
                stylesheets=[
                    ui.CHAT_INTERFACE_CUSTOM_BUTTON,
                ],
            )
            copy_button.on_click(lambda event: print("on click copy button", event))

            copy_js = """console.log("test", source); navigator.clipboard.writeText(source);"""
            copy_button.js_on_click(args={"source": self.object}, code=copy_js)

            self._composite[1].append(pn.Row(copy_button, source_info_button, height=0))

    def trigger_on_click_source_info_callback(self, event):
        if self.on_click_source_info_callback is not None:
            self.on_click_source_info_callback(event, self)

    def update_css_classes(self):
        role = self.msg_data["role"] if "role" in self.msg_data else None
        self.css_classes = [
            "chat-entry",
            "chat-entry-user" if role == "user" else "chat-entry-ragna",
        ]

    @classmethod
    def chat_entry_value_renderer(cls, txt, role):
        markdown_css_classes = []
        if role is not None:
            markdown_css_classes = [
                "chat-entry-user" if role == "user" else "chat-entry-ragna"
            ]

        return pn.pane.Markdown(
            txt,
            css_classes=markdown_css_classes,
            stylesheets=[markdown_table_stylesheet],
        )


class CentralView(pn.viewable.Viewer):
    current_chat = param.ClassSelector(class_=dict, default=None)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper
        self.on_click_chat_info = None

    def on_click_chat_info_wrapper(self, event):
        if self.on_click_chat_info is not None:
            self.on_click_chat_info(
                event,
                pn.Column(
                    pn.pane.Markdown(f"Chat ID: {self.current_chat['id']}"),
                    stylesheets=[""" :host {  background-color: lightblue ; }  """],
                ),
            )

    def on_click_source_info_wrapper(self, event, msg):
        if self.on_click_chat_info is not None:
            markdown = "This response was generated using the following data from the uploaded files: <br />\n"

            for i in range(len(msg.msg_data["sources"])):
                source = msg.msg_data["sources"][i]
                print(source)
                location = ""
                if source["location"] != "":
                    location = f": {source['location']}"
                markdown += (
                    f"""{(i+1)}. **{source['document']['name']}** {location}\n"""
                )
                markdown += "----\n"

            self.on_click_chat_info(
                event,
                pn.Column(
                    pn.pane.Markdown(
                        markdown,
                        dedent=True,
                        stylesheets=[""" hr { width: 94%; height:1px;  }  """],
                    ),
                    # Debug bloc :
                    # pn.pane.Markdown(
                    #         f"""Chat ID: {self.current_chat['id']} <br />
                    #                     Message ID: {msg.msg_data['id']} <br />
                    #                     Sources: {msg.msg_data['sources']}""",
                    #         dedent=True,
                    #     stylesheets=[""" :host {  background-color: red ; }  """]
                    # ),
                ),
            )

    def set_current_chat(self, chat):
        self.current_chat = chat

    async def chat_callback(
        self, contents: str, user: str, instance: pn.chat.ChatInterface
    ):
        self.current_chat["messages"].append({"role": "user", "content": contents})

        answer = self.api_wrapper.answer(self.current_chat["id"], contents)

        self.current_chat["messages"].append(answer["message"])

        yield {
            "user": "Ragna",
            "avatar": "🤖",
            "value": answer["message"]["content"],
        }

    def get_chat_messages(self):
        chat_entries = []

        if self.current_chat is not None:
            for m in self.current_chat["messages"]:
                chat_entry = RagnaChatMessage(
                    m, on_click_source_info_callback=self.on_click_source_info_wrapper
                )
                chat_entries.append(chat_entry)

        return chat_entries

    @pn.depends("current_chat")
    def chat_interface(self):
        chat_interface = pn.chat.ChatInterface(
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
                "avatar_lookup": lambda user: "👤" if user == "User" else "🤖",
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

        # Trick to make the chat start from the bottom :
        #  - move the spacer first, and not last
        # chat_interface._composite.objects =  (
        #     [pn.layout.spacer.VSpacer()] +
        #     [
        #     w
        #     for w in chat_interface._composite.objects
        #     if not isinstance(w, pn.layout.spacer.VSpacer)
        # ])
        # chat_interface._chat_log.stylesheets.append(
        #     """ :host .chat-feed-log {
        #             height: unset; max-height: 90%; }
        #     """
        # )

        """
        By default, each new message is a ChatMessage object. 
        But for new messages from the AI, we want to have a RagnaChatMessage, that contains the msg data, the sources, etc.
        I haven't found a better way than to watch for the `objects` param of chat_interface, 
            and replace the ChatMessage objects with RagnaChatMessage object.
        We do it only for the new messages from the rag, not for the existing messages, neither for the messages from the user.
        """

        def messages_changed(event):
            needs_refresh = False
            for i in range(len(chat_interface.objects)):
                msg = chat_interface.objects[i]
                if (
                    len(chat_interface.objects) == len(self.current_chat["messages"])
                    and not isinstance(msg, RagnaChatMessage)
                    and msg.user != "User"
                ):
                    chat_interface.objects[i] = RagnaChatMessage(
                        self.current_chat["messages"][i],
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

        return chat_interface

    @pn.depends("current_chat")
    def header(self):
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

        chat_info_button = pn.widgets.Button(
            name="Chat Info", button_style="outline", icon="info-circle"
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

    def __panel__(self):
        """
        The ChatInterface.view_latest option doesn't seem to work.
        So to scroll to the latest message, we use some JS trick.

        There might be a more elegant solution than running this after a timeout of 200ms,
        but without it, the $$$ function isn't available yet.
        And even if I add the $$$ here, the fix itself doesn't work and the chat doesn't scroll
        to the bottom.
        """

        scroll_to_latest_fix = pn.pane.HTML(
            """<script type="text/javascript">
                            setTimeout(() => {
                                    var chatbox_scrolldiv = $$$('.chat-feed-log')[0];
                                    chatbox_scrolldiv.scrollTop = chatbox_scrolldiv.scrollHeight;
                            }, 200);
                         </script>"""
        )

        result = pn.Column(
            self.header,
            self.chat_interface,
            scroll_to_latest_fix,
            sizing_mode="stretch_width",
            stylesheets=[
                """                    :host { 
                                            background-color: white;
                                            
                                            height:100%;
                                            max-width: 100%;
                                            margin-left: min(15px, 2%);
                                            border-left: 1px solid #EEEEEE;
                                            border-right: 1px solid #EEEEEE;
                                        }
                                """
            ],
        )

        return result
