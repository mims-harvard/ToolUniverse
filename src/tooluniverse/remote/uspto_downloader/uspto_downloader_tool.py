import importlib
from io import BytesIO

import requests

from tooluniverse.tool_registry import register_tool
from tooluniverse.uspto_tool import USPTOOpenDataPortalTool


def _import_server_dependency(module_name, distribution_name):
    """Import a dependency owned by the standalone USPTO MCP server."""
    try:
        return importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            f"The USPTO downloader server requires {distribution_name}. "
            "Install its server dependencies with "
            "`pip install -r "
            "src/tooluniverse/remote/uspto_downloader/requirements.txt`."
        ) from exc


@register_tool("USPTOPatentDocumentDownloader")
class USPTOPatentDocumentDownloader(USPTOOpenDataPortalTool):
    """
    Fetch and download the abstract (ABST), claims (CLM), and full application text (APP.TEXT)
    documents for a given patent application number.
    """

    MIN_PAGE_TEXT_CHARACTERS = 32

    def __init__(self, tool_config):
        super().__init__(tool_config=tool_config)
        self._ocr_reader = None

    @staticmethod
    def _extract_docx_text(document_bytes):
        docx = _import_server_dependency("docx", "python-docx")
        document = docx.Document(BytesIO(document_bytes))
        return "\n\n".join(
            paragraph.text
            for paragraph in document.paragraphs
            if paragraph.text.strip()
        )

    @staticmethod
    def _extract_pdf_pages(pdf_bytes):
        fitz = _import_server_dependency("pymupdf", "PyMuPDF")
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            return [page.get_text().strip() for page in document]
        finally:
            document.close()

    def _ocr_pdf_pages(self, pdf_bytes, page_indexes=None, dpi=300):
        fitz = _import_server_dependency("pymupdf", "PyMuPDF")
        easyocr = _import_server_dependency("easyocr", "EasyOCR")
        image_module = _import_server_dependency("PIL.Image", "Pillow")

        if self._ocr_reader is None:
            self._ocr_reader = easyocr.Reader(["en"], gpu=True)

        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        try:
            selected_pages = (
                set(range(len(document))) if page_indexes is None else set(page_indexes)
            )
            pages_text = {}
            for page_index, page in enumerate(document):
                if page_index not in selected_pages:
                    continue
                pixmap = page.get_pixmap(dpi=dpi)
                image = image_module.frombytes(
                    "RGB", [pixmap.width, pixmap.height], pixmap.samples
                )
                image_bytes = BytesIO()
                image.save(image_bytes, format="PNG")
                results = self._ocr_reader.readtext(image_bytes.getvalue(), detail=0)
                pages_text[page_index] = "\n".join(results).strip()
            return pages_text
        finally:
            document.close()

    def _ocr_pdf_bytes(self, pdf_bytes, dpi=300):
        pages = self._ocr_pdf_pages(pdf_bytes, dpi=dpi)
        return "\n\n".join(pages[index] for index in sorted(pages) if pages[index])

    def _extract_pdf_text(self, pdf_bytes):
        pages = self._extract_pdf_pages(pdf_bytes)
        pages_needing_ocr = [
            page_index
            for page_index, page_text in enumerate(pages)
            if len("".join(page_text.split())) < self.MIN_PAGE_TEXT_CHARACTERS
        ]

        if pages_needing_ocr:
            ocr_pages = self._ocr_pdf_pages(pdf_bytes, pages_needing_ocr)
            for page_index, ocr_text in ocr_pages.items():
                if len("".join(ocr_text.split())) > len(
                    "".join(pages[page_index].split())
                ):
                    pages[page_index] = ocr_text

        return "\n\n".join(page for page in pages if page)

    @staticmethod
    def _metadata_error(response):
        if not isinstance(response, dict):
            return {"error": "USPTO returned an invalid metadata response."}

        if response.get("error"):
            return response

        if response.get("status") == "error":
            data = response.get("data")
            if not isinstance(data, dict):
                return {"error": "USPTO metadata request failed."}
            return data

        return None

    def run(self, arguments):
        metadata_response = super().run(arguments)
        metadata_error = self._metadata_error(metadata_response)
        if metadata_error:
            return metadata_error

        metadata = metadata_response.get("data", metadata_response)
        if not isinstance(metadata, dict):
            return {"error": "USPTO returned invalid document metadata."}

        desired = self.tool_config.get("document")

        docs = metadata.get("documentBag", [])
        if not docs:
            return {"error": "No documents found."}

        result = None
        all_doc_codes = set()
        matching_document_errors = []
        for doc in docs:
            code = doc.get("documentCode")
            if code:
                all_doc_codes.add(str(code))
            if code != desired:
                continue

            plain_text = ""
            pdf_opt = None
            word_opt = None
            for opt in doc.get("downloadOptionBag") or []:
                m = str(opt.get("mimeTypeIdentifier") or "").upper()
                if m == "PDF" and not pdf_opt:
                    pdf_opt = opt
                elif m == "MS_WORD" and not word_opt:
                    word_opt = opt

            processing_errors = []
            if word_opt:
                try:
                    response = self.session.get(
                        word_opt["downloadUrl"],
                        headers=self.headers,
                        timeout=120,
                    )
                    response.raise_for_status()
                    plain_text = self._extract_docx_text(response.content)
                except (
                    requests.RequestException,
                    RuntimeError,
                    ValueError,
                    OSError,
                    KeyError,
                ) as exc:
                    processing_errors.append(f"MS_WORD: {exc}")

            if not plain_text and pdf_opt:
                try:
                    response = self.session.get(
                        pdf_opt["downloadUrl"],
                        headers=self.headers,
                        timeout=120,
                    )
                    response.raise_for_status()
                    pdf_bytes = response.content
                    plain_text = self._extract_pdf_text(pdf_bytes)
                except (
                    requests.RequestException,
                    RuntimeError,
                    ValueError,
                    OSError,
                    KeyError,
                ) as exc:
                    processing_errors.append(f"PDF: {exc}")

            if not word_opt and not pdf_opt:
                processing_errors.append("no supported MS_WORD or PDF download option")

            if not plain_text and not processing_errors:
                processing_errors.append("no text could be extracted")

            if not plain_text and processing_errors:
                document_identifier = doc.get("documentIdentifier") or "unknown"
                matching_document_errors.append(
                    f"document {document_identifier}: {'; '.join(processing_errors)}"
                )

            if plain_text:
                # if plain text is longer than current result, it is probably a better text extraction
                if result is None or len(plain_text) > len(result):
                    result = plain_text

        if result is None:
            if matching_document_errors:
                return {
                    "error": f"Failed to download or parse every USPTO document "
                    f"with code {desired}: {'; '.join(matching_document_errors)}"
                }
            available = ", ".join(sorted(all_doc_codes)) or "none"
            return {
                "error": f"Could not parse document with code {desired}. "
                f"The documents available for this patent are: {available}."
            }
        return {"result": result}
