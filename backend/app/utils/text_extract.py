import os
import fitz  # pymupdf


def extract_text_from_pdf(pdf_path: str, max_pages: int = 5) -> str:
    """
    Extract limited text from first few pages (fast & cheap for AI).
    """
    if not os.path.exists(pdf_path):
        return ""

    doc = fitz.open(pdf_path)
    text = []

    pages = min(len(doc), max_pages)
    for i in range(pages):
        page = doc[i]
        page_text = page.get_text("text").strip()
        if page_text:
            text.append(page_text)

    doc.close()

    return "\n\n".join(text)[:8000]  # keep safe size
