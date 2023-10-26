from .styles import CONFIG_MODAL_MAX_HEIGHT, CONFIG_MODAL_MIN_HEIGHT


# Reset modal size
def reset_modal_size(width, height):
    return f"""
    document.getElementById("pn-Modal").style.setProperty("--dialog-height","{height}px", "important")
    document.getElementById("pn-Modal").style.setProperty("--dialog-width","{width}px", "important")
    """


JS_TOGGLE_CARD = f"""
let height = card.collapsed ? "{CONFIG_MODAL_MAX_HEIGHT}px" : "{CONFIG_MODAL_MIN_HEIGHT}px";
document.getElementById("pn-Modal").style.setProperty("--dialog-height",height, "important")
"""


# Allow selecting elements of the shadowroot with "$$$"
# https://discourse.holoviz.org/t/sync-scrollbars-for-wide-tabulators/5459
SHADOWROOT_INDEXING = """
<script type="text/javascript">
    function $$$(selector, rootNode=document.body) {
        const arr = []

        const traverser = node => {
            // 1. decline all nodes that are not elements
            if(node.nodeType !== Node.ELEMENT_NODE) {
                return
            }

            // 2. add the node to the array, if it matches the selector
            if(node.matches(selector)) {
                arr.push(node)
            }

            // 3. loop through the children
            const children = node.children
            if (children.length) {
                for(const child of children) {
                    traverser(child)
                }
            }

            // 4. check for shadow DOM, and loop through it's children
            const shadowRoot = node.shadowRoot
            if (shadowRoot) {
                const shadowChildren = shadowRoot.children
                for(const shadowChild of shadowChildren) {
                    traverser(shadowChild)
                }
            }
        }

        traverser(rootNode)
        return arr
    }
</script>
""".strip()


""" This is a fix to close the modal only when click *down* on it's outside area.
We have seen a bug where, if you start by clicking down somewhere inside and end click up
outside of it (like selectiong the ChatName text input with the mouse ),
it's considered as a click outside the modal so it needs to be closed.
"""
MODAL_MOUSE_UP_FIX = """
<script>
    window.onclick = null

    window.onmousedown = (event) => {
        if ( event.target == modal){
            modal.style.display = "none";
        }
    };
</script>
""".strip()

CONNECTION_MONITOR = """
<script>
    const originalSend = WebSocket.prototype.send;
    window.sockets = [];
    WebSocket.prototype.send = function(...args) {
        if (window.sockets.indexOf(this) === -1)
            window.sockets.push(this);
        return originalSend.call(this, ...args);
    };

    const polling = setInterval(function() {

        if ( window.sockets.length > 0 ){

            if ( window.sockets[0].readyState >= 2 ){

                let div = document.createElement('div');
                div.style.color = 'white';
                div.style.backgroundColor= 'crimson';
                div.style.padding = '10px 10px 10px 10px';
                div.style.textAlign= 'center';

                let text = document.createTextNode('Session has expired. Please reload.');
                div.appendChild(text);


                window.document.body.insertBefore(
                    div,
                    window.document.body.firstChild
                );

                clearInterval(polling);
            }
        }

    }, 5000);

</script>
"""
