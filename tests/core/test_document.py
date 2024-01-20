import docx

from ragna.core import DocxDocumentHandler, LocalDocument


def get_docx_document(tmp_path, docx_text):
    document = docx.Document()
    document.add_heading(docx_text)
    document.add_paragraph(docx_text)
    path = tmp_path / "test_document.docx"
    document.save(path)
    return LocalDocument.from_path(path)


def test_docx(tmp_path):
    docx_text = "ragna is neat!"
    tmp_docx_document = get_docx_document(tmp_path, docx_text)
    assert isinstance(tmp_docx_document.handler, DocxDocumentHandler)
    pages = list(tmp_docx_document.extract_pages())
    assert len(pages) == 2
    for page in pages:
        assert page.text == docx_text
