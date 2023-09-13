from pathlib import Path

import panel as pn

from helpers import JS_HACK_SHADOWROOT


def upload_demo():
    template = pn.template.FastListTemplate(
        title="Demo upload",
        theme_toggle=False,
        collapsed_sidebar=True,
    )

    page = pn.Column(
        pn.pane.HTML(
            JS_HACK_SHADOWROOT
            + """
                    <script type="text/javascript" src="/resources/upload.js"></script>
                    <div>
                        <label>Select file to upload</label>
                            <input type="file" id="fileUpload" multiple="multiple"> 
                    </div>
                    <button onclick="upload()">Upload</button>

                     """
        )
    )

    template.main.append(page)

    return template


if __name__ == "__main__":
    pn.serve(
        {"/": upload_demo},
        titles={"/": "Upload Demo"},
        port=8080,
        start=True,
        show=False,
        autoreload=True,
        allow_websocket_origin=["*"],
        static_dirs={"resources": Path(Path(__file__).parent.resolve() / "resources")},
    )
