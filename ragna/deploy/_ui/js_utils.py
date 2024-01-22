import panel as pn


def preformat(text):
    """Allows {{key}} to be used for formatting in textcthat already uses
    curly braces.  First switch this into something else, replace curlies
    with double curlies, and then switch back to regular braces
    """
    text = text.replace("{{", "<<<").replace("}}", ">>>")
    text = text.replace("{", "{{").replace("}", "}}")
    text = text.replace("<<<", "{").replace(">>>", "}")
    return text


def redirect_script(remove, append="/", remove_auth_cookie=False):
    """
    This function returns a js script to redirect to correct url.
    :param remove: string to remove from the end of the url
    :param append: string to append at the end of the url
    :param remove_auth_cookie: boolean, will clear auth_token cookie when true.
    :return: string javascript script

    Examples:
    =========

    # This will remove nothing from the end of the url and will
    # add auth to it, so /foo/bar/car/ becomes /foo/bar/car/auth
    >>> redirect_script(remove="", append="auth")

    # This will remove nothing from the end of the url and will
    # add auth to it, so /foo/bar/car/ becomes /foo/bar/car/logout
    >>> redirect_script(remove="", append="logout")

    # This will remove "auth" from the end of the url and will add / to it
    # so /foo/bar/car/auth becomes /foo/bar/car/
    >>> redirect_script(remove="auth", append="/")
    """
    js_script = preformat(
        r"""
        <script>
            var currentPath = window.location.pathname; // Get the current path
            if (currentPath.includes('/{{remove}}')) {
              if ("{{remove}}") {
                currentPath = currentPath.replace(/\/{{remove}}(\/)?$/, '')
              }
              var redirectTo = currentPath + '{{append}}';
              window.location.href = redirectTo;
              if ({{remove_auth_cookie}}) {
                document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${redirectTo}";
              }
            }
        </script>
        """
    )

    return pn.pane.HTML(
        js_script.format(
            remove=remove,
            append=append,
            remove_auth_cookie=str(remove_auth_cookie).lower(),
        )
    )
