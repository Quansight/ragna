import panel as pn
import param

from ragna.ui.central_view import CentralView
from ragna.ui.left_sidebar import LeftSidebar
from ragna.ui.modal import ModalConfiguration
from ragna.ui.right_sidebar import RightSidebar


class MainPage(param.Parameterized):
    current_chat_id = param.String(default=None)

    def __init__(self, api_wrapper, template):
        super().__init__()
        self.api_wrapper = api_wrapper
        self.template = template

        self.modal = None
        self.central_view = CentralView(api_wrapper=self.api_wrapper)
        self.central_view.on_click_chat_info = (
            lambda event, title, content: self.show_right_sidebar(title, content)
        )

        self.left_sidebar = LeftSidebar(api_wrapper=self.api_wrapper)
        self.left_sidebar.on_click_chat = lambda chat: self.on_click_chat(chat)
        self.left_sidebar.on_click_new_chat = lambda event: self.open_modal()

        self.right_sidebar = RightSidebar()

        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

        self.refresh_data()

    def refresh_data(self):
        chats = self.api_wrapper.get_chats()
        self.left_sidebar.chats = chats

        if self.current_chat_id is None:
            self.current_chat_id = chats[0]["id"]

        for c in chats:
            if c["id"] == self.current_chat_id:
                self.central_view.set_current_chat(c)
                break

    # Modal and callbacks
    def open_modal(self):
        self.modal = ModalConfiguration(
            api_wrapper=self.api_wrapper,
            new_chat_ready_callback=lambda new_chat_id: self.open_new_chat(new_chat_id),
            cancel_button_callback=lambda event: self.on_click_cancel_button(event),
        )

        self.template.modal.objects[0].objects = [self.modal]
        self.template.open_modal()

    def open_new_chat(self, new_chat_id):
        # called after creating a new chat.
        self.current_chat_id = new_chat_id
        self.refresh_data()

        self.template.close_modal()

    def on_click_cancel_button(self, event):
        self.template.close_modal()

    # Left sidebar callbacks
    def on_click_chat(self, chat):
        print("set current chat id", chat["id"])
        self.current_chat_id = chat["id"]
        self.central_view.set_current_chat(chat)

    # Right sidebar callbacks
    def show_right_sidebar(self, title, content):
        self.right_sidebar.title = title
        self.right_sidebar.content = content
        self.right_sidebar.param.trigger("content")
        self.right_sidebar.show()

    @param.depends("current_chat_id", watch=True)
    def update_subviews_current_chat_id(self, avoid_senders=[]):
        try:
            if self.left_sidebar is not None and self.left_sidebar not in avoid_senders:
                self.left_sidebar.current_chat_id = self.current_chat_id
        except Exception:
            pass

    def page(self):
        main_page = pn.Row(
            self.left_sidebar,
            self.central_view,
            self.right_sidebar,
            stylesheets=[
                """   
                                :host { 
                                    background-color: rgb(248, 248, 248);
                                    height: 100%;
                                    width: 100%;
                                }

                                /* Enforces the width of the LeftSidebarn 
                                which is the "first of type" with this class 
                                (first object in the row) */
                                .bk-panel-models-layout-Column:first-of-type {
                                    min-width: 220px;
                                    width: 15%;     
                                }
                        """
            ],
        )

        return main_page
