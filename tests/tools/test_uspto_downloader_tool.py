"""Tests for the separately deployed USPTO patent document MCP service."""

import os
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
import requests

from tooluniverse.remote.uspto_downloader import uspto_downloader_tool as module
from tooluniverse.uspto_tool import USPTOOpenDataPortalTool


def _downloader(document="ABST"):
    downloader = object.__new__(module.USPTOPatentDocumentDownloader)
    downloader.tool_config = {"document": document}
    downloader.headers = {"X-API-KEY": "test-key"}
    downloader.session = Mock()
    downloader._ocr_reader = None
    return downloader


def _metadata(*documents):
    return {
        "status": "success",
        "data": {"documentBag": list(documents)},
    }


def _document(code, *download_options):
    return {
        "documentCode": code,
        "downloadOptionBag": list(download_options),
    }


def _download_option(mime_type, url="https://example.test/document"):
    return {"mimeTypeIdentifier": mime_type, "downloadUrl": url}


def test_module_import_does_not_require_gpu_server_dependencies():
    assert module.USPTOPatentDocumentDownloader.__name__ == (
        "USPTOPatentDocumentDownloader"
    )


def test_missing_server_dependency_has_install_instructions(monkeypatch):
    def missing_dependency(_name):
        raise ModuleNotFoundError("missing")

    monkeypatch.setattr(module.importlib, "import_module", missing_dependency)

    with pytest.raises(RuntimeError, match="uspto_downloader/requirements.txt"):
        module._import_server_dependency("easyocr", "EasyOCR")


def test_extracts_nonempty_docx_paragraphs(monkeypatch):
    fake_document = SimpleNamespace(
        paragraphs=[
            SimpleNamespace(text="First paragraph"),
            SimpleNamespace(text="  "),
            SimpleNamespace(text="Second paragraph"),
        ]
    )
    fake_docx = SimpleNamespace(Document=Mock(return_value=fake_document))
    monkeypatch.setattr(module, "_import_server_dependency", lambda *_: fake_docx)

    result = module.USPTOPatentDocumentDownloader._extract_docx_text(b"docx")

    assert result == "First paragraph\n\nSecond paragraph"


def test_extracts_searchable_pdf_text_and_closes_document(monkeypatch):
    class FakePdf(list):
        pass

    fake_pdf = FakePdf(
        [
            SimpleNamespace(get_text=Mock(return_value="Page one ")),
            SimpleNamespace(get_text=Mock(return_value="  ")),
            SimpleNamespace(get_text=Mock(return_value="Page three")),
        ]
    )
    fake_pdf.close = Mock()
    fake_fitz = SimpleNamespace(open=Mock(return_value=fake_pdf))
    monkeypatch.setattr(module, "_import_server_dependency", lambda *_: fake_fitz)

    result = module.USPTOPatentDocumentDownloader._extract_pdf_text(b"pdf")

    assert result == "Page one\n\nPage three"
    fake_pdf.close.assert_called_once_with()


def test_ocr_uses_gpu_reader_once_and_closes_documents(monkeypatch):
    class FakeImage:
        def save(self, buffer, format):
            assert format == "PNG"
            buffer.write(b"png")

    class FakePage:
        def get_pixmap(self, dpi):
            assert dpi == 300
            return SimpleNamespace(width=2, height=1, samples=b"pixels")

    class FakePdf(list):
        def __init__(self):
            super().__init__([FakePage()])
            self.close = Mock()

    reader = SimpleNamespace(readtext=Mock(return_value=["line one", "line two"]))
    fake_easyocr = SimpleNamespace(Reader=Mock(return_value=reader))
    fake_image_module = SimpleNamespace(frombytes=Mock(return_value=FakeImage()))
    documents = [FakePdf(), FakePdf()]
    fake_fitz = SimpleNamespace(open=Mock(side_effect=documents))

    dependencies = {
        "pymupdf": fake_fitz,
        "easyocr": fake_easyocr,
        "PIL.Image": fake_image_module,
    }
    monkeypatch.setattr(
        module,
        "_import_server_dependency",
        lambda name, _distribution: dependencies[name],
    )
    downloader = _downloader()

    assert downloader._ocr_pdf_bytes(b"first") == "line one\nline two"
    assert downloader._ocr_pdf_bytes(b"second") == "line one\nline two"
    fake_easyocr.Reader.assert_called_once_with(["en"], gpu=True)
    assert all(document.close.call_count == 1 for document in documents)


