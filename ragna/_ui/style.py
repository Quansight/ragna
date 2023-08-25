"""
CSS constants
"""

MAIN_COLOR = "#10BBE5"
MAIN_COLOR_LIGHT = "#10BBE580"
MAIN_COLOR_LIGHTER = "#E1E8E3"
TABS_SIDEBAR_BKGROUND_COLOR = "#EAEAEA"
TABS_SIDEBAR_WIDTH = "20em"

# set modal height (in x heights)
MODAL_MIN_HEIGHT = 70
MODAL_MAX_HEIGHT = 300


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

RAGNA_DASHBOARD = """
:host {
    background-color: rgb(248,247,241);
    height: 100%;
    width: 100%;
    flex: 1;
}
"""
