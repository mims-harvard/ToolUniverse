"""Local indices of three NCBI Bookshelf books, built once and kept.

StatPearls, LactMed and LiverTox are published as open-access archives on
NCBI's literature archive (https://ftp.ncbi.nlm.nih.gov/pub/litarch/, one
BITS/NXML file per chapter or drug record). None of them has a search API,
and Europe PMC's search does not index Bookshelf. This module downloads an
archive, parses it into a compact SQLite index and keeps the index, so the
tools in ``ncbi_bookshelf_reference_tool`` answer offline from then on:

  * StatPearls (NBK430685, ~2 GB archive) -> statpearls.sqlite (~360 MB):
    chapters, ordered section outline, SQLite FTS5 (BM25) over chapter
    title + section heading + section text
  * LactMed (NBK501922, ~210 MB) -> lactmed.sqlite (~10 MB): one row per drug
    record, its lactation sections and every listed name
  * LiverTox (NBK547852, ~200 MB) -> livertox.sqlite (~11 MB): one row per
    drug / class record, hepatotoxicity sections, likelihood score, trade
    names, and the LiverTox master list

Usage::

    python -m tooluniverse.ncbi_bookshelf_index build            # all three
    python -m tooluniverse.ncbi_bookshelf_index build --books lactmed livertox
    python -m tooluniverse.ncbi_bookshelf_index build --statpearls statpearls_NBK430685.tar.gz
    python -m tooluniverse.ncbi_bookshelf_index status

The index directory is ``--dir``, else ``$TOOLUNIVERSE_BOOKSHELF_DIR``, else
``ncbi_bookshelf`` under the ToolUniverse user cache directory. Archives are
streamed member by member (nothing is extracted to disk; only ``*.nxml``
members are parsed) and deleted after a successful build unless
``--keep-archives`` is given. An index is written under a temporary name and
moved into place when complete, so a reader never sees a partial index.
``manifest.json`` records each archive's NCBI path, last-updated date and
SHA-256, record counts, parse failures and build time.

Requires SQLite 3.27.0 or newer with FTS5 (``remove_diacritics 2``).
"""

import argparse
import csv
import datetime
import hashlib
import io
import json
import os
import re
import sqlite3
import sys
import tarfile
import time
import unicodedata
import xml.etree.ElementTree as ET
from pathlib import Path

SCHEMA_VERSION = "1"
INDEX_DIR_ENV = "TOOLUNIVERSE_BOOKSHELF_DIR"
LITARCH_URL = "https://ftp.ncbi.nlm.nih.gov/pub/litarch/"
FTS_TOKENIZER = "porter unicode61 remove_diacritics 2"
MIN_SQLITE = "3.27.0"  # 'remove_diacritics 2' was added in SQLite 3.27.0

BOOKS = {
    "statpearls": {
        "book_id": "NBK430685",
        "book_title": "StatPearls",
        "url_slug": "statpearls",
        "index_file": "statpearls.sqlite",
        "archive_size": "about 2 GB",
        "needs_fts5": True,
        "publisher": "StatPearls Publishing, Treasure Island (FL)",
        "license": "CC BY-NC-ND 4.0",
        "citation": (
            "StatPearls [Internet]. Treasure Island (FL): StatPearls Publishing. "
            "CC BY-NC-ND 4.0 (https://creativecommons.org/licenses/by-nc-nd/4.0/); "
            "excerpted from the NCBI Bookshelf open-access archive, citation "
            "markers and layout removed."
        ),
    },
    "lactmed": {
        "book_id": "NBK501922",
        "book_title": "Drugs and Lactation Database (LactMed)",
        "url_slug": "lactmed",
        "index_file": "lactmed.sqlite",
        "archive_size": "about 210 MB",
        "publisher": "National Institute of Child Health and Human Development (US), Bethesda (MD)",
        "license": "US government work (public domain); attribution requested",
        "citation": (
            "Drugs and Lactation Database (LactMed) [Internet]. Bethesda (MD): "
            "National Institute of Child Health and Human Development; 2006-. "
            "US government work (public domain); attribution requested."
        ),
    },
    "livertox": {
        "book_id": "NBK547852",
        "book_title": "LiverTox: Clinical and Research Information on Drug-Induced Liver Injury",
        "url_slug": "livertox",
        "index_file": "livertox.sqlite",
        "archive_size": "about 200 MB",
        "publisher": "National Institute of Diabetes and Digestive and Kidney Diseases (US), Bethesda (MD)",
        "license": "US government work (public domain); attribution requested",
        "citation": (
            "LiverTox [Internet]. Bethesda (MD): National Institute of Diabetes "
            "and Digestive and Kidney Diseases; 2012-. US government work "
            "(public domain); attribution requested."
        ),
    },
}

# Book fields copied into each index's meta table and the manifest.
_BOOK_META = ("book_id", "book_title", "publisher", "license")


def book_meta(name):
    return {key: BOOKS[name][key] for key in _BOOK_META}


def install_command(name, out_dir=None):
    """The command that builds ``name``'s index (into ``out_dir`` when that is
    not the default directory)."""
    command = "python -m tooluniverse.ncbi_bookshelf_index build --books " + name
    if out_dir and os.path.abspath(out_dir) != os.path.abspath(default_index_dir()):
        command += " --dir " + str(out_dir)
    return command


def meta_problem(meta, name, path):
    """Why the index at ``path`` (with these meta rows) cannot serve ``name``."""
    if meta.get("source") != name:
        return "%s is not a %s index." % (path, BOOKS[name]["book_title"])
    if meta.get("schema_version") != SCHEMA_VERSION:
        return (
            "%s has index schema %s; this ToolUniverse reads schema %s. Rebuild it "
            "with `%s`."
            % (
                path,
                meta.get("schema_version"),
                SCHEMA_VERSION,
                install_command(name, os.path.dirname(str(path))),
            )
        )
    return None


