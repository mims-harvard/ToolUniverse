"""Default CORE PDF extraction must not require the opt-in PyMuPDF backend."""

from tooluniverse.core_tool import CorePDFSnippetsTool


class _Response:
    status_code = 200
    url = "https://example.test/paper.pdf"
    headers = {"content-type": "application/pdf"}
    content = b"%PDF-1.4 default-backend-test"
    text = ""


class _MarkItDownResult:
    text_content = "This paper discusses epistasis in detail."


class _MarkItDown:
    def convert(self, path):
        return _MarkItDownResult()


def test_auto_extractor_works_without_pymupdf(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})
    tool.md_converter = _MarkItDown()

    monkeypatch.setattr("tooluniverse.core_tool.FITZ_AVAILABLE", False)
    monkeypatch.setattr("tooluniverse.core_tool.PYPDF_AVAILABLE", False)
    monkeypatch.setattr("tooluniverse.core_tool.MARKITDOWN_AVAILABLE", True)
    monkeypatch.setattr(
        "tooluniverse.core_tool.request_with_retry",
        lambda *args, **kwargs: _Response(),
    )

    result = tool.run(
        {
            "pdf_url": "https://example.test/paper.pdf",
            "terms": ["epistasis"],
            "extractor": "auto",
        }
    )

    assert result["status"] == "success"
    assert result["extractor_used"] == "markitdown"
    assert result["snippets_count"] == 1


def test_explicit_pymupdf_request_explains_opt_in_and_license(monkeypatch):
    tool = CorePDFSnippetsTool({"name": "CORE_get_fulltext_snippets"})
    monkeypatch.setattr("tooluniverse.core_tool.FITZ_AVAILABLE", False)

    result = tool.run(
        {
            "pdf_url": "https://example.test/paper.pdf",
            "terms": ["epistasis"],
            "extractor": "fitz",
        }
    )

    assert result["status"] == "error"
    assert "tooluniverse[pdf]" in result["error"]
    assert "AGPL-3.0" in result["error"]
