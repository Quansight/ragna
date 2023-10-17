import panel as pn
import param


chat_entry_stylesheets = [
    """ :host .right, :host .center, :host .chat-entry {
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
                    }
            """,
    """
                    :host .chat-entry-user {
                        background-color: rgba(243, 243, 243);
                        border: 1px solid rgb(238, 238, 238);
                    }
                """,
    """
                    :host .chat-entry-ragna {
                        background-color: white;
                        border: 1px solid rgb(234, 234, 234);
                    }
                """,
    """
                    :host .avatar {
                        margin-top:0px;
                    }
                """,
]
pn.widgets.ChatEntry._stylesheets = (
    pn.widgets.ChatEntry._stylesheets + chat_entry_stylesheets
)


def chat_entry_value_renderer(txt, role):
    return pn.pane.Markdown(
        txt,
        css_classes=["chat-entry-user" if role == "user" else "chat-entry-ragna"],
        stylesheets=[
            " \n                    table {\n                        margin-top:10px;\n                        margin-bottom:10px;\n                        \n                    }\n                "
        ],
    )


def build_chat_entry(role, txt, timestamp=None):
    chat_entry = pn.widgets.ChatEntry(
        value=txt,
        # user="User" if m["role"] == "user" else "Ragna (Chat GPT 3.5)",
        # actually looking better with empty user name than show_user=False
        # show_user=False,
        renderers=[lambda txt: chat_entry_value_renderer(txt, role=role)],
        css_classes=[
            "chat-entry",
            "chat-entry-user" if role == "user" else "chat-entry-ragna",
        ],
        avatar="👤" if role == "user" else "🤖",
        timestamp=timestamp,
        show_reaction_icons=False,
        show_copy_icon=True,
        show_user=False,
    )

    chat_entry.chat_copy_icon.visible = False
    return chat_entry


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

    def set_current_chat(self, chat):
        self.current_chat = chat

    async def chat_callback(
        self, contents: str, user: str, instance: pn.widgets.ChatInterface
    ):
        # message = f"Echoing {user}: {contents}"
        # return message
        print(user, contents)

        yield {
            "user": "Ragna",
            "avatar": "🤖",
            "value": self.api_wrapper.answer(self.current_chat["id"], contents),
        }

        #
        # yield build_chat_entry("Ragna", self.api_wrapper.answer(self.current_chat["id"], contents))

        print("yielded")
        return

        if user == "User":
            pass
        else:
            self.api_wrapper.answer(self.current_chat["id"], contents)

        yield pn.widgets.ChatEntry(
            value=contents,
            user="",
            renderers=[
                lambda txt: pn.pane.Markdown(
                    txt,
                    css_classes=[
                        "chat-entry-user" if user == "user" else "chat-entry-ragna"
                    ],
                )
            ],
            css_classes=[
                "chat-entry",
                "chat-entry-user" if user == "User" else "chat-entry-ragna",
            ],
            avatar="👤" if user == "User" else "🤖",
            # timestamp=m["timestamp"],
            show_reaction_icons=False,
            # show_user=False,
        )

        if user != "User":
            instance.respond()

    def get_chat_entries(self):
        chat_entries = []

        if self.current_chat is not None:
            for m in self.current_chat["messages"]:
                chat_entry = build_chat_entry(m["role"], m["content"], m["timestamp"])

                # Works, but ugly code
                # chat_entry._composite[1].stylesheets = list(chat_entry._composite[1].stylesheets) + [
                #         """ :host div.center {
                #                 width: 100%;
                #             }
                #             :host {
                #                 /*background-color:red !important;*/
                #             }
                #         """.strip(),
                # ]
                # chat_entry._composite[1][1][0].stylesheets += [ """ :host, :host .message {width:calc(100% - 10px);}""" ]

                chat_entries.append(chat_entry)

        return chat_entries

    @pn.depends("current_chat")
    def chat_interface(self):
        chat_entries = self.get_chat_entries()

        chat_interface = pn.widgets.ChatInterface(
            callback=self.chat_callback,
            callback_user="Ragna",
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            value=chat_entries,
            view_latest=True,
            sizing_mode="stretch_width",
            renderers=[lambda txt: pn.pane.Markdown(txt)],
            entry_params={"show_reaction_icons": False, "show_user": False},
            stylesheets=[
                """
                    :host {  
                    /*background-color:pink;*/
                    margin-left: 18% !important;
                    /*margin-right: 18% !important;*/
                    min-width:45%;
                    border: none !important;
                    height:100%;
                    margin-bottom: 20px; 
                    }

                    :host .chat-feed-log {
                        padding-right:18% !important;
                    }

                    :host .chat-interface-input-container {
                        margin-right: 19%;
                        margin-left:2%;
                    }

                    """,
            ],
        )

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
                                                    color:rgba(69, 35, 145, 1);
                                                    
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
        result = pn.Column(
            self.header,
            self.chat_interface,
            sizing_mode="stretch_width",
            stylesheets=[
                """                    :host { 
                                            /*background-color: orange;*/
                                            /*background-color: #FCFCFC;*/
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