def read_meta(path):
    """The meta rows of an index, opened read-only (``immutable=1``: no locks
    or journal, safe on shared and network storage)."""
    uri = Path(path).resolve().as_uri() + "?mode=ro&immutable=1"
    conn = sqlite3.connect(uri, uri=True)
    try:
        return {
            k: json.loads(v) for k, v in conn.execute("SELECT key, value FROM meta")
        }
    finally:
        conn.close()


def default_index_dir():
    """``$TOOLUNIVERSE_BOOKSHELF_DIR``, else ``<user cache>/ncbi_bookshelf``."""
    override = os.environ.get(INDEX_DIR_ENV, "").strip()
    if override:
        return os.path.expanduser(os.path.expandvars(override))
    from .utils import get_user_cache_dir

    return os.path.join(get_user_cache_dir(), "ncbi_bookshelf")


def sqlite_problem():
    """Why this Python's SQLite cannot build or search the StatPearls index,
    or None. Probed directly: version numbers alone miss builds without FTS5."""
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(
            "CREATE VIRTUAL TABLE probe USING fts5(x, tokenize='%s')" % FTS_TOKENIZER
        )
    except sqlite3.Error as exc:
        return (
            "This Python's SQLite %s cannot use the StatPearls full-text index "
            "(FTS5 with tokenize='%s' needs SQLite %s or newer built with FTS5): %s"
            % (sqlite3.sqlite_version, FTS_TOKENIZER, MIN_SQLITE, exc)
        )
    finally:
        conn.close()
    return None


# Section headings whose content is bibliography, quiz links or chemical
# structure tables. They are dropped everywhere (all three books).
SKIP_HEADINGS = {
    "references",
    "review questions",
    "annotated bibliography",
    "other reference links",
    "chemical formula and structure",
    "chemical formulas and structures",
}

# Elements rendered as their own line(s) rather than inline text.
BLOCK_TAGS = {
    "p",
    "list",
    "list-item",
    "table-wrap",
    "table",
    "boxed-text",
    "disp-quote",
    "def-list",
    "def-item",
    "statement",
    "verse-group",
    "disp-formula",
    "fig",
    "fig-group",
    "ref-list",
    "sec",
}
# Elements whose content is dropped entirely.
DROP_TAGS = {
    "fig",
    "fig-group",
    "ref-list",
    "graphic",
    "media",
    "alternatives",
    "object-id",
    "label",
}

# "[1]", "[1,2]", "[3-5]", "[1, 4-6]" citation markers left by <xref> numbers.
_CITATION_RE = re.compile(r"\s?\[\s*\d+(?:\s*[-–,]\s*\d+)*\s*\]")
_SPACE_RE = re.compile(r"[ \t   ]+")


# ---------------------------------------------------------------------------
# text helpers
# ---------------------------------------------------------------------------


def normalize_name(name):
    """Lower-case a name and reduce it to alphanumeric tokens.

    The index stores names normalized by this function and the tools
    normalize queries with it, so the two always agree.
    """
    if not name:
        return ""
    text = unicodedata.normalize("NFKD", str(name))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.replace("®", " ").replace("™", " ").replace("©", " ")
    text = re.sub(r"[^0-9a-zA-Z]+", " ", text.lower())
    return " ".join(text.split())


def local(tag):
    """Tag name without namespace."""
    if not isinstance(tag, str):
        return ""
    return tag.rsplit("}", 1)[-1]


def _ws(text):
    """Source whitespace (including line breaks inside a paragraph) -> one space."""
    return re.sub(r"\s+", " ", text or "")


def clean_text(text):
    """Drop citation markers and blank runs; keep nested-list indentation.

    Line breaks here only ever come from block structure (paragraphs, list
    items, table rows), because ``inline_text`` folds source line breaks.
    """
    text = _CITATION_RE.sub("", text)
    out = []
    for line in text.split("\n"):
        body = _SPACE_RE.sub(" ", line).strip()
        indent = len(line) - len(line.lstrip(" "))
        if body.startswith("- ") and indent >= 2:
            body = " " * min(indent - indent % 2, 6) + body
        if body or (out and out[-1]):
            out.append(body)
    return "\n".join(out).strip()


def inline_text(elem):
    """Text of an element with inline children; nested blocks become lines."""
    parts = [_ws(elem.text)]
    for child in elem:
        tag = local(child.tag)
        if tag in DROP_TAGS:
            pass
        elif tag in BLOCK_TAGS:
            block = render_block(child)
            if block:
                parts.append("\n" + block + "\n")
        elif tag == "related-object" and child.get("object-type") == "image":
            pass
        elif tag == "break":
            parts.append("\n")
        else:
            parts.append(inline_text(child))
        parts.append(_ws(child.tail))
    return "".join(parts)


def render_table(table_wrap):
    lines = []
    for child in table_wrap:
        tag = local(child.tag)
        if tag == "caption":
            caption = " ".join(inline_text(child).split())
            if caption:
                lines.append(
                    caption
                    if caption.lower().startswith("table")
                    else "Table: " + caption
                )
        elif tag in ("table", "alternatives"):
            tables = (
                [child]
                if tag == "table"
                else [t for t in child if local(t.tag) == "table"]
            )
            for table in tables:
                for row in table.iter():
                    if local(row.tag) != "tr":
                        continue
                    cells = [
                        " ".join(inline_text(cell).split())
                        for cell in row
                        if local(cell.tag) in ("td", "th")
                    ]
                    if any(cells):
                        lines.append(" | ".join(cells))
        elif tag == "table-wrap-foot":
            foot = " ".join(inline_text(child).split())
            if foot:
                lines.append(foot)
    return "\n".join(lines)


