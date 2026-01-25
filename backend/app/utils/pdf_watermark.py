import io
from reportlab.pdfgen import canvas
from pypdf import PdfReader, PdfWriter


def create_watermark_layer(text: str, page_width: float, page_height: float):
    """
    Creates a single-page PDF watermark layer with diagonal text.
    """
    packet = io.BytesIO()
    c = canvas.Canvas(packet, pagesize=(page_width, page_height))

    # light watermark
    c.setFont("Helvetica", 20)
    c.setFillGray(0.7, 0.3)  # gray + alpha-like

    # rotate watermark
    c.saveState()
    c.translate(page_width / 2, page_height / 2)
    c.rotate(35)
    c.drawCentredString(0, 0, text)
    c.restoreState()

    c.save()
    packet.seek(0)
    return PdfReader(packet)


def watermark_pdf_bytes(original_pdf_path: str, watermark_text: str) -> bytes:
    """
    Reads original PDF file, overlays watermark text on each page, returns bytes.
    """
    reader = PdfReader(original_pdf_path)
    writer = PdfWriter()

    for page in reader.pages:
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)

        watermark_layer = create_watermark_layer(watermark_text, width, height)
        watermark_page = watermark_layer.pages[0]

        page.merge_page(watermark_page)
        writer.add_page(page)

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.read()
