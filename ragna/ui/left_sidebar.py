import panel as pn
import param

from ragna import __version__ as ragna_version


class LeftSidebar(pn.viewable.Viewer):
    chats = param.List(default=[])
    current_chat_id = param.String(default=None)
    refresh_counter = param.Integer(default=0)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.on_click_chat = None
        self.on_click_new_chat = None

        self.chat_buttons = []

        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

    def trigger_on_click_new_chat(self, event):
        if event.old > event.new:
            return

        if self.on_click_new_chat is not None:
            self.on_click_new_chat(event)

    def on_click_chat_wrapper(self, event, chat):
        # This is a hack to avoid the event being triggered twice in a row
        if event.old > event.new:
            return

        # update the UI, unselect all buttons ...
        for button in self.chat_buttons:
            if "selected" in button.css_classes:
                button.css_classes = []

        # ... and select the one that was clicked
        event.obj.css_classes = ["selected"]

        # call the actual callback
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

    def refresh(self):
        self.refresh_counter += 1

    @pn.depends("refresh_counter", "chats", "current_chat_id", on_init=True)
    def __panel__(self):
        self.chat_buttons = []
        for chat in self.chats:
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
                                        content: url("/imgs/chat_bubble.svg");
                                        margin-right: 10px;
                                        display: inline-block;
                                      }

                                      :host(.selected) div button, :host div button:hover {
                                        background-color: #F3F3F3 !important;
                                        border-radius: 0px 5px 5px 0px !important;
                                        border-left: solid 4px var(--accent-color) !important;
                                      }

                                      
                                      """
            )
            self.chat_buttons.append(button)

            try:
                if chat["id"] == self.current_chat_id:
                    button.css_classes = ["selected"]
            except Exception:
                pass

        header = pn.pane.HTML(
            """<img src="imgs/ragna_logo.svg" height="32px" /><span>Ragna</span>""",
            stylesheets=[
                """ 
                                               :host { 
                                                    background-color: #F9F9F9;
                                                    border-bottom: 1px solid #EEEEEE;

                                                    width: 100%;
                                                    height: 54px;
                                                    margin: 0;
                                               }

                                                :host div {
                                                    display: flex;
                                                    align-items: center;
                                                    height: 100%;
                                                }

                                                :host img {
                                                    margin: 5px;
                                                    margin-left: 12px;
                                                }

                                               :host span { 
                                                    margin-left: 20px;
                                                    font-size: 24px;
                                                    font-weight: 600;
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
                            background-color: var(--accent-color) !important;
                            text-align: left;
                        }
                """
            ],
        )

        new_chat_button.on_click(self.trigger_on_click_new_chat)

        objects = (
            [header, new_chat_button]
            + self.chat_buttons
            + [
                pn.layout.VSpacer(),
                pn.pane.HTML(f"version: {ragna_version}"),
                # self.footer()
            ]
        )

        result = pn.Column(
            *objects,
            stylesheets=[
                """   
                        :host { 
                            overflow-x: hidden;
                            height: 100%;
                            width:100%;
                            border-right: 1px solid #EEEEEE;
                        }
                """
            ],
        )

        return result
