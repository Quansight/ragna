from pathlib import Path

import panel as pn
import param

import ragna.ui.styles as ui
from ragna.ui.api_wrapper import ApiWrapper
from ragna.ui.central_view import CentralView
from ragna.ui.left_sidebar import LeftSidebar

pn.extension(
    loading_spinner="dots",
    loading_color=ui.MAIN_COLOR,
    layout_compatibility="error",
)
pn.config.browser_info = True


HERE = Path(__file__).parent
# CSS = HERE / "css"
IMGS = HERE / "imgs"


class RagnaUI(param.Parameterized):
    current_chat_id = param.String(default=None)

    def __init__(self, url="localhost", port=5007, api_url="localhost:31476"):
        super().__init__()
        self.url = url
        self.port = port
        self.api_url = api_url
        self.api_wrapper = ApiWrapper(api_url=self.api_url, user="Ragna")

    def index_page(self):
        pn.state.location.sync(
            self,
            {"current_chat_id": "current_chat_id"},
            on_error=lambda x: print(f"error sync on {x}"),
        )

        template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="AI Toolbox",
            # neutral_color="#FF0000", #ui.MAIN_COLOR,
            # header_background="#FF0000", #ui.MAIN_COLOR,
            # accent_base_color="#00FF00", #ui.MAIN_COLOR,
            theme_toggle=False,
            collapsed_sidebar=True,
            # main_layout=None
            raw_css=[ui.APP_RAW],
        )

        left_sidebar = LeftSidebar(api_wrapper=self.api_wrapper)
        main_content = CentralView(api_wrapper=self.api_wrapper)

        def on_click_chat(chat):
            self.current_chat_id = chat["id"]
            main_content.set_current_chat(chat)

        left_sidebar.on_click_chat = on_click_chat

        right_sidebar = pn.Column(
            pn.pane.Markdown("# right_sidebar"),
            visible=False,
            stylesheets=[
                """   
                                :host { 
                                        /*background-color: lightgreen; */
                                        height:100%;
                                        width: 260px;
                                }
                          """
            ],
        )

        main_page = pn.Row(
            left_sidebar,
            main_content,
            right_sidebar,
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

        return template

    def health_page(self):
        return pn.pane.HTML("<h1>Ok</h1>")

    def serve(self):
        # logging.init(log_level=args.log_level)

        all_pages = {"/": self.index_page, "/health": self.health_page}
        titles = {"/": "Home"}

        pn.serve(
            all_pages,
            titles=titles,
            port=self.port,
            admin=True,
            start=True,
            location=True,
            show=False,
            keep_alive=30 * 1000,  # 30s
            autoreload=True,
            profiler="pyinstrument",
            allow_websocket_origin=[self.url, f"{self.url}:{self.port}"],
            static_dirs={"imgs": str(IMGS)},  # "css": str(CSS),
        )
