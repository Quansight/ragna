import panel as pn


class LeftSidebar(pn.viewable.Viewer):
    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper
        self.on_click_chat = None

        self.chat_buttons = []

    def on_click_chat_wrapper(self, event, chat):
        print("wrapper", event)

        for button in self.chat_buttons:
            if "selected" in button.css_classes:
                button.css_classes = []

        # event.obj.css_classes.append("selected")
        event.obj.css_classes = ["selected"]

        if self.on_click_chat is not None:
            self.on_click_chat(chat)

    def footer(self):
        return pn.pane.HTML(
            """<div class='user_block'> Username </div>
                            """,
            styles={},
            stylesheets=[
                """ 
                                            
                                :host {
                                        height: 64px;
                                        width: 100%;
                                        margin: 0;
                                    
                                }

                                :host .user_block {
                                            height:64px;
                                            background-color: rgb(248, 248, 248);
                                            border-top: solid 1px rgb(248, 248, 248);
                                }
                            """
            ],
        )

    def __panel__(self):
        chats = self.api_wrapper.get_chats()

        current_chat_button = None

        try:
            print(pn.state.session_args.get("current_chat_id")[0])
        except Exception:
            pass

        for chat in chats:
            button = pn.widgets.Button(
                name=chat["metadata"]["name"], button_style="outline"
            )
            button.on_click(lambda event, c=chat: self.on_click_chat_wrapper(event, c))

            button.stylesheets.append(
                """
                                      :host {  
                                                width:90%;
                                                min-width: 200px;
                                        }
                                      
                                      :host div button {
                                        overflow: hidden;
                                        text-overflow: ellipsis;
                                        text-align:left;
                                        border: 0px !important;
                                      
                                      }

                                      :host div button:before {
                                        content: url("/imgs/chat_bubble.png");
                                        margin-right: 10px;
                                        display: inline-block;
                                      }

                                      :host(.selected) div button, :host div button:hover {
                                        background-color: #F3F3F3 !important;
                                        border-radius: 0px 5px 5px 0px !important;
                                        border-left: solid 4px #452391 !important;
                                      }

                                      
                                      """
            )
            self.chat_buttons.append(button)

            try:
                if chat["id"] == pn.state.session_args.get("current_chat_id")[0].decode(
                    "utf-8"
                ):
                    current_chat_button = button
            except Exception:
                pass

        header = pn.pane.Markdown(
            "# Ragna",
            stylesheets=[
                """ 
                                               :host { 
                                                    background-color: rgb(248, 248, 248);
                                                    width: 100%;
                                                    margin: 0;
                                               }

                                               :host div h1 { 
                                                    margin-left: 40px;
                                                    font-size: 20px;
                                               }
                                    """
            ],
        )

        new_chat_button = pn.widgets.Button(
            name="New Chat",
            button_type="primary",
            icon="plus",
            stylesheets=[
                """ 
                                                        :host { 
                                                          width: 90%;
                                                         margin-left: 10px;
                                                         margin-top: 10px;
                                                          
                                                        }
                                                         :host div button { 
                                                         background-color: #452391 !important;
                                                         text-align: left;
                                                          
                                                         }
"""
            ],
        )

        objects = (
            [header, new_chat_button]
            + self.chat_buttons
            + [pn.layout.VSpacer(), pn.pane.HTML("version: 1.0"), self.footer()]
        )

        if len(chats) > 0:
            self.on_click_chat(chats[0])

        result = pn.Column(
            *objects,
            stylesheets=[
                """   
                                        :host { 
                                            
                                            background-color: white;
                                            overflow-x: hidden;
                                            height: 100%;
                                            min-width: 220px;
                                            width: 15%;
                                            border-right: 1px solid #EEEEEE;
                                        }
                                """
            ],
        )

        if current_chat_button is not None:
            current_chat_button.clicks = 1

        return result