def render_block(elem):
    tag = local(elem.tag)
    if tag in DROP_TAGS:
        return ""
    if tag == "list":
        items = []
        for item in elem:
            if local(item.tag) == "list-item":
                lines = [
                    line.rstrip()
                    for line in render_children(item).split("\n")
                    if line.strip()
                ]
                if lines:
                    # A nested list keeps its own lines, indented under the item.
                    items.append(
                        "- "
                        + lines[0].strip()
                        + "".join("\n  " + line for line in lines[1:])
                    )
        return "\n".join(items)
    if tag in ("table-wrap", "table"):
        return render_table(elem if tag == "table-wrap" else _wrap(elem))
    if tag in (
        "boxed-text",
        "disp-quote",
        "list-item",
        "def-list",
        "def-item",
        "statement",
        "verse-group",
    ):
        return render_children(elem)
    return inline_text(elem).strip()


def _wrap(table):
    wrapper = ET.Element("table-wrap")
    wrapper.append(table)
    return wrapper


def render_children(elem, skip=("title", "sec", "ref-list")):
    """Render the block content of ``elem`` (excluding nested sections)."""
    blocks = []
    if (elem.text or "").strip():
        blocks.append(_ws(elem.text).strip())
    for child in elem:
        tag = local(child.tag)
        if tag in skip or tag in DROP_TAGS:
            pass
        elif tag == "related-object" and child.get("object-type") == "image":
            pass
        elif tag in BLOCK_TAGS:
            block = render_block(child)
            if block:
                blocks.append(block)
        else:
            text = inline_text(child).strip()
            if text:
                blocks.append(text)
        if (child.tail or "").strip():
            blocks.append(_ws(child.tail).strip())
    return "\n".join(blocks)


def heading_of(sec):
    for child in sec:
        if local(child.tag) == "title":
            return " ".join(inline_text(child).split())
    return ""


def outline(body):
    """Ordered section nodes of a <body>: (level, heading, path, own_text).

    ``own_text`` is the section's content without its nested sections; a
    nested section follows its parent with ``level + 1``. Content placed
    directly in <body> before the first section becomes a level-1 node with
    an empty heading. Bibliography / quiz / structure sections are dropped
    with everything below them.
    """
    nodes = []
    preamble = clean_text(render_children(body))
    if preamble:
        nodes.append((1, "", "", preamble))

    def walk(sec, level, parents):
        heading = heading_of(sec)
        if heading.strip().lower().rstrip(":") in SKIP_HEADINGS:
            return
        path = " > ".join(parents + [heading]) if heading else " > ".join(parents)
        nodes.append((level, heading, path, clean_text(render_children(sec))))
        for child in sec:
            if local(child.tag) == "sec":
                walk(child, level + 1, parents + [heading] if heading else parents)

    for child in body:
        if local(child.tag) == "sec":
            walk(child, 1, [])
    return nodes


def find_first(root, name):
    for elem in root.iter():
        if local(elem.tag) == name:
            return elem
    return None


def date_of(meta, date_types=("updated", "revised")):
    """ISO date (YYYY-MM-DD, or YYYY-MM / YYYY when partial) from pub-history."""
    if meta is None:
        return ""
    for elem in meta.iter():
        if local(elem.tag) != "date" or elem.get("date-type") not in date_types:
            continue
        values = {local(c.tag): (c.text or "").strip() for c in elem}
        year, month, day = values.get("year"), values.get("month"), values.get("day")
        if not year:
            continue
        if month and day:
            return "%04d-%02d-%02d" % (int(year), int(month), int(day))
        if month:
            return "%04d-%02d" % (int(year), int(month))
        return year
    return ""


def parse_xml(data):
    """Parse NXML bytes. External DTDs are never loaded."""
    try:
        return ET.fromstring(data)
    except ET.ParseError:
        # Undefined named entities are the only failure seen in practice;
        # lxml's recovering parser keeps the rest of the document.
        from lxml import etree as LET

        parser = LET.XMLParser(
            recover=True,
            resolve_entities=False,
            load_dtd=False,
            no_network=True,
            huge_tree=True,
        )
        root = LET.fromstring(data, parser)
        if root is None:
            raise
        return ET.fromstring(LET.tostring(root))


def part_meta(root):
    """(part_id, title, book_part_meta element, body element)."""
    meta = find_first(root, "book-part-meta")
    title = ""
    if meta is not None:
        title_group = find_first(meta, "title-group")
        if title_group is not None:
            title = heading_of(title_group)
    part_id = root.get("id") or ""
    if meta is not None:
        pid = find_first(meta, "book-part-id")
        if pid is not None and (pid.text or "").strip():
            part_id = pid.text.strip()
    return part_id, title, meta, find_first(root, "body")


# ---------------------------------------------------------------------------
# input iteration
# ---------------------------------------------------------------------------


def _utc_now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def new_db(path):
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=OFF")
    conn.execute("PRAGMA synchronous=OFF")
    conn.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
    return conn


def finish_db(conn, name, counts):
    meta = {
        "source": name,
        "schema_version": SCHEMA_VERSION,
        **book_meta(name),
        "counts": counts,
    }
    conn.executemany(
        "INSERT INTO meta VALUES (?, ?)", [(k, json.dumps(v)) for k, v in meta.items()]
    )
    conn.commit()
    conn.execute("VACUUM")
    conn.close()


# ---------------------------------------------------------------------------
# StatPearls
# ---------------------------------------------------------------------------