def test_run_unwraps_metadata_and_extracts_word_document():
    downloader = _downloader()
    response = SimpleNamespace(content=b"docx", raise_for_status=Mock())
    downloader.session.get.return_value = response
    downloader._extract_docx_text = Mock(return_value="Patent abstract")

    with patch.object(
        USPTOOpenDataPortalTool,
        "run",
        return_value=_metadata(_document("ABST", _download_option("MS_WORD"))),
    ):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert result == {"result": "Patent abstract"}
    downloader.session.get.assert_called_once_with(
        "https://example.test/document",
        headers={"X-API-KEY": "test-key"},
        timeout=120,
    )


def test_run_uses_ocr_only_when_pdf_has_no_text():
    downloader = _downloader("CLM")
    response = SimpleNamespace(content=b"pdf", raise_for_status=Mock())
    downloader.session.get.return_value = response
    downloader._extract_pdf_text = Mock(return_value="")
    downloader._ocr_pdf_bytes = Mock(return_value="OCR claims")

    with patch.object(
        USPTOOpenDataPortalTool,
        "run",
        return_value=_metadata(_document("CLM", _download_option("PDF"))),
    ):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert result == {"result": "OCR claims"}
    downloader._ocr_pdf_bytes.assert_called_once_with(b"pdf")


def test_run_falls_back_to_pdf_when_word_processing_fails():
    downloader = _downloader()
    word_response = SimpleNamespace(content=b"docx", raise_for_status=Mock())
    pdf_response = SimpleNamespace(content=b"pdf", raise_for_status=Mock())
    downloader.session.get.side_effect = [word_response, pdf_response]
    downloader._extract_docx_text = Mock(side_effect=ValueError("bad Word file"))
    downloader._extract_pdf_text = Mock(return_value="PDF abstract")

    with patch.object(
        USPTOOpenDataPortalTool,
        "run",
        return_value=_metadata(
            _document(
                "ABST",
                _download_option("MS_WORD", "https://example.test/document.docx"),
                _download_option("PDF", "https://example.test/document.pdf"),
            )
        ),
    ):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert result == {"result": "PDF abstract"}
    assert downloader.session.get.call_count == 2


def test_run_propagates_structured_metadata_errors():
    downloader = _downloader()
    response = {
        "status": "error",
        "data": {"error": "HTTP Error: 403", "hint": "Check USPTO_API_KEY"},
    }

    with patch.object(USPTOOpenDataPortalTool, "run", return_value=response):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert result == response["data"]


def test_run_reports_available_document_codes_deterministically():
    downloader = _downloader("ABST")

    with patch.object(
        USPTOOpenDataPortalTool,
        "run",
        return_value=_metadata(
            _document("ZZZ"),
            _document(None),
            _document("AAA"),
        ),
    ):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert result == {
        "error": "Could not parse document with code ABST. "
        "The documents available for this patent are: AAA, ZZZ."
    }


def test_run_returns_download_errors_instead_of_crashing():
    downloader = _downloader()
    downloader.session.get.side_effect = requests.ConnectionError("offline")

    with patch.object(
        USPTOOpenDataPortalTool,
        "run",
        return_value=_metadata(_document("ABST", _download_option("PDF"))),
    ):
        result = downloader.run({"applicationNumberText": "19053071"})

    assert "offline" in result["error"]


def test_server_exposes_the_document_tools_with_the_public_schema():
    repository_root = Path(__file__).resolve().parents[2]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repository_root / "src")
    env["USPTO_API_KEY"] = "test-key"

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            'exec("""import asyncio\n'
            "from fastmcp import Client\n"
            "from tooluniverse.remote.uspto_downloader "
            "import uspto_downloader_mcp_server as server_module\n"
            "async def main():\n"
            "    async with Client(server_module.server) as client:\n"
            "        tools = await client.list_tools()\n"
            "        schemas = {tool.name: tool.inputSchema for tool in tools}\n"
            "        expected = {\n"
            "            'get_abstract_from_patent_app_number',\n"
            "            'get_claims_from_patent_app_number',\n"
            "            'get_full_text_from_patent_app_number',\n"
            "        }\n"
            "        assert set(schemas) == expected\n"
            "        for schema in schemas.values():\n"
            "            assert schema['required'] == ['applicationNumberText']\n"
            "            assert schema['properties']['applicationNumberText']"
            "['type'] == 'string'\n"
            'asyncio.run(main())\n""")',
        ],
        cwd=repository_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert result.returncode == 0, result.stderr
