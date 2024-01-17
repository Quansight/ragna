from ragna.deploy._ui.js_utils import preformat, redirect_script
from textwrap import dedent


def test_preformat_basic():
    output = preformat("{ This is awesome {{var}} }").format(var="test")
    assert output == "{ This is awesome test }"


def test_preformat_multivars():
    output = preformat("{ {{var1}} This is awesome {{var2}} }").format(var1="test1", var2="test2")
    assert output == "{ test1 This is awesome test2 }"


def test_preformat_unsubs():
    output = preformat("{ This is {Hello} awesome {{var}} }").format(var="test")
    assert output == "{ This is {Hello} awesome test }"


def test_redirect_script():
    output = redirect_script(remove="foo", append="bar")
    expected = dedent(r"""
        <script>
            var currentPath = window.location.pathname; // Get the current path
            if (currentPath.includes('/foo')) {
              console.log("Removing foo from " + currentPath)
              if ("foo") {
                currentPath = currentPath.replace(/\/foo(\/)?$/, '')
              }
              var redirectTo = currentPath + 'bar';
              console.log("Redirecting to " + redirectTo)
              window.location.href = redirectTo;
              if (false) {
                console.log("Removing auth_token cookie")
                document.cookie = "auth_token=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=${redirectTo}";
              }
            }
        </script>
    """)
    assert dedent(output) == expected