def build_statpearls(source, out_path, log=print):
    conn = new_db(out_path)
    conn.executescript(
        """
        CREATE TABLE chapters(
            chapter_id TEXT PRIMARY KEY, title TEXT, title_norm TEXT,
            updated TEXT, archived INTEGER, nursing INTEGER, indexed INTEGER,
            in_toc INTEGER, source_file TEXT, n_sections INTEGER, n_chars INTEGER);
        CREATE TABLE sections(
            sec_rowid INTEGER PRIMARY KEY, chapter_id TEXT, ord INTEGER,
            level INTEGER, heading TEXT, path TEXT, title TEXT, text TEXT);
        CREATE INDEX sections_chapter ON sections(chapter_id, ord);
        CREATE INDEX chapters_title ON chapters(title_norm);
        """
    )
    counts = {
        "files": 0,
        "chapters": 0,
        "sections": 0,
        "archived": 0,
        "nursing": 0,
        "not_indexed": 0,
        "empty": 0,
        "parse_failures": [],
    }
    toc_ids = None
    for name, data in iter_members(source, ".nxml"):
        counts["files"] += 1
        try:
            root = parse_xml(data)
        except Exception as exc:  # recorded, never fatal
            counts["parse_failures"].append(
                [name, type(exc).__name__ + ": " + str(exc)[:200]]
            )
            continue
        if root.get("content-type") == "toc":
            # The book's table of contents lists the current chapters; the
            # archived and nursing chapters are not in it.
            toc_ids = {
                e.get("document-id")
                for e in root.iter()
                if local(e.tag) == "related-object" and e.get("document-id")
            }
            counts["toc_file"] = name
            continue
        part_id, title, meta, body = part_meta(root)
        if body is None or not title:
            counts["empty"] += 1
            continue
        nodes = [n for n in outline(body) if n[1] or n[3]]
        if not nodes:
            counts["empty"] += 1
            continue
        chapter_id = part_id or os.path.splitext(name)[0]
        book_part = find_first(root, "book-part")
        archived = int("(archived)" in title.lower())
        indexed = (
            None
            if book_part is None or book_part.get("indexed") is None
            else int(book_part.get("indexed") != "no")
        )
        nursing = int(chapter_id.startswith("nurse-") or title.endswith("(Nursing)"))
        n_chars = sum(len(n[3]) for n in nodes)
        conn.execute(
            "INSERT OR REPLACE INTO chapters VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                chapter_id,
                title,
                normalize_name(title),
                date_of(meta),
                archived,
                nursing,
                indexed,
                None,
                name,
                len(nodes),
                n_chars,
            ),
        )
        conn.execute("DELETE FROM sections WHERE chapter_id = ?", (chapter_id,))
        conn.executemany(
            "INSERT INTO sections(chapter_id, ord, level, heading, path, title, text)"
            " VALUES (?,?,?,?,?,?,?)",
            [
                (chapter_id, i, lvl, head, path, title, text)
                for i, (lvl, head, path, text) in enumerate(nodes)
            ],
        )
        counts["chapters"] += 1
        counts["sections"] += len(nodes)
        counts["archived"] += archived
        counts["nursing"] += nursing
        counts["not_indexed"] += indexed == 0
        if counts["chapters"] % 1000 == 0:
            log("statpearls: %d chapters" % counts["chapters"])
            conn.commit()
    if toc_ids is not None:
        conn.execute("CREATE TEMP TABLE toc(chapter_id TEXT PRIMARY KEY)")
        conn.executemany(
            "INSERT OR IGNORE INTO toc VALUES (?)", [(i,) for i in toc_ids]
        )
        conn.execute(
            "UPDATE chapters SET in_toc = chapter_id IN (SELECT chapter_id FROM toc)"
        )
        counts["toc_entries"] = len(toc_ids)
        counts["in_toc"] = conn.execute(
            "SELECT COUNT(*) FROM chapters WHERE in_toc = 1"
        ).fetchone()[0]
    conn.executescript(
        """
        CREATE VIRTUAL TABLE sections_fts USING fts5(
            title, heading, text, content='sections', content_rowid='sec_rowid',
            tokenize='%s');
        INSERT INTO sections_fts(sections_fts) VALUES('rebuild');
        INSERT INTO sections_fts(sections_fts) VALUES('optimize');
        """
        % FTS_TOKENIZER
    )
    # A chapter re-parsed under an existing id replaced its rows above.
    counts["chapters"] = conn.execute("SELECT COUNT(*) FROM chapters").fetchone()[0]
    counts["sections"] = conn.execute("SELECT COUNT(*) FROM sections").fetchone()[0]
    finish_db(conn, "statpearls", counts)
    return counts


# ---------------------------------------------------------------------------
# LactMed
# ---------------------------------------------------------------------------


def build_lactmed(source, out_path, log=print):
    conn = new_db(out_path)
    conn.executescript(
        """
        CREATE TABLE records(
            record_id TEXT PRIMARY KEY, title TEXT, revised TEXT, casrn TEXT,
            drug_classes TEXT, record_type TEXT, source_file TEXT);
        CREATE TABLE sections(record_id TEXT, ord INTEGER, heading TEXT, text TEXT);
        CREATE TABLE names(name_norm TEXT, record_id TEXT, kind TEXT, name TEXT);
        CREATE INDEX sections_record ON sections(record_id, ord);
        CREATE INDEX names_norm ON names(name_norm);
        """
    )
    counts = {
        "files": 0,
        "records": 0,
        "drug_records": 0,
        "other_records": 0,
        "names": 0,
        "parse_failures": [],
    }
    for name, data in iter_members(source, ".nxml"):
        counts["files"] += 1
        try:
            root = parse_xml(data)
        except Exception as exc:
            counts["parse_failures"].append(
                [name, type(exc).__name__ + ": " + str(exc)[:200]]
            )
            continue
        record_id, title, meta, body = part_meta(root)
        if body is None or not title:
            counts["other_records"] += 1
            continue
        record_id = record_id or os.path.splitext(name)[0]
        nodes = outline(body)
        rows = []
        casrn, classes = "", []
        for _lvl, head, path, text in nodes:
            top = path.split(" > ")[0] if path else ""
            if top == "Substance Identification":
                if head == "CAS Registry Number":
                    casrn = text.strip()
                elif head == "Drug Class":
                    classes = [
                        line
                        for line in text.split("\n")
                        if line
                        and line not in ("Breast Feeding", "Lactation", "Milk, Human")
                    ]
                continue
            if not text:
                continue
            if head == "" and text.startswith("CASRN:"):
                casrn = casrn or text.split(":", 1)[1].strip()
                continue
            rows.append((head, text))
        headings = {h for h, _ in rows}
        record_type = (
            "drug" if "Summary of Use during Lactation" in headings else "other"
        )
        conn.execute(
            "INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?)",
            (
                record_id,
                title,
                date_of(meta),
                casrn,
                json.dumps(classes),
                record_type,
                name,
            ),
        )
        conn.executemany(
            "INSERT INTO sections VALUES (?,?,?,?)",
            [(record_id, i, h, t) for i, (h, t) in enumerate(rows)],
        )
        names = [(title, "title"), (record_id, "record_id")]
        if meta is not None:
            for kwd in meta.iter():
                if local(kwd.tag) == "kwd" and (kwd.text or "").strip():
                    names.append((kwd.text.strip(), "synonym"))
        seen = set()
        for raw, kind in names:
            norm = normalize_name(raw)
            # Registry numbers and catalogue codes in the keyword list ("21",
            # "-93/26") carry no letters or are too short to be a drug name.
            if kind == "synonym" and (len(norm) < 3 or not re.search("[a-z]", norm)):
                continue
            if norm and norm not in seen:
                seen.add(norm)
                conn.execute(
                    "INSERT INTO names VALUES (?,?,?,?)", (norm, record_id, kind, raw)
                )
                counts["names"] += 1
        counts["records"] += 1
        counts["drug_records" if record_type == "drug" else "other_records"] += 1
    finish_db(conn, "lactmed", counts)
    return counts


