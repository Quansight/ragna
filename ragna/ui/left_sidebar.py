import panel as pn


class LeftSidebar(pn.viewable.Viewer):
    def __init__(self, api_wrapper, **params):
        super().__init__(**params)

        self.api_wrapper = api_wrapper
        self.on_click_chat = None

    def __panel__(self):
        chats = self.api_wrapper.get_chats()

        objects = [pn.pane.Markdown("# left_sidebar")]

        for chat in chats:
            button = pn.widgets.Button(name=chat["metadata"]["name"])
            if self.on_click_chat is not None:
                button.on_click(lambda event, c=chat: self.on_click_chat(c))
            objects.append(button)

        if len(chats) > 0:
            self.on_click_chat(chats[0])

        result = pn.Column(
            *objects,
            stylesheets=[
                """   
                                        :host { 
                                           /* background-color: #64BAFF; */

                                            height: 100%;
                                            width: 260px;
                                        }
                                """
            ],
        )

        return result
