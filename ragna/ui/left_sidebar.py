import panel as pn
import param

import ragna.ui.js as js


class LeftSidebar(pn.viewable.Viewer):
    refresh_counter = param.Integer(default=0)

    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper
        self.on_click_chat = None
        self.on_click_new_chat = None

        self.chat_buttons = []

    def trigger_on_click_new_chat(self, event):
        if self.on_click_new_chat is not None:
            self.on_click_new_chat(event)

    def on_click_chat_wrapper(self, event, chat):
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

    @pn.depends("refresh_counter")
    def __panel__(self):
        chats = self.api_wrapper.get_chats()

        # current_chat_button = None
        current_chat = None

        self.chat_buttons = []
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
                                        content: url("/imgs/chat_bubble.svg");
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
                    # current_chat_button = button
                    current_chat = chat
                    button.css_classes = ["selected"]
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
        new_chat_button.on_click(self.trigger_on_click_new_chat)

        objects = (
            [header, new_chat_button]
            + self.chat_buttons
            + [pn.layout.VSpacer(), pn.pane.HTML("version: 1.0"), self.footer()]
        )

        result = pn.Column(
            *objects,
            stylesheets=[
                """   
                        :host { 
                            background-color: white;
                            overflow-x: hidden;
                            height: 100%;
                            width:100%;
                            border-right: 1px solid #EEEEEE;
                        }
                """
            ],
        )

        # if current_chat_button is not None:
        #     current_chat_button.clicks = 1
        if current_chat is not None:
            self.on_click_chat(current_chat)
        elif len(chats) > 0:
            self.chat_buttons[0].clicks = 1
        elif len(chats) == 0:
            """I haven't found a better way to open the modal when the pages load,
            than simulating a click on the "New chat" button.
            - calling self.template.open_modal() doesn't work
            - calling self.on_click_new_chat doesn't work either
            - trying to schedule a call to on_click_new_chat with pn.state.schedule_task
                could have worked but my tests were yielding an unstable result.
            """
            new_chat_button_name = "New Chat"
            hack_open_modal = pn.pane.HTML(
                """
                            <script>   let buttons = $$$('button.bk-btn-primary');
                                        buttons.forEach(function(btn){
                                            if ( btn.innerText.trim() == '{new_chat_btn_name}' ){
                                                btn.click();
                                            }
                                        });
                            </script>
                            """.replace(
                    "{new_chat_btn_name}", new_chat_button_name
                ).strip(),
                stylesheets=[":host { position:absolute; z-index:-999; }"],
            )

            result.append(pn.pane.HTML(js.SHADOWROOT_INDEXING))
            result.append(hack_open_modal)

        return result