# ---------------------------------------------------------------------------
# LiverTox
# ---------------------------------------------------------------------------

# A likelihood statement is its own paragraph and starts with the phrase:
#   "Likelihood score: E* (unproven but suspected rare cause ...)."
#   "Likelihood score: A [HD] (well known cause ... in high doses)."
#   "Likelihood score (venlafaxine): B (...)."  -- one per agent in a
#   multi-agent chapter, which is why every statement is kept verbatim.
_STATEMENT_RE = re.compile(r"^\s*likelihood scores?\b", re.IGNORECASE)
# The single-score form, parsed only when it is the record's only statement.
_SINGLE_SCORE_RE = re.compile(
    r"^\s*likelihood scores?\s*:\s*([A-EX]\*?(?:\s*\[[^\]]*\])?)(?![A-Za-z])"
    r"\s*(?:\(([^)]*)\))?",
    re.IGNORECASE,
)


def likelihood_statements(rows):
    """Every 'Likelihood score...' paragraph, Hepatotoxicity section first."""
    ordered = sorted(rows, key=lambda row: row[0] != "Hepatotoxicity")
    found = []
    for _head, _path, text in ordered:
        for line in text.split("\n"):
            if _STATEMENT_RE.match(line) and line.strip() not in found:
                found.append(line.strip())
    return found


def single_score(statements):
    """(score, wording) when the record states exactly one plain score."""
    if len(statements) != 1:
        return "", ""
    match = _SINGLE_SCORE_RE.match(statements[0])
    if not match:
        return "", ""
    return match.group(1).replace(" ", "").upper(), (match.group(2) or "").strip()


def parse_trade_names(text):
    """'Nabumetone \u2013 Generic, Relafen\u00ae' -> ['Relafen'] (one line per product)."""
    names = []
    for line in text.split("\n"):
        if "\u2013" in line:
            _, _, rest = line.partition("\u2013")
        elif " - " in line:
            _, _, rest = line.partition(" - ")
        else:
            continue
        for item in rest.split(","):
            item = item.replace("\u00ae", "").replace("\u2122", "").strip(" .;")
            if item and item.lower() not in ("generic", "generics") and len(item) <= 60:
                names.append(item)
    return names


def iter_members(source, suffix):
    """(basename, bytes) of members ending with ``suffix`` (tar.gz or directory).

    macOS AppleDouble companions ("._name.nxml"), which appear when a fixture
    directory is copied off a Mac, are metadata and are skipped.
    """
    if os.path.isdir(source):
        for name in sorted(os.listdir(source)):
            if name.endswith(suffix) and not name.startswith("._"):
                with open(os.path.join(source, name), "rb") as handle:
                    yield name, handle.read()
        return
    with tarfile.open(source, "r|gz") as archive:
        for member in archive:
            base = os.path.basename(member.name)
            if member.isfile() and base.endswith(suffix) and not base.startswith("._"):
                yield base, archive.extractfile(member).read()


def read_masterlist(data):
    """Rows of the LiverTox master list workbook (ingredient -> chapter).

    Columns (row 2 is the header): Count, Ingredient, Brand Name, Likelihood
    Score, Chapter Title, Last Update, Year Approved, In LiverTox, Primary
    Classification, Secondary Classification. Formula cells are read from
    their cached values. Returns None when openpyxl is unavailable.
    """
    try:
        import openpyxl
    except ImportError:
        return None
    book = openpyxl.load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    rows = list(book.worksheets[0].iter_rows(values_only=True))
    header = [str(c).strip() if c is not None else "" for c in rows[1]]
    out = []
    for row in rows[2:]:
        entry = {
            header[i]: row[i] for i in range(min(len(header), len(row))) if header[i]
        }
        if entry.get("Ingredient"):
            out.append(entry)
    return out


def _master_value(entry, key):
    value = entry.get(key)
    if isinstance(value, datetime.datetime):
        return value.strftime("%Y-%m-%d")
    return str(value).strip() if value not in (None, "") else ""


