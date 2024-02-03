"""
UI Helpers
"""
from typing import Any, Iterable, Optional, Type, Union

import panel as pn


def divider():
    return pn.layout.Divider(styles={"padding": "0em 1em"})


def apply_design_modifiers():
    apply_design_modifiers_global()
    apply_design_modifiers_source_accordion()
    apply_design_modifiers_auth_page()
    apply_design_modifiers_central_view()
    apply_design_modifiers_chat_info()
    apply_design_modifiers_chat_interface()


def add_modifier(
    modifier_class: Type[Any], modifications: Any, property: str = "stylesheets"
):
    if modifier_class not in pn.theme.fast.Fast.modifiers:
        pn.theme.fast.Fast.modifiers[modifier_class] = {}

    if property not in pn.theme.fast.Fast.modifiers[modifier_class]:
        pn.theme.fast.Fast.modifiers[modifier_class] = {property: [modifications]}
    else:
        pn.theme.fast.Fast.modifiers[modifier_class][property].append(modifications)


def apply_design_modifiers_global():
    add_modifier(
        pn.widgets.TextInput,
        """ .bk-input {border-color: var(--neutral-color) !important;} """,
    )
    add_modifier(
        pn.widgets.Select,
        """ .bk-input {border-color: var(--neutral-color) !important;} """,
    )

    add_modifier(pn.widgets.Button, "css/global/button.css")


def apply_design_modifiers_source_accordion():
    add_modifier(
        pn.layout.Accordion, " :host(.source-accordion) { height: 100%; width: 100%; } "
    )
    add_modifier(pn.layout.Card, "css/source_accordion/card.css")
    add_modifier(pn.pane.HTML, "css/source_accordion/html.css")
    add_modifier(pn.pane.Markdown, "css/source_accordion/markdown.css")


def apply_design_modifiers_chat_info():
    add_modifier(pn.pane.Markdown, "css/chat_info/markdown.css")
    add_modifier(pn.widgets.Button, "css/chat_info/button.css")


def apply_design_modifiers_auth_page():
    add_modifier(pn.widgets.TextInput, "css/auth/textinput.css")
    add_modifier(pn.pane.HTML, "css/auth/html.css")
    add_modifier(pn.widgets.Button, "css/auth/button.css")
    add_modifier(pn.Column, "css/auth/column.css")


def apply_design_modifiers_central_view():
    add_modifier(pn.Column, "css/central_view/column.css")
    add_modifier(pn.Row, "css/central_view/row.css")
    add_modifier(pn.pane.HTML, "css/central_view/html.css")


def apply_design_modifiers_chat_interface():
    add_modifier(pn.widgets.TextInput, "css/chat_interface/textinput.css")
    add_modifier(pn.layout.Card, "css/chat_interface/card.css")


"""
CSS constants
"""


def stylesheets(
    *class_selectors: tuple[Union[str, Iterable[str]], dict[str, str]]
) -> Optional[list[str]]:
    if not class_selectors:
        return None

    return [
        "\n".join(
            [
                f"{selector if isinstance(selector, str) else ', '.join(selector)} {{",
                *[
                    f"    {property}: {value};"
                    for property, value in declarations.items()
                ],
                "}",
            ]
        )
        for selector, declarations in class_selectors
    ]


MAIN_COLOR = "#DF5538"  # "rgba(223, 85, 56, 1)"


# MAIN_COLOR_LIGHT = "#10BBE580"
# MAIN_COLOR_LIGHTER = "#E1E8E3"
# TABS_SIDEBAR_BKGROUND_COLOR = "#EAEAEA"
# TABS_SIDEBAR_WIDTH = "20em"

# set modal height
CONFIG_MODAL_MIN_HEIGHT = 610
CONFIG_MODAL_MAX_HEIGHT = 850
CONFIG_MODAL_WIDTH = 800

WELCOME_MODAL_HEIGHT = 275
WELCOME_MODAL_WIDTH = 530


APP_RAW = """

:root {
    --body-font: 'Inter', sans-serif !important;
    --accent-color: {{MAIN_COLOR}} !important;
}

* {
    font-family: 'Inter', sans-serif;
}

.main {
    padding: 0px !important;

}

.pn-wrapper {
    padding: 0px;
}

div.card-margin {
    margin: 0px !important;
    height: 100% !important;
}


/* Hide the whole header */

#header {
    display: none;
}


div#content {
    height: calc(100vh);
}

/* Fix the size of the modal */
#pn-Modal {
    --dialog-width: 800px !important;
    --dialog-height:500px !important; 
}

/* Hide the default close button of the modal */
.pn-modal-close {
    display: none !important;
}


/* Hide the fullscreen button of the template */ 
span.fullscreen-button {
    display:none;
}

""".replace("{{MAIN_COLOR}}", MAIN_COLOR)


SS_LABEL_STYLE = """
:host {
    margin-top:20px;
}

label, .bk-slider-title {
    font-weight: bold;
    margin-bottom: 5px;
}

.bk-slider-value {
    font-weight: normal;
}

.noUi-target {
    border-color: var(--accent-fill-active);
}

.noUi-handle {
    border-radius: 50%;
}

.noUi-handle, .noUi-connects {
    background-color: var(--clear-button-active);
}

.noUi-target[disabled='true'] {
    border-color: darkgray;
}


.noUi-target[disabled='true'] .noUi-connect {
    background-color: darkgray !important;
}


:host(.disabled) div.bk-slider-title {
    color: darkgray !important;
}


"""


SS_ADVANCED_UI_CARD = """
:host {
    border : none !important;
    outline: none !important;
    background-color: unset !important;
}
"""


message_loading_indicator = f""" 
            <div style="height:48px;">
                <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24">
                    <circle cx="18" cy="12" r="0" fill="{MAIN_COLOR}">
                        <animate attributeName="r" begin=".67" calcMode="spline" dur="1.5s" keySplines="0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8" repeatCount="indefinite" values="0;2;0;0"/>
                    </circle>
                    <circle cx="12" cy="12" r="0" fill="{MAIN_COLOR}">
                        <animate attributeName="r" begin=".33" calcMode="spline" dur="1.5s" keySplines="0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8" repeatCount="indefinite" values="0;2;0;0"/>
                    </circle>
                    <circle cx="6" cy="12" r="0" fill="{MAIN_COLOR}">
                        <animate attributeName="r" begin="0" calcMode="spline" dur="1.5s" keySplines="0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8;0.2 0.2 0.4 0.8" repeatCount="indefinite" values="0;2;0;0"/>
                    </circle>
                </svg>
            </div>
            """
