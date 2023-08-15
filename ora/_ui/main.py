import panel as pn


class Page:
    def __init__(self, doc_db_names, llm_names):
        self._doc_db_names = doc_db_names
        self._llm_names = llm_names

    def __panel__(self):
        return pn.layout.Column(
            "Fake Modal",
            pn.widgets.Select(options=self._doc_db_names, name="_source_storage"),
            pn.widgets.Select(options=self._llm_names, name="llm_name"),
        )


def app(*, doc_dbs, llms, url, port):
    pn.serve(
        {"/": Page(doc_db_names=list(doc_dbs.keys()), llm_names=list(llms.keys()))},
        port=port,
        start=True,
        show=False,
        location=True,
        allow_websocket_origin=[url, f"{url}:{port}"],
    )
