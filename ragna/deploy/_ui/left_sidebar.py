from datetime import datetime

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
                button.css_classes = ["chat_button"]

        # ... and select the one that was clicked
        event.obj.css_classes = ["chat_button", "selected"]

        # call the actual callback
        if self.on_click_chat is not None:
            self.on_click_chat(chat)

    def footer(self):
        return pn.pane.HTML(
            """<div class='user_block'> Username </div>
                            """,
            css_classes=["left_sidebar_footer"],
        )

    def refresh(self):
        self.refresh_counter += 1

    @pn.depends("refresh_counter", "chats", "current_chat_id", on_init=True)
    def __panel__(self):
        epoch = datetime(1970, 1, 1)
        self.chats.sort(
            key=lambda chat: (
                epoch if not chat["messages"] else chat["messages"][-1]["timestamp"]
            ),
            reverse=True,
        )

        self.chat_buttons = []
        for chat in self.chats:
            button = pn.widgets.Button(
                name=chat["metadata"]["name"],
                css_classes=["chat_button"],
            )
            button.on_click(lambda event, c=chat: self.on_click_chat_wrapper(event, c))

            self.chat_buttons.append(button)

            try:
                if chat["id"] == self.current_chat_id:
                    button.css_classes.append("selected")
            except Exception:
                pass

        header = pn.pane.HTML(
            """<img src="imgs/ragna_logo.svg" height="32px" /><span>Ragna</span>""",
            css_classes=["left_sidebar_header"],
        )

        new_chat_button = pn.widgets.Button(
            name="New Chat",
            button_type="primary",
            icon="plus",
            css_classes=["new_chat_button"],
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
            css_classes=["left_sidebar_main_column"],
        )

        return result
