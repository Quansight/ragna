import panel as pn
import param


class RightSidebar(pn.viewable.Viewer):
    title = param.String(default="")
    content = param.List(default=[])

    def __init__(self, **params):
        super().__init__(**params)

        self.main_column = None
        self.close_button = None

    def show(self):
        self.main_column.css_classes = ["right_sidebar_main_column", "visible_sidebar"]

    def hide(self, event):
        self.main_column.css_classes = ["right_sidebar_main_column", "hidden_sidebar"]

    @pn.depends("content")
    def content_layout(self):
        return pn.Column(*self.content, css_classes=["right_sidebar_content"])

    @pn.depends("title")
    def header(self):
        return pn.pane.Markdown(
            f"## {self.title}",
            css_classes=["right_sidebar_header"],
        )

    def __panel__(self):
        self.close_button = pn.widgets.Button(
            icon="x",
            button_type="light",
            css_classes=["right_sidebar_close_button"],
        )
        self.close_button.on_click(self.hide)

        self.main_column = pn.Column(
            self.close_button,
            self.header,
            self.content_layout,
            css_classes=["right_sidebar_main_column"],
        )

        return self.main_column
