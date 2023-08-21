"""
CSS constants
"""

MAIN_COLOR = "#10BBE5"
MAIN_COLOR_LIGHT = "#10BBE580"
MAIN_COLOR_LIGHTER = "#E1E8E3"
TABS_SIDEBAR_BKGROUND_COLOR = "#EAEAEA"
TABS_SIDEBAR_WIDTH = "20em"

# If you need to change the 500px below, update it in template_fixes.css as well
MODAL_MIN_HEIGHT = 500
MODAL_MAX_HEIGHT = 850


"""
CSS definitions for widgets
"""

HEADER_STYLESHEET = """
a, a.title {
    font-size: 15px;
    color: #DBD6B7;
    text-decoration: none;
}

a:hover, :host(.active) a {
    text-decoration: underline;
    text-underline-offset: 10px;
    text-decoration-thickness: 2px;
}

:host(.title) a {
    font-size: 24px;

}

:host(.link) {
    margin-left: 50px;
}
"""

APP_RAW = """
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

/* Hide the title in the header bar */
div.app-header a.title {
    display:none;
}

/* Hide the shadow below the header */
#header {
    box-shadow: none !important;
}
"""

CHAT_BOX_DIALOG_BUTTON = """
:host(.solid) .bk-btn.bk-btn-default {
    background-color: transparent;
    color: gray;
}

.bk-btn {
    border-radius: 0;
    padding: 0;
    font-size: 10px;
}
    """

CHAT_ANSWER = """
div > *:first-child {
    margin-top: 0;
}
div > *:last-child {
    margin-bottom: 0;
}

"""

DOC_NAMES = """
:host {
    border: 2px solid #E9E6D4;
    border-radius: 20px;
    background-color: white;
    padding: 3px 8px !important;
    margin: 0px 5px !important;
    width: fit-content;

}

div.docname {
    width: fit-content;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

"""


INFO_BUTTON = """
:host(.solid) .bk-btn.bk-btn-default {
    background-color: transparent;
    color: gray;
    padding: 10px;
}
"""

MODEL_RADIO_BOX = """
input[type='radio'] {
    --webkit-appearance: radio !important;
    appearance: revert !important;
    accent-color: {MAIN_COLOR};
    margin-left: 10px !important;
}

span {
    margin-right: 10px !important;
}
""".replace(
    "{MAIN_COLOR}", MAIN_COLOR
)

MULTI_SELECT_STYLE = """
option:hover, option:checked, option:focus {
    color:white !important;
}
"""

LABEL_STYLE = """
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

.noUi-handle {
    border-radius: 50%;
}

.noUi-handle, .noUi-connects {
    background-color: var(--clear-button-active);
}
"""

ADVANCED_UI_CARD = """
:host {
    border : none !important;
    background-color: unset !important;
}
"""

TABS = (
    """
:host {
    height: 100%;
}

.bk-header {
    width: {TABS_SIDEBAR_WIDTH};
    background-color: {TABS_SIDEBAR_BKGROUND_COLOR};
    padding-top: 70px !important;
}

.bk-tab {
    height: 50px;
    margin: 0px 10px !important;

    border-right: 0px !important;

    text-align: left;
    font-size: 16px;

    /* This is the trick to vertically align text in a div ... */
    flex-direction: column;
    justify-content: center;

    /* This is a trick to truncate the chat name */
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    display: block;

}

.bk-tab.bk-active {
    border-left: {MAIN_COLOR} 3px solid !important;
    background-color: #FFFFFF80 !important;
}

""".replace(
        "{MAIN_COLOR}", MAIN_COLOR
    )
    .replace("{TABS_SIDEBAR_BKGROUND_COLOR}", TABS_SIDEBAR_BKGROUND_COLOR)
    .replace("{TABS_SIDEBAR_WIDTH}", TABS_SIDEBAR_WIDTH)
)


NEW_CHAT_BUTTON = """
button.bk-btn {
    width: 230px;
    text-align: left;
    height: 45px;
    font-size: 16px;
}
:host {
    position: absolute;
    top: 10px;
    z-index: 99;
}
"""

CHAT_BUBBLES_COL = """
:host {
    bottom: 55px;
    max-height: 85%;
    border: none !important;

    width: 80%;
    margin: 70px 0px 0px 20%;
    padding: 0px 20% 0px 0px;
}
"""

SEND_BUTTON = """
:host {
    position: absolute;
    bottom: 0;

    width: 80%;
    margin: 0px 0% 0px 20%;
    padding: 0px 20% 0px 0px;
    }
"""

TEXT_INPUT = """
.bk-input {
    box-shadow:  1px  1px 2px 0px lightgray,
                -1px -1px 2px 0px lightgray,
                1px -1px 2px 0px lightgray,
                -1px  1px 2px 0px lightgray ;
    border: none;
}
"""

RIGHT_SIDEBAR_HIDDEN = """
:host {
    height: 100%;
    width:22%;
    overflow: hidden;
    background-color: white;
    border-left: 2px solid #EAEAEA;
}
"""
RIGHT_SIDEBAR_EXPANDED = """
:host {
    height: calc(100% - 5px);
    width: 100%;
}
"""

CLOSE_BUTTON = """
:host {
    position: absolute;
    top: 10px;
    right: 10px;
    z-index: 99;
}
"""

PAIGE_DASHBOARD = """
:host {
    background-color: rgb(248,247,241);
    height: 100%;
    width: 100%;
    flex: 1;
}
"""

VERSION_ID = """
:host {
    width: {TABS_SIDEBAR_WIDTH};
    background-color: {TABS_SIDEBAR_BKGROUND_COLOR};
    margin: 0px 0px 0px 0px;    /* top, right, bottom, left */
    padding: 0px 10px;          /* top/bottom, right/left */
    color: grey;
}
""".replace(
    "{TABS_SIDEBAR_BKGROUND_COLOR}", TABS_SIDEBAR_BKGROUND_COLOR
).replace(
    "{TABS_SIDEBAR_WIDTH}", TABS_SIDEBAR_WIDTH
)
