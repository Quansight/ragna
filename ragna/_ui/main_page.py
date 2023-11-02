import asyncio

import panel as pn
import param

from . import js
from .central_view import CentralView
from .left_sidebar import LeftSidebar
from .modal_configuration import ModalConfiguration
from .modal_welcome import ModalWelcome
from .right_sidebar import RightSidebar


class MainPage(pn.viewable.Viewer, param.Parameterized):
    current_chat_id = param.String(default=None)
    chats = param.List(default=None)

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
        self.left_sidebar.on_click_chat = self.on_click_chat
        self.left_sidebar.on_click_new_chat = lambda event: self.open_modal()

        self.right_sidebar = RightSidebar()

        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

    async def refresh_data(self):
        self.chats = await self.api_wrapper.get_chats()

    @param.depends("chats", watch=True)
    def after_update_chats(self):
        self.left_sidebar.chats = self.chats

        if len(self.chats) > 0:
            chat_id_exist = (
                len([c["id"] for c in self.chats if c["id"] == self.current_chat_id])
                > 0
            )

            if self.current_chat_id is None or not chat_id_exist:
                self.current_chat_id = self.chats[0]["id"]

            for c in self.chats:
                if c["id"] == self.current_chat_id:
                    self.central_view.set_current_chat(c)
                    break

    # Modal and callbacks
    def open_modal(self):
        self.modal = ModalConfiguration(
            api_wrapper=self.api_wrapper,
            new_chat_ready_callback=self.open_new_chat,
            cancel_button_callback=self.on_click_cancel_button,
        )

        self.template.modal.objects[0].objects = [self.modal]
        self.template.open_modal()

    def open_welcome_modal(self, event):
        self.modal = ModalWelcome(
            close_button_callback=lambda: self.template.close_modal(),
        )

        self.template.modal.objects[0].objects = [self.modal]
        self.template.open_modal()

    async def open_new_chat(self, new_chat_id):
        # called after creating a new chat.
        self.current_chat_id = new_chat_id
        await self.refresh_data()

        self.template.close_modal()

    def on_click_cancel_button(self, event):
        self.template.close_modal()

    # Left sidebar callbacks
    def on_click_chat(self, chat):
        self.central_view.set_loading(True)
        self.current_chat_id = chat["id"]
        self.central_view.set_current_chat(chat)
        self.central_view.set_loading(False)

    # Right sidebar callbacks
    def show_right_sidebar(self, title, content):
        self.right_sidebar.title = title
        self.right_sidebar.content = content
        self.right_sidebar.param.trigger("content")
        self.right_sidebar.show()

    @param.depends("current_chat_id", watch=True)
    def update_subviews_current_chat_id(self, avoid_senders=[]):
        if self.left_sidebar is not None and self.left_sidebar not in avoid_senders:
            self.left_sidebar.current_chat_id = self.current_chat_id

    def __panel__(self):
        asyncio.ensure_future(self.refresh_data())

        objects = [self.left_sidebar, self.central_view, self.right_sidebar]

        if self.chats is not None and len(self.chats) == 0:
            """I haven't found a better way to open the modal when the pages load,
            than simulating a click on the "New chat" button.
            - calling self.template.open_modal() doesn't work
            - calling self.on_click_new_chat doesn't work either
            - trying to schedule a call to on_click_new_chat with pn.state.schedule_task
                could have worked but my tests were yielding an unstable result.
            """

            new_chat_button_name = "open welcome modal"
            open_welcome_modal = pn.widgets.Button(
                name=new_chat_button_name,
                button_type="primary",
            )
            open_welcome_modal.on_click(self.open_welcome_modal)

            hack_open_modal = pn.pane.HTML(
                """
                            <script>   let buttons = $$$('button.bk-btn-primary');
                            console.log(buttons);
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

            objects.append(
                pn.Row(
                    open_welcome_modal,
                    pn.pane.HTML(js.SHADOWROOT_INDEXING),
                    hack_open_modal,
                    visible=False,
                )
            )

        main_page = pn.Row(
            *objects,
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
