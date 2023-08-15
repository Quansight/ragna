from ora.extensions import DocMeta, hookimpl


class TxtDocMeta(DocMeta):
    pass


@hookimpl(specname="ora_doc_meta")
def txt_doc():
    return TxtDocMeta
