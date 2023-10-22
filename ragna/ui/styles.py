"""
CSS constants
"""

MAIN_COLOR = "#DF5538"  # "rgba(223, 85, 56, 1)"


# MAIN_COLOR_LIGHT = "#10BBE580"
# MAIN_COLOR_LIGHTER = "#E1E8E3"
# TABS_SIDEBAR_BKGROUND_COLOR = "#EAEAEA"
# TABS_SIDEBAR_WIDTH = "20em"

# set modal height (in x heights)
MODAL_MAX_HEIGHT = 63

MODAL_WIDTH = 800

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

""".replace(
    "{{MAIN_COLOR}}", MAIN_COLOR
)


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
