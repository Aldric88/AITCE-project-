import io
from PIL import Image, ImageDraw, ImageFont


def watermark_image_bytes(image_path: str, watermark_text: str) -> bytes:
    """
    Adds watermark text to bottom-right of an image and returns bytes.
    """
    img = Image.open(image_path).convert("RGBA")
    width, height = img.size

    overlay = Image.new("RGBA", img.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # fallback font
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except:
        font = ImageFont.load_default()

    text_w, text_h = draw.textsize(watermark_text, font=font)

    x = width - text_w - 15
    y = height - text_h - 15

    # watermark background box
    draw.rectangle(
        [x - 8, y - 6, x + text_w + 8, y + text_h + 6],
        fill=(0, 0, 0, 80)
    )

    # watermark text
    draw.text((x, y), watermark_text, font=font, fill=(255, 255, 255, 180))

    combined = Image.alpha_composite(img, overlay).convert("RGB")

    out = io.BytesIO()
    combined.save(out, format="JPEG")
    out.seek(0)
    return out.read()
