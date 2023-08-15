from ora.extensions import DocumentMetadata, hookimpl


class TxtDocumentMetadata(DocumentMetadata):
    pass


@hookimpl(specname="ora_document_metadata")
def txt_document_metadata():
    return TxtDocumentMetadata
