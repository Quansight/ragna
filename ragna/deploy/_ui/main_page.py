import asyncio

import panel as pn
import param

from .central_view import CentralView
from .left_sidebar import LeftSidebar
from .modal_configuration import ModalConfiguration
from .right_sidebar import RightSidebar


class MainPage(pn.viewable.Viewer, param.Parameterized):
    current_chat_id = param.String(default=None)
    chats = param.List(default=None)

    def __init__(self, engine, template):
        super().__init__()
        self._engine = engine
        self.template = template

        self.components = None
        self.corpus_metadata = None
        self.corpus_names = None

        self.modal = None
        self.central_view = CentralView(engine=self._engine)
        self.central_view.on_click_chat_info = (
            lambda event, title, content: self.show_right_sidebar(title, content)
        )

        self.left_sidebar = LeftSidebar(engine=self._engine)
        self.left_sidebar.on_click_chat = self.on_click_chat
        self.left_sidebar.on_click_new_chat = self.open_modal

        self.right_sidebar = RightSidebar()

        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

    async def refresh_data(self):
        self.chats = self._engine.get_chats(user=pn.state.user)
        self.components = self._engine.get_components()
        self.corpus_metadata = await self._engine.get_corpus_metadata()
        self.corpus_names = await self._engine.get_corpuses()

    @param.depends("chats", watch=True)
    def after_update_chats(self):
        self.left_sidebar.chats = self.chats

        if len(self.chats) > 0:
            chat_id_exist = any(c.id == self.current_chat_id for c in self.chats)

            if self.current_chat_id is None or not chat_id_exist:
                self.current_chat_id = str(self.chats[0].id)

            for c in self.chats:
                if str(c.id) == self.current_chat_id:
                    self.central_view.set_current_chat(c)
                    break

    async def open_modal(self, event):
        if (
            self.components is None
            or self.corpus_metadata is None
            or self.corpus_names is None
        ):
            await self.refresh_data()

        self.modal = ModalConfiguration(
            engine=self._engine,
            components=self.components,
            corpus_metadata=self.corpus_metadata,
            corpus_names=self.corpus_names,
            new_chat_ready_callback=self.open_new_chat,
            cancel_button_callback=self.on_click_cancel_button,
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
        self.current_chat_id = str(chat.id)
        self.central_view.set_current_chat(chat)
        self.central_view.set_loading(False)

    # Right sidebar callbacks
    def show_right_sidebar(self, title, content):
        self.right_sidebar.title = title
        self.right_sidebar.content = content
        self.right_sidebar.param.trigger("content")
        self.right_sidebar.show()

    @param.depends("current_chat_id", watch=True)
    def update_subviews_current_chat_id(self, avoid_senders=None):
        if avoid_senders is None:
            avoid_senders = []
        if self.left_sidebar is not None and self.left_sidebar not in avoid_senders:
            self.left_sidebar.current_chat_id = self.current_chat_id

    def __panel__(self):
        asyncio.ensure_future(self.refresh_data())

        return pn.Row(
            self.left_sidebar,
            self.central_view,
            self.right_sidebar,
            css_classes=["main_page_main_row"],
        )
