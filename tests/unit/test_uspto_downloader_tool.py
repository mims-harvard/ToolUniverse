"""Regression tests for issue #521: USPTOPatentDocumentDownloader imported
easyocr and python-docx unconditionally at module scope, but neither is a
declared dependency (root or MCPB). In an environment resolved from the
declared dependencies alone — this test environment included — both imports
failed, so importing this module raised ModuleNotFoundError instead of the
tool merely failing (with a clear message) the first time OCR or MS_WORD
extraction was actually needed.

PyMuPDF was already handled this way (a soft import backed by
``_pdf_backend()``); this fix applies the same pattern to EasyOCR and
python-docx.
"""

from unittest.mock import patch

import pytest

from tooluniverse.remote.uspto_downloader import uspto_downloader_tool as mod
from tooluniverse.remote.uspto_downloader.uspto_downloader_tool import (
    USPTOPatentDocumentDownloader,
    _docx_backend,
    _MissingDocxDependencyError,
    _MissingOcrDependencyError,
    _MissingPdfDependencyError,
    _MissingProviderDependencyError,
    _ocr_reader,
    _pdf_backend,
)


def test_module_imports_without_optional_dependencies():
    """None of pymupdf/easyocr/docx are installed in this environment; the
    module must still import (this is the regression the issue reports)."""
    assert mod.fitz is None
    assert mod.easyocr is None
    assert mod.Document is None


@pytest.mark.parametrize(
    "backend_fn,attr,exc_type",
    [
        (_pdf_backend, "fitz", _MissingPdfDependencyError),
        (_ocr_reader, "easyocr", _MissingOcrDependencyError),
        (_docx_backend, "Document", _MissingDocxDependencyError),
    ],
)
def test_backend_raises_friendly_error_when_missing(backend_fn, attr, exc_type):
    with patch.object(mod, attr, None), pytest.raises(exc_type) as exc_info:
        backend_fn()
    assert isinstance(exc_info.value, _MissingProviderDependencyError)
    assert "pip install tooluniverse[" in str(exc_info.value)


@pytest.fixture(autouse=True)
def _uspto_api_key(monkeypatch):
    monkeypatch.setenv("USPTO_API_KEY", "test-key")


def _tool():
    return USPTOPatentDocumentDownloader(
        {"name": "uspto_patent_document_downloader", "document": "ABST"}
    )


def _metadata(download_option_bag):
    return {
        "data": {
            "documentBag": [
                {
                    "documentCode": "ABST",
                    "documentIdentifier": "doc-1",
                    "downloadOptionBag": download_option_bag,
                }
            ]
        }
    }


def test_run_reports_missing_pdf_dependency_without_crashing():
    """A PDF-only document, with no PyMuPDF installed, must return a clear
    error from run() — not raise ModuleNotFoundError out of the tool."""
    tool = _tool()
    metadata = _metadata(
        [{"mimeTypeIdentifier": "PDF", "downloadUrl": "https://uspto.gov/x.pdf"}]
    )
    with (
        patch.object(mod.USPTOOpenDataPortalTool, "run", return_value=metadata),
        patch.object(mod, "_download_uspto_document", return_value=b"%PDF-1.4 fake"),
    ):
        result = tool.run({"applicationNumberText": "19053071"})

    assert result["error"] == "USPTO document extraction dependency is not installed."
    assert "PyMuPDF" in result["hint"]
    assert "pip install tooluniverse[pdf]" in result["hint"]


def test_run_reports_missing_docx_dependency_without_crashing():
    """An MS_WORD-only document, with no python-docx installed, must return a
    clear error from run() — not raise ModuleNotFoundError out of the tool."""
    tool = _tool()
    metadata = _metadata(
        [{"mimeTypeIdentifier": "MS_WORD", "downloadUrl": "https://uspto.gov/x.docx"}]
    )
    with (
        patch.object(mod.USPTOOpenDataPortalTool, "run", return_value=metadata),
        patch.object(mod, "_download_uspto_document", return_value=b"fake docx bytes"),
        patch.object(mod, "_validate_docx_archive", return_value=None),
    ):
        result = tool.run({"applicationNumberText": "19053071"})

    assert result["error"] == "USPTO document extraction dependency is not installed."
    assert "python-docx" in result["hint"]
    assert "pip install tooluniverse[ocr]" in result["hint"]


