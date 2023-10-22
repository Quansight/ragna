import panel as pn
import param

import ragna.ui.js as js

import ragna.ui.styles as ui
from ragna.ui.central_view import CentralView
from ragna.ui.left_sidebar import LeftSidebar
from ragna.ui.modal import ModalConfiguration
from ragna.ui.right_sidebar import RightSidebar


class MainPage(param.Parameterized):
    current_chat_id = param.String(default=None)

    def __init__(self, api_wrapper):
        super().__init__()
        self.api_wrapper = api_wrapper

        self.modal = None
        self.central_view = None
        self.left_sidebar = None
        self.right_sidebar = None

    # Modal and callbacks
    def open_modal(self, template):
        self.modal = ModalConfiguration(
            api_wrapper=self.api_wrapper,
            new_chat_ready_callback=lambda new_chat_id, template=template: self.open_new_chat(
                new_chat_id, template
            ),
            cancel_button_callback=lambda event, template=template: self.on_click_cancel_button(
                event, template
            ),
        )

        template.modal.objects[0].objects = [self.modal]
        template.open_modal()

    def open_new_chat(self, new_chat_id, template):
        # called after creating a new chat.
        self.current_chat_id = new_chat_id
        self.left_sidebar.refresh()

        template.close_modal()

    def on_click_cancel_button(self, event, template):
        template.close_modal()

    # Left sidebar callbacks
    def on_click_chat(self, chat):
        self.current_chat_id = chat["id"]
        self.central_view.set_current_chat(chat)

    # Right sidebar callbacks
    def show_right_sidebar(self, title, content):
        self.right_sidebar.title = title
        self.right_sidebar.content = content
        self.right_sidebar.param.trigger("content")
        self.right_sidebar.show()

    @param.depends("current_chat_id", watch=True)
    def update_subviews_current_chat_id(self):
        try:
            if self.left_sidebar is not None:
                self.left_sidebar.current_chat_id = self.current_chat_id
        except Exception:
            pass

    def page(self):
        template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="Ragna",
            # neutral_color="#FF0000", #ui.MAIN_COLOR,
            # header_background="#FF0000", #ui.MAIN_COLOR,
            accent_base_color=ui.MAIN_COLOR,
            theme_toggle=False,
            collapsed_sidebar=True,
            # main_layout=None
            raw_css=[ui.APP_RAW],
            css_files=["https://rsms.me/", "https://rsms.me/inter/inter.css"],
        )

        template.modal.objects = [
            pn.Column(
                min_height=600,
                sizing_mode="stretch_both",
            )
        ]

        self.central_view = CentralView(api_wrapper=self.api_wrapper)
        self.central_view.on_click_chat_info = (
            lambda event, title, content: self.show_right_sidebar(title, content)
        )

        self.left_sidebar = LeftSidebar(api_wrapper=self.api_wrapper)
        self.left_sidebar.on_click_chat = lambda chat: self.on_click_chat(chat)
        self.left_sidebar.on_click_new_chat = (
            lambda event, template=template: self.open_modal(template)
        )

        self.right_sidebar = RightSidebar()

        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

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

        template.main.append(main_page)

        template.header.append(pn.pane.HTML(js.SHADOWROOT_INDEXING))
        template.header.append(pn.pane.HTML(js.CONNECTION_MONITOR))

        return template
