import panel as pn
import param

import ragna.ui.js as js

import ragna.ui.styles as ui
from ragna.ui.central_view import CentralView

from ragna.ui.chat_config import ChatConfig
from ragna.ui.left_sidebar import LeftSidebar

from ragna.ui.modal import ModalConfiguration
from ragna.ui.right_sidebar import RightSidebar


class MainPage(param.Parameterized):
    current_chat_id = param.String(default=None)

    def __init__(self, api_wrapper):
        super().__init__()
        self.api_wrapper = api_wrapper

        self.central_view = None
        self.left_sidebar = None
        self.right_sidebar = None

    # Modal and callbacks
    def open_modal(self, template):
        self.modal = ModalConfiguration(
            chat_configs=[],  # self.chat_configs,
            start_button_callback=lambda event, template=template: self.on_click_start_conv_button(
                event, template
            ),
            cancel_button_callback=lambda event, template=template: self.on_click_cancel_button(
                event, template
            ),
        )
        template.modal.objects[0].objects = [self.modal]
        template.open_modal()

    def on_click_start_conv_button(self, event, template):
        print("on_click_start_conv_button")

    def on_click_cancel_button(self, event, template):
        print("on_click_cancel_button")
        template.close_modal()

    # Left sidebar callbacks
    def on_click_chat(self, chat):
        self.current_chat_id = chat["id"]
        self.central_view.set_current_chat(chat)

    # Right sidebar callbacks
    def show_right_sidebar(self, content):
        print("show_right_sidebar")
        # self.right_sidebar.visible = True

        # the right sidebar is basically just a column
        # self.right_sidebar.objects = [content]
        self.right_sidebar.show()

    def page(self):
        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

        # TODO : retrieve this from the API
        print(self.api_wrapper.get_components())
        self.chat_configs = [
            ChatConfig(
                # components=self.components,
                source_storage_names=["source", "source2"],
                llm_names=["gpt"],
                extra={"some config": "value", "other_config": 42},
            )
        ]

        template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="Ragna",
            # neutral_color="#FF0000", #ui.MAIN_COLOR,
            # header_background="#FF0000", #ui.MAIN_COLOR,
            # accent_base_color="#00FF00", #ui.MAIN_COLOR,
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
            lambda event, content: self.show_right_sidebar(content)
        )

        self.left_sidebar = LeftSidebar(api_wrapper=self.api_wrapper)
        self.left_sidebar.on_click_chat = lambda chat: self.on_click_chat(chat)
        self.left_sidebar.on_click_new_chat = (
            lambda event, template=template: self.open_modal(template)
        )

        self.right_sidebar = RightSidebar()

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
                        """
            ],
        )

        template.main.append(main_page)

        """I haven't found a better way to open the modal when the pages load,
        than simulating a click on the "New chat" button.
        - calling self.template.open_modal() doesn't work
        - calling self.on_click_new_chat doesn't work either
        - trying to schedule a call to on_click_new_chat with pn.state.schedule_task
            could have worked but my tests were yielding an unstable result.
        """
        new_chat_button_name = "New Chat"
        pn.pane.HTML(
            js.SHADOWROOT_INDEXING
            + """
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
        # template.header.append(hack_open_modal)
        template.header.append(pn.pane.HTML(js.CONNECTION_MONITOR))

        return template
