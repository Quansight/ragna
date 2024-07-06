"""
UI Helpers
"""

from typing import Any, Dict, Iterable, Union

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
    "global": [
        pn.widgets.TextInput,
        pn.widgets.Select,
        pn.widgets.Button,
        pn.layout.Divider,
    ],
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
            css_filepath = f"css/{dir}/{cls.__name__.lower()}.css"
            add_modifier(cls, css_filepath)
            css_filepaths.append(css_filepath)

    return css_filepaths


def add_modifier(
    modifier_class: pn.viewable.Viewable,
    modifications: Dict[str, Any],
    property: str = "stylesheets",
):
    properties = pn.theme.fast.Fast.modifiers.setdefault(modifier_class, {})
    property_modifications = properties.setdefault(property, [])
    property_modifications.append(modifications)


"""
CSS helpers, constants and UI Helpers
"""


def divider():
    return pn.layout.Divider(css_classes=["default_divider"])


def css(selector: Union[str, Iterable[str]], declarations: dict[str, str]) -> str:
    return "\n".join(
        [
            f"{selector if isinstance(selector, str) else ', '.join(selector)} {{",
            *[f"    {property}: {value};" for property, value in declarations.items()],
            "}",
        ]
    )


MAIN_COLOR = "#DF5538"  # "rgba(223, 85, 56, 1)"

# set modal height
CONFIG_MODAL_MIN_HEIGHT = 610
CONFIG_MODAL_MAX_HEIGHT = 850
CONFIG_MODAL_WIDTH = 800


CSS_VARS = css(
    ":root",
    {
        "--body-font": "'Inter', sans-serif !important",
        "--accent-color": f"{MAIN_COLOR} !important",
    },
)


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
