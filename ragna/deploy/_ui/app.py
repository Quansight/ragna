from pathlib import Path

import panel as pn
import param
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ragna._utils import handle_localhost_origins
from ragna.deploy import Config

from . import js
from . import styles as ui
from .api_wrapper import ApiWrapper
from .main_page import MainPage

pn.extension(
    loading_spinner="dots",
    loading_color=ui.MAIN_COLOR,
    layout_compatibility="error",
)
pn.config.browser_info = True


class App(param.Parameterized):
    def __init__(self, *, hostname, port, api_url, origins, open_browser):
        super().__init__()

        # Apply the design modifiers to the panel components
        # It returns all the CSS files of the modifiers
        self.css_filepaths = ui.apply_design_modifiers()
        self.hostname = hostname
        self.port = port
        self.api_url = api_url
        self.origins = origins
        self.open_browser = open_browser

    def get_template(self):
        # A bit hacky, but works.
        # we need to preload the css files to avoid a flash of unstyled content, especially when switching between chats.
        # This is achieved by adding <link ref="preload" ...> tags in the head of the document.
        # But none of the panel templates allow to add custom link tags in the head.
        # the only way I found is to take advantage of the raw_css parameter, which allows to add custom css in the head.
        preload_css = "\n".join(
            [
                f"""<link rel="preload" href="{css_fp}" as="style" />"""
                for css_fp in self.css_filepaths
            ]
        )
        preload_css = f"""
                     </style>
                     {preload_css}
                     <style type="text/css">
                     """

        template = pn.template.FastListTemplate(
            # We need to set a title to have it appearing on the browser's tab
            # but it means we need to hide it from the header bar
            title="Ragna",
            accent_base_color=ui.MAIN_COLOR,
            theme_toggle=False,
            collapsed_sidebar=True,
            raw_css=[ui.CSS_VARS, preload_css],
            favicon="imgs/ragna_logo.svg",
            css_files=["https://rsms.me/inter/inter.css", "css/main.css"],
        )

        template.modal.objects = [
            pn.Column(
                sizing_mode="stretch_both",
            )
        ]

        template.header.append(pn.pane.HTML(js.SHADOWROOT_INDEXING))
        template.header.append(pn.pane.HTML(js.MODAL_MOUSE_UP_FIX))
        template.header.append(pn.pane.HTML(js.CONNECTION_MONITOR))

        return template

    def index_page(self):
        api_wrapper = ApiWrapper(api_url=self.api_url)

        template = self.get_template()
        main_page = MainPage(api_wrapper=api_wrapper, template=template)
        template.main.append(main_page)
        return template

    def health_page(self):
        return pn.pane.HTML("<h1>Ok</h1>")

    def add_panel_app(self, server, panel_app_fn):
        # FIXME: this code will ultimately be distributed as part of panel
        from functools import partial

        import panel as pn
        from bokeh.application import Application
        from bokeh.application.handlers.function import FunctionHandler
        from bokeh_fastapi import BokehFastAPI
        from bokeh_fastapi.handler import WSHandler
        from panel.io.document import extra_socket_handlers
        from panel.io.state import set_curdoc

        def dispatch_fastapi(conn, events=None, msg=None):
            if msg is None:
                msg = conn.protocol.create("PATCH-DOC", events)
            return [conn._socket.send_message(msg)]

        extra_socket_handlers[WSHandler] = dispatch_fastapi

        def panel_app(doc):
            doc.on_event("document_ready", partial(pn.state._schedule_on_load, doc))

            with set_curdoc(doc):
                panel_app = panel_app_fn()
                panel_app.server_doc(doc)

        handler = FunctionHandler(panel_app)
        application = Application(handler)

        BokehFastAPI(application, server=server)

    def make_app(self):
        app = FastAPI()
        self.add_panel_app(app, self.index_page)

        for dir in ["css", "imgs", "resources"]:
            app.mount(
                f"/{dir}",
                StaticFiles(directory=str(Path(__file__).parent / dir)),
                name=dir,
            )

        return app

    def serve(self):
        import uvicorn

        uvicorn.run(self.make_app, factory=True, host=self.hostname, port=self.port)


def app(*, config: Config, open_browser: bool) -> App:
    return App(
        hostname=config.ui.hostname,
        port=config.ui.port,
        api_url=config.api.url,
        origins=handle_localhost_origins(config.ui.origins),
        open_browser=open_browser,
    )
