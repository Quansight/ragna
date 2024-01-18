import pytest

from ragna.core import DocxDocumentHandler, LocalDocument


@pytest.fixture()
def docx_text():
    return "Ragna is neat!"


@pytest.fixture()
def tmp_docx_document(tmp_path, docx_text):
    import docx

    document = docx.Document()
    document.add_heading(docx_text)
    document.add_paragraph(docx_text)
    path = tmp_path / "test_document.docx"
    document.save(path)
    return LocalDocument.from_path(path)


def test_docx(tmp_docx_document, docx_text):
    handler = DocxDocumentHandler()
    for page in handler.extract_pages(tmp_docx_document):
        assert page.text == docx_text
