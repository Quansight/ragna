"""
CSS constants
"""

MAIN_COLOR = "#10BBE5"


# MAIN_COLOR_LIGHT = "#10BBE580"
# MAIN_COLOR_LIGHTER = "#E1E8E3"
# TABS_SIDEBAR_BKGROUND_COLOR = "#EAEAEA"
# TABS_SIDEBAR_WIDTH = "20em"

# set modal height (in x heights)
MODAL_MIN_HEIGHT = 70
MODAL_MAX_HEIGHT = 300
MODAL_WIDTH = 800


APP_RAW = """

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


"""
