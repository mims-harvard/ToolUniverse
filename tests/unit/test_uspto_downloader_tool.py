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