def build_livertox(source, out_path, log=print):
    conn = new_db(out_path)
    conn.executescript(
        """
        CREATE TABLE records(
            record_id TEXT PRIMARY KEY, title TEXT, updated TEXT,
            likelihood_score TEXT, likelihood_text TEXT, likelihood_statements TEXT,
            drug_class TEXT, trade_names TEXT, record_type TEXT, source_file TEXT);
        CREATE TABLE sections(record_id TEXT, ord INTEGER, heading TEXT, path TEXT,
                              text TEXT);
        CREATE TABLE names(name_norm TEXT, record_id TEXT, kind TEXT, name TEXT);
        CREATE TABLE masterlist(ingredient_norm TEXT, ingredient TEXT, record_id TEXT,
                                chapter_title TEXT, likelihood_score TEXT,
                                brand_name TEXT, last_update TEXT, in_livertox TEXT,
                                classification TEXT);
        CREATE INDEX sections_record ON sections(record_id, ord);
        CREATE INDEX names_norm ON names(name_norm);
        CREATE INDEX masterlist_norm ON masterlist(ingredient_norm);
        """
    )
    counts = {
        "files": 0,
        "records": 0,
        "drug_records": 0,
        "overview_records": 0,
        "with_single_likelihood_score": 0,
        "with_likelihood_statements": 0,
        "names": 0,
        "skipped": 0,
        "parse_failures": [],
        "masterlist_rows": 0,
        "masterlist_mapped": 0,
        "masterlist_new_names": 0,
        "masterlist_unmapped": 0,
    }
    for name, data in iter_members(source, ".nxml"):
        counts["files"] += 1
        try:
            root = parse_xml(data)
        except Exception as exc:
            counts["parse_failures"].append(
                [name, type(exc).__name__ + ": " + str(exc)[:200]]
            )
            continue
        record_id, title, meta, body = part_meta(root)
        if body is None or not title:
            counts["skipped"] += 1
            continue
        record_id = record_id or os.path.splitext(name)[0]
        rows, trade_names, drug_class = [], [], ""
        for _lvl, head, path, text in outline(body):
            if head.upper() == "PRODUCT INFORMATION":
                # Labelled blocks: REPRESENTATIVE TRADE NAMES / DRUG CLASS / ...
                label, buckets = None, {}
                for line in text.split("\n"):
                    # Labels are upper case, optionally qualified by an agent:
                    # "DRUG CLASS", "COMPLETE LABELING (Venlafaxine)".
                    head = line.split("(")[0].strip()
                    if head.isupper() and len(line) < 80:
                        label = head
                        continue
                    if label:
                        buckets.setdefault(label, []).append(line)
                trade_names = parse_trade_names(
                    "\n".join(buckets.get("REPRESENTATIVE TRADE NAMES", []))
                )
                drug_class = "; ".join(buckets.get("DRUG CLASS", []))
            if text:
                rows.append((head, path, text))
        if not rows:
            counts["skipped"] += 1
            continue
        statements = likelihood_statements(rows)
        score, score_text = single_score(statements)
        headings = {h for h, _p, _t in rows}
        # Drug (or drug-class) chapters carry a Hepatotoxicity section and
        # either product information or a likelihood statement; class
        # overviews and the book's own front matter carry neither.
        record_type = (
            "drug"
            if "Hepatotoxicity" in headings
            and ("PRODUCT INFORMATION" in headings or statements)
            else "overview"
        )
        conn.execute(
            "INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                record_id,
                title,
                date_of(meta),
                score,
                score_text,
                json.dumps(statements),
                drug_class,
                json.dumps(trade_names),
                record_type,
                name,
            ),
        )
        conn.executemany(
            "INSERT INTO sections VALUES (?,?,?,?,?)",
            [(record_id, i, h, p, t) for i, (h, p, t) in enumerate(rows)],
        )
        seen = set()
        for raw, kind in [(title, "title"), (record_id, "record_id")] + [
            (t, "trade_name") for t in trade_names
        ]:
            norm = normalize_name(raw)
            if norm and norm not in seen:
                seen.add(norm)
                conn.execute(
                    "INSERT INTO names VALUES (?,?,?,?)", (norm, record_id, kind, raw)
                )
                counts["names"] += 1
        counts["records"] += 1
        counts["drug_records" if record_type == "drug" else "overview_records"] += 1
        counts["with_single_likelihood_score"] += bool(score)
        counts["with_likelihood_statements"] += bool(statements)

    # The master list maps ingredients covered inside another chapter
    # (e.g. one agent of a drug-class chapter) to that chapter's title.
    masterlist = None
    for name, data in iter_members(source, ".xlsx"):
        if name.lower().startswith("masterlist"):
            masterlist = read_masterlist(data)
            counts["masterlist_file"] = name
    if masterlist is None:
        counts["masterlist_rows"] = None
    else:
        titles = {}
        for record_id, title in conn.execute("SELECT record_id, title FROM records"):
            titles.setdefault(normalize_name(title), record_id)
        for entry in masterlist:
            ingredient = _master_value(entry, "Ingredient")
            chapter = _master_value(entry, "Chapter Title")
            record_id = titles.get(normalize_name(chapter)) or titles.get(
                normalize_name(ingredient)
            )
            counts["masterlist_rows"] += 1
            classification = "; ".join(
                v
                for v in (
                    _master_value(entry, "Primary Classification"),
                    _master_value(entry, "Secondary Classification"),
                )
                if v
            )
            conn.execute(
                "INSERT INTO masterlist VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    normalize_name(ingredient),
                    ingredient,
                    record_id,
                    chapter,
                    _master_value(entry, "Likelihood Score"),
                    _master_value(entry, "Brand Name"),
                    _master_value(entry, "Last Update"),
                    _master_value(entry, "In LiverTox"),
                    classification,
                ),
            )
            if not record_id:
                counts["masterlist_unmapped"] += 1
                continue
            counts["masterlist_mapped"] += 1
            norm = normalize_name(ingredient)
            known = conn.execute(
                "SELECT 1 FROM names WHERE name_norm = ? AND record_id = ?",
                (norm, record_id),
            ).fetchone()
            if norm and not known:
                conn.execute(
                    "INSERT INTO names VALUES (?,?,?,?)",
                    (norm, record_id, "master_list_ingredient", ingredient),
                )
                counts["masterlist_new_names"] += 1
                counts["names"] += 1
    finish_db(conn, "livertox", counts)
    return counts


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------

