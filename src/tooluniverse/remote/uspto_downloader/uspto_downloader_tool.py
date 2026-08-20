import requests
import pymupdf as fitz
import easyocr
import re
import zipfile
from io import BytesIO
from docx import Document
from PIL import Image
from urllib.parse import urljoin, urlparse
from tooluniverse.uspto_tool import USPTOOpenDataPortalTool
from tooluniverse.tool_registry import register_tool


_APPLICATION_NUMBER_PATTERN = re.compile(r"^[0-9]{8,16}$")
_MAX_DOWNLOAD_BYTES = 50_000_000
_MAX_DOCUMENT_CHARS = 1_000_000
_MAX_DOCX_MEMBERS = 10_000
_MAX_DOCX_UNCOMPRESSED_BYTES = 100_000_000
_MAX_PDF_PAGES = 2_000
_MAX_OCR_PAGES = 100
_MAX_OCR_PIXELS_PER_PAGE = 25_000_000
_MAX_OCR_TOTAL_PIXELS = 250_000_000


def _validate_uspto_download_url(url):
    if not isinstance(url, str):
        raise ValueError("USPTO returned an invalid document URL.")
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or parsed.username is not None
        or parsed.password is not None
        or not (hostname == "uspto.gov" or hostname.endswith(".uspto.gov"))
    ):
        raise ValueError("USPTO returned an unapproved document URL.")
    return url


def _download_uspto_document(url, headers):
    """Download one bounded document, validating an optional single redirect."""
    current_url = _validate_uspto_download_url(url)
    response = None
    try:
        for redirect_count in range(2):
            response = requests.get(
                current_url,
                headers=headers,
                timeout=30,
                stream=True,
                allow_redirects=False,
            )
            if response.status_code in (301, 302, 303, 307, 308):
                if redirect_count:
                    raise ValueError("USPTO document redirected more than once.")
                location = response.headers.get("Location")
                response.close()
                response = None
                current_url = _validate_uspto_download_url(
                    urljoin(current_url, location or "")
                )
                continue
            response.raise_for_status()
            length = response.headers.get("Content-Length")
            if length is not None and int(length) > _MAX_DOWNLOAD_BYTES:
                raise ValueError("USPTO document exceeds the provider download limit.")
            content = bytearray()
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                content.extend(chunk)
                if len(content) > _MAX_DOWNLOAD_BYTES:
                    raise ValueError(
                        "USPTO document exceeds the provider download limit."
                    )
            return bytes(content)
        raise ValueError("USPTO document redirect could not be resolved.")
    finally:
        if response is not None:
            response.close()


def _validate_docx_archive(document_bytes):
    """Reject oversized or malformed DOCX archives before XML decompression."""
    try:
        with zipfile.ZipFile(BytesIO(document_bytes)) as archive:
            members = archive.infolist()
            if len(members) > _MAX_DOCX_MEMBERS:
                raise ValueError("USPTO Word document contains too many archive members.")
            if sum(member.file_size for member in members) > _MAX_DOCX_UNCOMPRESSED_BYTES:
                raise ValueError("USPTO Word document exceeds the expansion limit.")
            if any(member.flag_bits & 0x1 for member in members):
                raise ValueError("USPTO Word document must not be encrypted.")
    except zipfile.BadZipFile:
        raise ValueError("USPTO returned an invalid Word document.") from None


def _bounded_join_text(values):
    """Join extracted text while retaining at most one character past the cap."""
    parts = []
    length = 0
    truncated = False
    for value in values:
        if not isinstance(value, str):
            continue
        value = value.strip()
        if not value:
            continue
        piece = ("\n\n" if parts else "") + value
        remaining = _MAX_DOCUMENT_CHARS + 1 - length
        if remaining <= 0:
            truncated = True
            break
        if len(piece) > remaining:
            piece = piece[:remaining]
            truncated = True
        parts.append(piece)
        length += len(piece)
        if length > _MAX_DOCUMENT_CHARS:
            truncated = True
            break
    return "".join(parts), truncated