class _FakePixmap:
    def __init__(self, width=2, height=2):
        self.width = width
        self.height = height
        self.samples = bytes([255, 255, 255] * (width * height))


class _FakePage:
    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text

    def get_pixmap(self, dpi=300, alpha=False):
        return _FakePixmap()


class _FakePdfDoc:
    def __init__(self, pages):
        self._pages = pages
        self.page_count = len(pages)

    def __iter__(self):
        return iter(self._pages)

    def close(self):
        pass


class _FakeFitz:
    def __init__(self, pages):
        self._pages = pages

    def open(self, stream, filetype):
        return _FakePdfDoc(self._pages)


class _FakeOcrReader:
    def __init__(self, calls):
        self._calls = calls

    def readtext(self, image_bytes, detail=0):
        self._calls.append(image_bytes)
        return ["OCR RESULT"]


class _FakeEasyocr:
    def __init__(self, calls):
        self._calls = calls

    def Reader(self, langs, gpu=False):
        return _FakeOcrReader(self._calls)


def _pdf_metadata():
    return _metadata(
        [{"mimeTypeIdentifier": "PDF", "downloadUrl": "https://uspto.gov/x.pdf"}]
    )


def test_run_ocrs_only_pdf_pages_without_embedded_text():
    """A page with no embedded text (e.g. a scanned page mixed into an
    otherwise text-based PDF) is OCR'd; pages with real text are not."""
    tool = _tool()
    pages = [_FakePage("Real embedded text"), _FakePage("   "), _FakePage("More text")]
    ocr_calls = []

    with (
        patch.object(mod.USPTOOpenDataPortalTool, "run", return_value=_pdf_metadata()),
        patch.object(mod, "_download_uspto_document", return_value=b"%PDF-1.4 fake"),
        patch.object(mod, "_pdf_backend", return_value=_FakeFitz(pages)),
        patch.object(mod, "_ocr_reader", return_value=_FakeEasyocr(ocr_calls)),
    ):
        result = tool.run({"applicationNumberText": "19053071"})

    assert "Real embedded text" in result["result"]
    assert "More text" in result["result"]
    assert "OCR RESULT" in result["result"]
    assert len(ocr_calls) == 1


def test_run_does_not_ocr_a_text_heavy_document_that_needs_no_ocr():
    """A large document made entirely of text pages must not be blocked by
    the OCR page-count budget, since no page actually needs OCR."""
    tool = _tool()
    pages = [_FakePage(f"page {i} text") for i in range(mod._MAX_OCR_PAGES + 50)]
    ocr_calls = []

    with (
        patch.object(mod.USPTOOpenDataPortalTool, "run", return_value=_pdf_metadata()),
        patch.object(mod, "_download_uspto_document", return_value=b"%PDF-1.4 fake"),
        patch.object(mod, "_pdf_backend", return_value=_FakeFitz(pages)),
        patch.object(mod, "_ocr_reader", return_value=_FakeEasyocr(ocr_calls)),
    ):
        result = tool.run({"applicationNumberText": "19053071"})

    assert "error" not in result
    assert ocr_calls == []


def test_run_still_enforces_ocr_page_limit_when_pages_actually_need_ocr():
    """The OCR budget still applies, counted over pages that lack embedded
    text (not the document's total page count)."""
    tool = _tool()
    pages = [_FakePage("") for _ in range(mod._MAX_OCR_PAGES + 1)]
    ocr_calls = []

    with (
        patch.object(mod.USPTOOpenDataPortalTool, "run", return_value=_pdf_metadata()),
        patch.object(mod, "_download_uspto_document", return_value=b"%PDF-1.4 fake"),
        patch.object(mod, "_pdf_backend", return_value=_FakeFitz(pages)),
        patch.object(mod, "_ocr_reader", return_value=_FakeEasyocr(ocr_calls)),
    ):
        result = tool.run({"applicationNumberText": "19053071"})

    assert result["error"] == "USPTO document retrieval failed on the provider."