DOWNLOAD_TIMEOUT_S = 60
DOWNLOAD_ATTEMPTS = 5


def _session():
    import requests

    from .http_utils import with_user_agent

    session = requests.Session()
    session.headers.update(with_user_agent())
    return session


def file_list(session=None):
    """Rows of NCBI's litarch ``file_list.csv`` (path, title, publisher, year,
    accession, last updated), which names each book's current archive."""
    from .http_utils import request_with_retry

    response = request_with_retry(
        session or _session(),
        "GET",
        LITARCH_URL + "file_list.csv",
        timeout=DOWNLOAD_TIMEOUT_S,
    )
    response.raise_for_status()
    return list(csv.reader(io.StringIO(response.text)))


def locate_archive(name, rows):
    """The book's current archive among ``file_list()`` rows: ``{"path",
    "url", "last_updated"}``. The path changes when NCBI republishes the
    book, so it is looked up rather than fixed."""
    book_id = BOOKS[name]["book_id"]
    for row in rows:
        if len(row) >= 5 and row[4].strip() == book_id:
            path = row[0].strip()
            return {
                "path": path,
                "url": LITARCH_URL + path,
                "last_updated": row[5].strip() if len(row) > 5 else "",
            }
    raise RuntimeError(
        "%s (%s) is not listed in %sfile_list.csv"
        % (BOOKS[name]["book_title"], book_id, LITARCH_URL)
    )


class _IncompleteDownload(OSError):
    """A transfer that ended early or a stale partial file; worth retrying."""


def _fetch_once(session, url, part, log):
    """Append the rest of ``url`` to ``part`` (or start it over)."""
    have = os.path.getsize(part) if os.path.exists(part) else 0
    headers = {"Range": "bytes=%d-" % have} if have else {}
    with session.get(
        url, headers=headers, stream=True, timeout=DOWNLOAD_TIMEOUT_S
    ) as response:
        status = response.status_code
        if status == 416 and have:
            os.remove(part)
            raise _IncompleteDownload("partial file no longer matches; starting over")
        if 400 <= status < 500 and status != 429:
            # A missing file or a refused request does not get better on retry.
            raise RuntimeError("%s: HTTP %d %s" % (url, status, response.reason))
        response.raise_for_status()
        if status == 206:
            total = int(response.headers["Content-Range"].rsplit("/", 1)[1])
        else:
            total, have = int(response.headers.get("Content-Length") or 0), 0
        log("downloading %s (%d of %d bytes present)" % (url, have, total))
        with open(part, "ab" if status == 206 else "wb") as handle:
            for chunk in response.iter_content(chunk_size=1 << 20):
                handle.write(chunk)
    size = os.path.getsize(part)
    if total and size != total:
        raise _IncompleteDownload("got %d of %d bytes" % (size, total))
    return size


def download(url, dest, session=None, log=print):
    """Stream ``url`` to ``dest``, resuming a partial ``dest + '.part'``.

    Retries an interrupted or short transfer (requests' errors are OSError
    subclasses) with backoff, and moves the file to ``dest`` only once its
    size matches what the server announced. Returns ``{"bytes", "sha256",
    "downloaded"}``.
    """
    session = session or _session()
    part = dest + ".part"
    for attempt in range(1, DOWNLOAD_ATTEMPTS + 1):
        try:
            size = _fetch_once(session, url, part, log)
            break
        except (OSError, ValueError, KeyError) as exc:
            if attempt == DOWNLOAD_ATTEMPTS:
                raise RuntimeError(
                    "%s: download failed after %d attempts: %s" % (url, attempt, exc)
                ) from exc
            log("download interrupted (%s); retrying" % exc)
            time.sleep(min(10 * attempt, 60))
    os.replace(part, dest)
    return {"bytes": size, "sha256": sha256_file(dest), "downloaded": _utc_now()}


# ---------------------------------------------------------------------------
# driver
# ---------------------------------------------------------------------------

BUILDERS = {
    "statpearls": build_statpearls,
    "lactmed": build_lactmed,
    "livertox": build_livertox,
}


def _read_manifest(out_dir):
    path = os.path.join(out_dir, "manifest.json")
    if os.path.exists(path):
        with open(path) as handle:
            return json.load(handle)
    return {}


def _write_manifest(out_dir, manifest):
    manifest["updated_at"] = _utc_now()
    path = os.path.join(out_dir, "manifest.json")
    with open(path + ".tmp", "w") as handle:
        json.dump(manifest, handle, indent=2)
    os.replace(path + ".tmp", path)


def _check_sqlite(books):
    problem = (
        sqlite_problem() if any(BOOKS[b].get("needs_fts5") for b in books) else None
    )
    if problem:
        raise RuntimeError(problem)


def _build_one(name, source, out_dir, provenance, log):
    """Build one index into place and return its manifest entry."""
    start = time.time()
    log("building %s from %s" % (name, source))
    out_path = os.path.join(out_dir, BOOKS[name]["index_file"])
    tmp_path = out_path + ".building"
    try:
        counts = BUILDERS[name](source, tmp_path, log=log)
        os.replace(tmp_path, out_path)
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
    entry = {
        "input": os.path.abspath(source),
        "index_file": BOOKS[name]["index_file"],
        "index_bytes": os.path.getsize(out_path),
        "index_sha256": sha256_file(out_path),
        "counts": counts,
        "build_seconds": round(time.time() - start, 1),
        "built_at": _utc_now(),
        **book_meta(name),
    }
    if os.path.isfile(source):
        entry["archive"] = os.path.basename(source)
        entry["archive_bytes"] = os.path.getsize(source)
        entry.update(provenance or {})
        if "archive_sha256" not in entry:  # download() already hashed its file
            entry["archive_sha256"] = sha256_file(source)
    log("%s: %s" % (name, json.dumps(counts)[:500]))
    return entry


