"""
packager.py — turn a folder of files into (doc_key, text, metadata, text_hash) tuples.
"""

from pathlib import Path
from typing import Dict, List, Tuple, Optional
import hashlib

TextRow = Tuple[str, str, Dict, Optional[str]]


def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _read_utf8(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")


def pack_folder(folder: str, exts=(".txt", ".md")) -> List[TextRow]:
    """
    Walk `folder` and package supported files into datastore-ready rows.

    doc_key     = relative path
    text        = file body
    metadata    = {"title": filename, "path": relpath, "source": "file"}
    text_hash   = sha256(text)[:16]

    Returns:
      list[(doc_key, text, metadata, text_hash)]
    """
    root = Path(folder).resolve()
    rows: List[TextRow] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            rel = str(p.relative_to(root))
            body = _read_utf8(p)
            meta = {"title": p.stem, "path": rel, "source": "file"}
            rows.append((rel, body, meta, _sha16(body)))
    return rows
