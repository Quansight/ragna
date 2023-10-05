import panel as pn
import param


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
        if user == "User":
            yield {
                "user": "Ragna",
                "avatar": "🤖",
                "value": self.api_wrapper.answer(self.current_chat["id"], contents),
            }
            instance.respond()

    def get_chat_entries(self):
        ragna_stylesheet = """
                            :host {
                                
                            }
                                """

        user_stylesheet = """
                    :host {
                            flex-direction:row-reverse;
                            }

                    .right {
                            width:fit-content;
                    }
                    """

        chat_entries = []

        if self.current_chat is not None:
            for m in self.current_chat["messages"]:
                chat_entry = pn.widgets.ChatEntry(
                    value=m["content"],
                    user="User" if m["role"] == "user" else "Ragna",
                    timestamp=m["timestamp"],
                    show_reaction_icons=False,
                    # show_user=False,
                    stylesheets=[
                        """ :host {  background-color:transparent; }
        
                        """,
                        user_stylesheet if m["role"] == "user" else ragna_stylesheet,
                    ],
                )

                # print(chat_entry._composite)
                # chat_entry._composite is a row
                # chat_entry._composite[1] is a Column containing the username, the text+reactions, and the timestamp
                # chat_entry._composite[1][1] is the row containing the text+reactions
                # print(chat_entry._composite[1][1][0])
                chat_entry._composite[1][1][0].stylesheets = [
                    """ :host { 
                                                                background-color: #F3F3F3 !important;
                                                                border-radius: 10px !important;
                                                                border: 1px solid rgb(248, 248, 248) !important;
                                                            
                                                            } """
                ]

                chat_entries.append(chat_entry)

        return chat_entries

    @pn.depends("current_chat")
    def chat_interface(self):
        chat_entries = self.get_chat_entries()

        chat_interface = pn.widgets.ChatInterface(
            callback=self.chat_callback,
            callback_user="System",
            show_rerun=False,
            show_undo=False,
            show_clear=False,
            show_button_name=False,
            value=chat_entries,
            view_latest=True,
            sizing_mode="stretch_width",
            stylesheets=[
                """
                    :host {  
                    /*background-color:pink;*/
                    margin-left: 18% !important;
                    margin-right: 18% !important;
                    min-width:45%;
                    }
                    """,
            ],
        )

        chat_interface._composite.objects = [pn.layout.spacer.VSpacer()] + [
            w
            for w in chat_interface._composite.objects
            if not isinstance(w, pn.layout.spacer.VSpacer)
        ]

        chat_interface._chat_log.stylesheets.append(
            """ :host .chat-feed-log {  
                    height: unset; max-height: 90%; }
            """
        )

        return chat_interface

    @pn.depends("current_chat")
    def header(self):
        current_chat_name = ""
        if self.current_chat is not None:
            current_chat_name = self.current_chat["metadata"]["name"]

        # self.current_chat['metadata']['document_ids']

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
                                            background-color: #FCFCFC;
                                            
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