@register_tool("USPTOPatentDocumentDownloader")
class USPTOPatentDocumentDownloader(USPTOOpenDataPortalTool):
    """
    Fetch and download the abstract (ABST), claims (CLM), and full application text (APP.TEXT)
    PDFs for a given patent application number, following the one-time redirect flow.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config=tool_config)

    def run(self, arguments):
        if not isinstance(arguments, dict):
            return {"error": "Arguments must be an object."}
        application_number = arguments.get("applicationNumberText")
        if (
            not isinstance(application_number, str)
            or not _APPLICATION_NUMBER_PATTERN.fullmatch(application_number.strip())
        ):
            return {"error": "applicationNumberText must contain 8 to 16 digits."}
        try:
            result = self._run_provider(
                {"applicationNumberText": application_number.strip()}
            )
        except (requests.RequestException, ValueError):
            return {"error": "USPTO document retrieval failed on the provider."}
        except Exception:
            return {
                "error": "USPTO document retrieval failed due to an internal provider error."
            }

        text = result.get("result") if isinstance(result, dict) else None
        if isinstance(text, str):
            provider_truncated = bool(result.pop("_truncated", False))
            result["result"] = text[:_MAX_DOCUMENT_CHARS]
            result["document_chars"] = len(result["result"])
            result["truncated"] = provider_truncated or len(text) > _MAX_DOCUMENT_CHARS
        return result

    def _run_provider(self, arguments):
        def ocr_pdf_bytes(pdf_bytes, dpi=300):
            print("Running OCR on PDF bytes...")
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            try:
                if doc.page_count > _MAX_PDF_PAGES:
                    raise ValueError("USPTO PDF exceeds the page limit.")
                if doc.page_count > _MAX_OCR_PAGES:
                    raise ValueError("USPTO image-only PDF exceeds the OCR page limit.")

                reader = easyocr.Reader(["en"], gpu=False)
                pages_text = []
                total_pixels = 0
                for page in doc:
                    pix = page.get_pixmap(dpi=dpi, alpha=False)
                    pixels = pix.width * pix.height
                    total_pixels += pixels
                    if (
                        pixels > _MAX_OCR_PIXELS_PER_PAGE
                        or total_pixels > _MAX_OCR_TOTAL_PIXELS
                    ):
                        raise ValueError("USPTO PDF exceeds the OCR image limit.")
                    img = Image.frombytes(
                        "RGB", [pix.width, pix.height], pix.samples
                    )
                    img_bytes = BytesIO()
                    img.save(img_bytes, format="PNG")
                    results = reader.readtext(img_bytes.getvalue(), detail=0)
                    pages_text.append("\n".join(results))
                return _bounded_join_text(pages_text)
            finally:
                doc.close()

        metadata = super().run(arguments)
        if isinstance(metadata, dict) and metadata.get("error"):
            return {"error": "USPTO metadata request failed."}
        if isinstance(metadata, dict) and metadata.get("status") == "error":
            data = metadata.get("data")
            error = data.get("error") if isinstance(data, dict) else None
            hint = data.get("hint") if isinstance(data, dict) else None
            result = {"error": error or "USPTO metadata request failed."}
            if isinstance(hint, str):
                result["hint"] = hint
            return result
        if not isinstance(metadata, dict):
            return {"error": "USPTO metadata response was invalid."}
        metadata = metadata.get("data", metadata)

        desired = self.tool_config.get("document")

        docs = metadata.get("documentBag", [])
        if not docs:
            return {"error": "No documents found."}

        result = None
        for doc in docs:
            code = doc.get("documentCode")
            if code != desired:
                continue

            plain_text = ""
            extraction_truncated = False
            pdf_opt = None
            word_opt = None
            for opt in doc.get("downloadOptionBag", []):
                m = opt.get("mimeTypeIdentifier", "").upper()
                if m == "PDF" and not pdf_opt:
                    pdf_opt = opt
                elif m == "MS_WORD" and not word_opt:
                    word_opt = opt

            if word_opt:
                document_bytes = _download_uspto_document(
                    word_opt.get("downloadUrl"), self.headers
                )
                _validate_docx_archive(document_bytes)
                buf = BytesIO(document_bytes)
                docx = Document(buf)
                plain_text, extraction_truncated = _bounded_join_text(
                    p.text for p in docx.paragraphs
                )

            if not plain_text and pdf_opt:
                pdf_bytes = _download_uspto_document(
                    pdf_opt.get("downloadUrl"), self.headers
                )
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                try:
                    if pdf_doc.page_count > _MAX_PDF_PAGES:
                        raise ValueError("USPTO PDF exceeds the page limit.")
                    plain_text, extraction_truncated = _bounded_join_text(
                        page.get_text() for page in pdf_doc
                    )
                finally:
                    pdf_doc.close()

                if plain_text == "":
                    # If no text was extracted, try to extract text from images
                    plain_text, extraction_truncated = ocr_pdf_bytes(pdf_bytes)

            if plain_text:
                # if plain text is longer than current result, it is probably a better text extraction
                if result is None or len(plain_text) > len(result):
                    result = plain_text
                    result_truncated = extraction_truncated

        if result is None:
            return {"error": f"Could not parse the requested {desired} document."}
        else:
            # Return the plain text extracted from the PDF
            return {"result": result, "_truncated": result_truncated}


# if __name__ == "__main__":
#     # Example usage
#     tool_config = {
#         "name": "uspto_patent_document_downloader",
#         "description": "Download patent documents and extract text.",
#         "document": "ABST",  # Specify the document type to download
#     }
#     downloader = USPTOPatentDocumentDownloader(tool_config)
#     arguments = {"applicationNumberText": "19053071"}  # Example application number
#     result = downloader.run(arguments)
#     print(result)
