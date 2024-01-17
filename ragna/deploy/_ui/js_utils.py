def preformat(text):
    """ allow {{key}} to be used for formatting in text
    that already uses curly braces.  First switch this into
    something else, replace curlies with double curlies, and then
    switch back to regular braces
    """
    text = text.replace('{{', '<<<').replace('}}', '>>>')
    text = text.replace('{', '{{').replace('}', '}}')
    text = text.replace('<<<', '{').replace('>>>', '}')
    return text


def redirect_script(remove, append='/', remove_auth_cookie=False):
    js_script = preformat("""
        <script>
            var currentPath = window.location.pathname; // Get the current path
            if (currentPath.includes('/{{remove}}')) {
              console.log("Removing {{remove}} from " + currentPath)
              if ("{{remove}}") {
                currentPath = currentPath.replace(/\/{{remove}}(\/)?$/, '')
              }
              var redirectTo = currentPath + '{{append}}';
              console.log("Redirecting to " + redirectTo)
              window.location.href = redirectTo;
              if ({{remove_auth_cookie}}) {
                console.log("Removing auth_token cookie")
                document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${redirectTo}";
              }
            }
        </script>
        """)

    return js_script.format(
        remove=remove,
        append=append,
        remove_auth_cookie=str(remove_auth_cookie).lower()
    )
