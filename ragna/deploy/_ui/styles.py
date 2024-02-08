"""
UI Helpers
"""
from typing import Any, Iterable, Optional, Type, Union

import panel as pn

"""
the structure of css_modifiers is as follows:
{
    "directory name under css/":[list of panel classes that will be modified],
    ...
}

Each CSS modifier file that needs to be loaded, is infered from the panel class name and the directory name.
For example, with value :
{ "foobar":[pn.widgets.TextInput] }
the css file that will be loaded is css/foobar/textinput.css

"""

css_modifiers = {
    "global": [pn.widgets.TextInput, pn.widgets.Select, pn.widgets.Button],
    "source_accordion": [
        pn.layout.Accordion,
        pn.layout.Card,
        pn.pane.HTML,
        pn.pane.Markdown,
    ],
    "chat_info": [pn.pane.Markdown, pn.widgets.Button],
    "auth": [pn.widgets.TextInput, pn.pane.HTML, pn.widgets.Button, pn.Column],
    "central_view": [pn.Column, pn.Row, pn.pane.HTML],
    "chat_interface": [
        pn.widgets.TextInput,
        pn.layout.Card,
        pn.pane.Markdown,
        pn.widgets.button.Button,
        pn.Column,
    ],
    "right_sidebar": [pn.widgets.Button, pn.Column, pn.pane.Markdown],
    "left_sidebar": [pn.widgets.Button, pn.pane.HTML, pn.Column],
    "main_page": [pn.Row],
    "modal_welcome": [pn.widgets.Button],
    "modal_configuration": [
        pn.widgets.IntSlider,
        pn.layout.Card,
        pn.Row,
        pn.widgets.Button,
    ],
}


def apply_design_modifiers():
    css_filepaths = []
    for dir, classes in css_modifiers.items():
        for cls in classes:
            css_filename = cls.__name__.lower().split(".")[-1] + ".css"
            add_modifier(cls, f"css/{dir}/{css_filename}")
            css_filepaths.append(f"css/{dir}/{css_filename}")

    return css_filepaths


def add_modifier(
    modifier_class: Type[Any], modifications: Any, property: str = "stylesheets"
):
    if modifier_class not in pn.theme.fast.Fast.modifiers:
        pn.theme.fast.Fast.modifiers[modifier_class] = {}

    if property not in pn.theme.fast.Fast.modifiers[modifier_class]:
        pn.theme.fast.Fast.modifiers[modifier_class][property] = [modifications]
    else:
        pn.theme.fast.Fast.modifiers[modifier_class][property].append(modifications)


"""
def apply_design_modifiers_source_accordion():
    add_modifier(pn.layout.Accordion, "css/source_accordion/accordion.css")
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
    add_modifier(pn.pane.Markdown, "css/chat_interface/markdown.css")
    add_modifier(pn.widgets.button.Button, "css/chat_interface/button.css")
    add_modifier(pn.Column, "css/chat_interface/column.css")


def apply_design_modifiers_right_sidebar():
    add_modifier(pn.widgets.Button, "css/right_sidebar/button.css")
    add_modifier(pn.Column, "css/right_sidebar/column.css")
    add_modifier(pn.pane.Markdown, "css/right_sidebar/markdown.css")


def apply_design_modifiers_left_sidebar():
    add_modifier(pn.widgets.Button, "css/left_sidebar/button.css")
    add_modifier(pn.Column, "css/left_sidebar/column.css")
    add_modifier(pn.pane.HTML, "css/left_sidebar/html.css")


def apply_design_modifiers_main_page():
    add_modifier(pn.Row, "css/main_page/row.css")


def apply_design_modifiers_modal_welcome():
    add_modifier(pn.widgets.Button, "css/modal_welcome/button.css")


def apply_design_modifiers_modal_configuration():
    add_modifier(pn.widgets.IntSlider, "css/modal_configuration/intslider.css")
    add_modifier(pn.layout.Card, "css/modal_configuration/card.css")
    add_modifier(pn.Row, "css/modal_configuration/row.css")
    add_modifier(pn.widgets.Button, "css/modal_configuration/button.css")
"""

"""
CSS constants
"""

MAIN_COLOR = "#DF5538"  # "rgba(223, 85, 56, 1)"

# set modal height
CONFIG_MODAL_MIN_HEIGHT = 610
CONFIG_MODAL_MAX_HEIGHT = 850
CONFIG_MODAL_WIDTH = 800

WELCOME_MODAL_HEIGHT = 275
WELCOME_MODAL_WIDTH = 530


CSS_VARS = """
:root {
    --body-font: 'Inter', sans-serif !important;
    --accent-color: {{MAIN_COLOR}} !important;
}
""".replace("{{MAIN_COLOR}}", MAIN_COLOR)


"""
CSS and UI Helpers
"""


def divider():
    return pn.layout.Divider(styles={"padding": "0em 1em"})


def css(
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
