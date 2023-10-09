import panel as pn
import param


class RightSidebar(pn.viewable.Viewer):
    content = param.List(default=[])

    def _create_view(self):
        return self.__panel__()

    def __init__(self, **params):
        super().__init__(**params)

        self.main_column = None
        self.close_button = None

    def show(self):
        print("show")
        self.main_column.css_classes = ["visible_sidebar"]
        # self.close_button.visible = True

    def hide(self, event):
        self.main_column.css_classes = ["hidden_sidebar"]
        # self.close_button.visible = False

    @pn.depends("content")
    def __panel__(self):
        self.close_button = pn.widgets.Button(
            icon="x",
            button_type="light",
            css_classes=["close_button"],
            stylesheets=[
                """ 
                        :host {
                            position: absolute;
                            top: 6px;
                            right: 10px;
                            z-index: 99;
                        }
                        """
            ],
        )
        self.close_button.on_click(self.hide)

        self.main_column = pn.Column(
            self.close_button,
            *self.content,
            pn.pane.Markdown(
                "## Source Info",
                stylesheets=[
                    """ :host { 
                                                                    background-color: rgb(238, 238, 238);
                                                                    margin:0;
                                                                    padding-left:15px !important;
                                                                    width:100%;
                                                           } """
                ],
            ),
            stylesheets=[
                """   
                                :host { 
                                        /*background-color: lightgreen !important; */
                                        height:100%;
                                        min-width: unset;
                                        width: 0px;
                                        overflow:hidden;

                                        margin-left: min(15px, 2%);
                                        border-left: 1px solid #EEEEEE;
                                }

                                :host .close_button {
                                    transform: translateX(20px);

                                }



                                :host(.visible_sidebar) {
                                        animation: 0.25s ease-in forwards show_right_sidebar;
                                }

                                @keyframes show_right_sidebar {
                                    from {
                                        min-width: unset;
                                        width: 0px;
                                    }

                                    to {
                                        min-width: 200px;
                                        width: 25%;
                                    }
                                }

                                
                                :host(.visible_sidebar) .close_button {
                                    animation: 0.25s ease-in forwards show_close_button;
                                }

                                @keyframes show_close_button {
                                    from {
                                        transform: translateX(20px);
                                    }
                                    to {
                                        transform: translateX(0px);
                                    }
                                }

                                /* hide */

                                :host(.hidden_sidebar) {
                                        animation: 0.33s ease-in forwards hide_right_sidebar;
                                }

                                @keyframes hide_right_sidebar {
                                    from {
                                        min-width: 200px;
                                        width: 25%;
                                    }

                                    to {
                                        min-width: unset;
                                        width: 0px;
                                    }
                                }

                                :host(.hidden_sidebar) .close_button {
                                    animation: 0.33s ease-in forwards hide_close_button;
                                }

                                @keyframes hide_close_button {
                                    from {
                                        transform: translateX(0px);
                                    }
                                    to {
                                        transform: translateX(20px);
                                    }
                                }

                                


                                """
            ],
        )

        return self.main_column
