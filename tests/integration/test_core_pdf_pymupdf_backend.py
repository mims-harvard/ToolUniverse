"""Exercise the real opt-in PyMuPDF backend installed by the CI test step."""

import pytest

pymupdf = pytest.importorskip("pymupdf")

from tooluniverse.core_tool import CorePDFSnippetsTool


class _Response:
    status_code = 200
    url = "https://example.test/paper.pdf"
    headers = {"content-type": "application/pdf"}
    text = ""

    def __init__(self, content):
        self.content = content


def test_core_pdf_snippets_with_pymupdf(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})

    with pymupdf.open() as document:
        page = document.new_page()
        page.insert_text((72, 72), "This paper discusses epistasis in detail.")
        pdf_bytes = document.tobytes()

    def mock_request(session, method, url, **kwargs):
        return _Response(b"" if method == "HEAD" else pdf_bytes)

    monkeypatch.setattr("tooluniverse.core_tool.request_with_retry", mock_request)

    result = tool.run(
        {
            "pdf_url": "https://example.test/paper.pdf",
            "terms": ["epistasis"],
            "extractor": "fitz",
        }
    )

    assert result["status"] == "success"
    assert result["extractor_used"] == "fitz"
    assert result["pages_scanned"] == 1
    assert result["snippets_count"] == 1
