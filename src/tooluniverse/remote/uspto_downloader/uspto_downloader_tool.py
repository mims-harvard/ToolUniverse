import requests
import pymupdf as fitz
import easyocr
from io import BytesIO
from docx import Document
from PIL import Image
from .uspto_tool import USPTOOpenDataPortalTool
from .tool_registry import register_tool


@register_tool("USPTOPatentDocumentDownloader")
class USPTOPatentDocumentDownloader(USPTOOpenDataPortalTool):
    """
    Fetch and download the abstract (ABST), claims (CLM), and full application text (APP.TEXT)
    PDFs for a given patent application number, following the one-time redirect flow.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config=tool_config)

    def run(self, arguments):
        def ocr_pdf_bytes(pdf_bytes, dpi=300):
            print("Running OCR on PDF bytes...")
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            pages_text = []

            # Initialize EasyOCR reader once
            reader = easyocr.Reader(["en"], gpu=True)

            for page in doc:
                # render the page to a PIL image at high resolution
                pix = page.get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                img_bytes = BytesIO()
                img.save(img_bytes, format="PNG")
                img_bytes.seek(0)
                results = reader.readtext(img_bytes.getvalue(), detail=0)
                text = "\n".join(results)
                pages_text.append(text.strip())

            doc.close()
            return "\n\n".join(pages_text)

        metadata = super().run(arguments)
        if isinstance(metadata, dict) and metadata.get("error"):
            return metadata

        desired = self.tool_config.get("document")

        docs = metadata.get("documentBag", [])
        if not docs:
            return {"error": "No documents found."}

        result = None
        all_doc_codes = set()
        for doc in docs:
            code = doc.get("documentCode")
            all_doc_codes.add(code)
            if code != desired:
                continue

            plain_text = ""
            pdf_opt = None
            word_opt = None
            for opt in doc.get("downloadOptionBag", []):
                m = opt.get("mimeTypeIdentifier", "").upper()
                if m == "PDF" and not pdf_opt:
                    pdf_opt = opt
                elif m == "MS_WORD" and not word_opt:
                    word_opt = opt

            if word_opt:
                url = word_opt["downloadUrl"]
                resp = requests.get(url, headers=self.headers, timeout=30)
                resp.raise_for_status()
                buf = BytesIO(resp.content)
                docx = Document(buf)
                plain_text = "\n\n".join(
                    p.text for p in docx.paragraphs if p.text.strip()
                )

            if not plain_text and pdf_opt:
                url = pdf_opt["downloadUrl"]
                resp = requests.get(url, headers=self.headers, timeout=30)
                resp.raise_for_status()
                pdf_bytes = resp.content
                pdf_doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                for page in pdf_doc:
                    plain_text += page.get_text().strip()
                pdf_doc.close()

                if plain_text == "":
                    # If no text was extracted, try to extract text from images
                    plain_text = ocr_pdf_bytes(pdf_bytes)

            if plain_text:
                # if plain text is longer than current result, it is probably a better text extraction
                if result is None or len(plain_text) > len(result):
                    result = plain_text

        if result is None:
            return {
                "error": f"Could not parse document with code {desired}. The documents available for this patent are: {', '.join(all_doc_codes)}."
            }
        else:
            # Return the plain text extracted from the PDF
            return {"result": result}


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
