from __future__ import annotations

import hashlib
from typing import Dict

import pdfplumber
from PyPDF2 import PdfReader


def _normalize_text(text: str) -> str:
    if not text:
        return ""
    # Remove NULs and normalize whitespace lightly
    cleaned = text.replace("\x00", "")
    return "\n".join(line.strip() for line in cleaned.splitlines())


def extract_metadata_and_text(path: str) -> Dict[str, object]:
    # Metadata via PyPDF2
    reader = PdfReader(path)
    info = reader.metadata or {}
    title = (getattr(info, 'title', None) or info.get('/Title') or "") or ""
    author = (getattr(info, 'author', None) or info.get('/Author') or "") or ""
    page_count = len(reader.pages)

    # Text via pdfplumber
    texts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            try:
                txt = page.extract_text() or ""
            except Exception:
                txt = ""
            if txt:
                texts.append(txt)
    content_text = _normalize_text("\n".join(texts))

    # MD5
    md5_hash = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            md5_hash.update(chunk)
    md5 = md5_hash.hexdigest()

    return {
        "title": title or "",
        "author": author or "",
        "page_count": page_count,
        "content_text": content_text,
        "md5": md5,
    }


