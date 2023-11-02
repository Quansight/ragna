"""
UI Helpers
"""
import panel as pn


def divider():
    return pn.layout.Divider(styles={"padding": "0em 1em"})


"""
CSS constants
"""

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


CHAT_INTERFACE_CUSTOM_BUTTON = """
:host(.solid) .bk-btn.bk-btn-default {
    background-color: transparent;
    color: gray;
}

:host {
    transform: translate(14px, -56px); 
}

.bk-btn {
    border-radius: 0;
    padding: 0;
    font-size: 14px;
}
    """

BK_INPUT_GRAY_BORDER = (
    """ .bk-input {border-color: var(--neutral-color) !important;} """
)


SS_MULTI_SELECT_STYLE = """
option:hover, option:checked, option:focus {
    color:white !important;
}
"""

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