def _start_manifest(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    manifest = _read_manifest(out_dir)
    manifest.update(
        {
            "schema_version": SCHEMA_VERSION,
            "build_script": "tooluniverse.ncbi_bookshelf_index",
            "build_script_sha256": sha256_file(os.path.abspath(__file__)),
            "python": sys.version.split()[0],
            "sqlite": sqlite3.sqlite_version,
        }
    )
    manifest.setdefault("sources", {})
    return manifest


def build(sources, out_dir, log=print):
    """Build every source in ``sources`` ({name: archive_or_dir}) into out_dir.

    Each index is written to a temporary file and moved into place only when
    complete; ``manifest.json`` records what was built.
    """
    _check_sqlite(sources)
    manifest = _start_manifest(out_dir)
    for name, source in sources.items():
        manifest["sources"][name] = _build_one(name, source, out_dir, None, log)
    _write_manifest(out_dir, manifest)
    return manifest


def install(books=None, out_dir=None, archives=None, keep_archives=False, log=print):
    """Download (unless an archive is given) and build each book's index.

    ``books`` defaults to all three, or to just the books in ``archives`` (a
    map of book to a local ``.tar.gz`` or ``.nxml`` directory to build from
    instead of downloading). Downloaded archives go to ``<out_dir>/downloads``
    and are deleted after a successful build unless ``keep_archives``.
    """
    out_dir = out_dir or default_index_dir()
    archives = dict(archives or {})
    if books is None:
        books = [] if archives else list(BOOKS)
    books = list(dict.fromkeys(list(books) + list(archives)))
    unknown = [b for b in books if b not in BOOKS]
    if unknown:
        raise ValueError(
            "unknown book(s) %s; choose from %s" % (unknown, ", ".join(BOOKS))
        )
    _check_sqlite(books)  # refuse before a 2 GB download, not after
    manifest = _start_manifest(out_dir)
    session = rows = None
    for name in books:
        source, provenance = archives.get(name), None
        if source is None:
            session = session or _session()
            rows = rows or file_list(session)  # one fetch for every book
            located = locate_archive(name, rows)
            downloads = os.path.join(out_dir, "downloads")
            os.makedirs(downloads, exist_ok=True)
            source = os.path.join(downloads, os.path.basename(located["path"]))
            fetched = download(located["url"], source, session, log=log)
            provenance = {
                "archive_url": located["url"],
                "archive_last_updated": located["last_updated"],
                "archive_sha256": fetched["sha256"],
                "archive_downloaded": fetched["downloaded"],
            }
        entry = _build_one(name, source, out_dir, provenance, log)
        if provenance and not keep_archives:
            os.remove(source)
            entry["archive_deleted_after_build"] = True
        manifest["sources"][name] = entry
        _write_manifest(out_dir, manifest)
    return manifest


def index_problem(name, out_dir=None):
    """Why ``name``'s index in ``out_dir`` cannot be used, or None."""
    out_dir = out_dir or default_index_dir()
    path = os.path.join(out_dir, BOOKS[name]["index_file"])
    if not os.path.isfile(path):
        return "%s does not exist" % path
    try:
        return meta_problem(read_meta(path), name, path)
    except (sqlite3.Error, ValueError) as exc:
        return "cannot read %s: %s" % (path, exc)


def status(out_dir=None):
    """What is installed in the index directory, per book."""
    out_dir = out_dir or default_index_dir()
    sources = _read_manifest(out_dir).get("sources", {})
    report = {
        "index_dir": out_dir,
        "env": INDEX_DIR_ENV,
        "sqlite": sqlite3.sqlite_version,
        "sqlite_problem": sqlite_problem(),
        "books": {},
    }
    for name, book in BOOKS.items():
        path = os.path.join(out_dir, book["index_file"])
        problem = index_problem(name, out_dir)
        entry = {"installed": problem is None, "index_file": path}
        if problem is None:
            entry["index_bytes"] = os.path.getsize(path)
            built = sources.get(name) or {}
            for key in ("built_at", "archive_last_updated", "archive_sha256"):
                if built.get(key):
                    entry[key] = built[key]
            counts = built.get("counts") or {}
            entry["counts"] = {k: v for k, v in counts.items() if isinstance(v, int)}
        else:
            entry["problem"] = problem
            entry["install"] = "%s (downloads %s from NCBI)" % (
                install_command(name, out_dir),
                book["archive_size"],
            )
        report["books"][name] = entry
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="python -m tooluniverse.ncbi_bookshelf_index",
        description="Build and inspect the local StatPearls, LactMed and "
        "LiverTox indices used by the NCBI Bookshelf reference tools.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("build", help="download the archives and build the indices")
    p.add_argument(
        "--books",
        nargs="+",
        choices=list(BOOKS),
        help="books to download and build (default: all three)",
    )
    p.add_argument(
        "--dir", help="index directory (default: %s or the user cache)" % INDEX_DIR_ENV
    )
    for name in BOOKS:
        p.add_argument(
            "--" + name,
            metavar="ARCHIVE",
            help="build %s from this local .tar.gz or .nxml directory instead "
            "of downloading" % name,
        )
    p.add_argument(
        "--keep-archives",
        action="store_true",
        help="keep downloaded archives after building",
    )
    p = sub.add_parser("status", help="show which indices are installed")
    p.add_argument("--dir", help="index directory")
    args = parser.parse_args(argv)
    if args.command == "status":
        print(json.dumps(status(args.dir), indent=2))
        return 0
    archives = {name: getattr(args, name) for name in BOOKS if getattr(args, name)}
    try:
        # Progress goes to stderr so stdout carries only the JSON status report.
        install(
            args.books,
            args.dir,
            archives,
            args.keep_archives,
            log=lambda message: print(message, file=sys.stderr),
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print("error: %s" % exc, file=sys.stderr)
        return 1
    print(json.dumps(status(args.dir), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
