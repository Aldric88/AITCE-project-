import fitz
import os
import time
import uuid
import hashlib


def paid_preview_pages(total_pages: int) -> int:
    """
    ✅ dynamic paid-preview rules
    """
    if total_pages <= 4:
        return 1
    if total_pages <= 10:
        return 2
    if total_pages <= 25:
        return 3
    return 5


def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def _cache_key(note_id: str, source_signature: str, preview_pages: int) -> str:
    """
    Cache key changes if note or preview rule changes.
    """
    raw = f"{note_id}|{source_signature}|{preview_pages}"
    return hashlib.sha256(raw.encode()).hexdigest()[:18]


def _apply_watermark(doc: fitz.Document, watermark_text: str):
    """
    Embed watermark on each page (not overlay DIV).
    """
    for page in doc:
        rect = page.rect
        # place watermark diagonally
        page.insert_text(
            fitz.Point(rect.width * 0.12, rect.height * 0.55),
            watermark_text,
            fontsize=28,
            rotate=25,
            color=(0.6, 0.6, 0.6),
            overlay=True
        )


def build_pdf_preview_cached(
    input_path: str,
    output_dir: str,
    note_id: str,
    max_pages: int,
    watermark_text: str | None = None,
    source_signature: str | None = None,
    cache_ttl_seconds: int = 24 * 60 * 60  # 24 hrs
) -> str:
    """
    ✅ Generates preview PDF only once and reuses cached version.
    ✅ Optional watermark support.

    Returns: path to preview PDF
    """
    _ensure_dir(output_dir)
    sig = source_signature or f"{int(os.path.getmtime(input_path))}-{os.path.getsize(input_path)}"
    cache_id = _cache_key(note_id, sig, max_pages)
    cached_path = os.path.join(output_dir, f"{cache_id}.pdf")
    meta_path = os.path.join(output_dir, f"{cache_id}.meta")

    # ✅ Cache hit + not expired
    if os.path.exists(cached_path) and os.path.exists(meta_path):
        try:
            with open(meta_path, "r") as f:
                created_at = int(f.read().strip())

            if int(time.time()) - created_at < cache_ttl_seconds:
                return cached_path
        except:
            pass  # fallthrough to regenerate

    # ✅ Generate new preview
    src = fitz.open(input_path)
    total_pages = src.page_count
    out = fitz.open()
    pages = min(max_pages, total_pages)

    for i in range(pages):
        out.insert_pdf(src, from_page=i, to_page=i)

    if watermark_text:
        _apply_watermark(out, watermark_text)

    out.save(cached_path)
    out.close()
    src.close()

    # ✅ write meta timestamp
    with open(meta_path, "w") as f:
        f.write(str(int(time.time())))

    return cached_path
