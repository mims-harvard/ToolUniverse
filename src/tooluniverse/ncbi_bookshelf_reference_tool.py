"""
NCBI Bookshelf reference tools: StatPearls, LactMed and LiverTox.

Read-only lookups over local SQLite indices that
``python -m tooluniverse.ncbi_bookshelf_index build`` downloads once from the
NCBI Bookshelf open-access archives (https://ftp.ncbi.nlm.nih.gov/pub/litarch/)
and keeps. The tools themselves make no network requests.

  * StatPearls (NBK430685) -- peer-reviewed point-of-care clinical review
    chapters: drug chapters carry indications, administration/dosing,
    adverse effects, monitoring; disease chapters carry evaluation and
    treatment/management; procedure chapters carry technique and
    complications. BM25 full-text search, a section reader, and a one-step
    "management of a condition" lookup.
  * LactMed (NBK501922)    -- drug use during breastfeeding.
  * LiverTox (NBK547852)   -- drug-induced liver injury and its likelihood score.

The index directory is ``fields.index_dir`` in the tool config, else
``$TOOLUNIVERSE_BOOKSHELF_DIR``, else ``ncbi_bookshelf`` under the
ToolUniverse user cache directory. A missing or unreadable index is reported
as an error result naming the build command, never raised.

Every result is bounded to ``MAX_OUTPUT_CHARS`` characters of JSON
(``json.dumps`` with ASCII escaping, the longest common serialization).
Text is only ever cut at a word boundary, and every cut carries a marker
saying how much was left out and how to read it.
"""

import difflib
import functools
import json
import re
import sqlite3
from pathlib import Path

from .base_tool import BaseTool
from .ncbi_bookshelf_index import (
    BOOKS,
    INDEX_DIR_ENV,
    default_index_dir,
    install_command,
    meta_problem,
    normalize_name,
    read_meta,
    sqlite_problem,
)
from .tool_registry import register_tool

MAX_OUTPUT_CHARS = 8000

# Counter-ions, hydrates and esters that name a salt form of the same active
# moiety ("metoprolol tartrate" -> "metoprolol"), and dosage-form words
# ("... extended release tablets"). Only tried after the full name failed.
SALT_WORDS = frozenset(
    """
    hydrochloride hcl dihydrochloride hydrobromide hbr hydroiodide sodium
    disodium potassium dipotassium calcium magnesium lithium zinc aluminum
    ammonium meglumine tromethamine lysine arginine tartrate bitartrate
    succinate maleate mesylate mesilate dimesylate besylate besilate camsylate
    edisylate esylate isethionate tosylate fumarate hemifumarate sulfate
    sulphate bisulfate phosphate diphosphate acetate diacetate citrate
    dicitrate lactate gluconate glucoheptonate bromide chloride iodide nitrate
    malate oxalate pamoate embonate napsylate salicylate stearate palmitate
    xinafoate hyclate monohydrate dihydrate trihydrate sesquihydrate
    hemihydrate hydrate anhydrous propionate dipropionate valerate butyrate
    decanoate enanthate cypionate undecanoate estolate ethylsuccinate
    stearoyl furoate pivalate trometamol cromoglicate olamine hemisulfate
    """.split()
)
FORM_WORDS = frozenset(
    """
    tablet tablets tab tabs capsule capsules cap caps injection injectable
    oral solution suspension syrup elixir drops cream ointment gel lotion
    patch transdermal topical ophthalmic otic nasal spray inhaler inhalation
    intravenous iv im subcutaneous sc extended delayed immediate release
    sustained controlled modified er xr xl sr cr la dr ec odt ir mr powder
    for vial chewable dispersible film coated
    """.split()
)

# Strength and unit tokens ("nabumetone 500 mg tablets").
UNIT_WORDS = frozenset(
    "mg mcg ug g kg ml l mmol meq iu unit units percent microgram micrograms "
    "milligram milligrams gram grams".split()
)

# Generic section-heading aliases for StatPearls ("what is the dose" ->
# the Administration section). Heading words, not drug or disease names.
# Request words that ask for the treatment section, and for the diagnostic
# work-up; the one vocabulary for both heading aliases and the StatPearls
# fallback to a chapter's own treatment / evaluation section.
TREATMENT_WORDS = frozenset(
    "treatment treatments treat treating management manage managing therapy "
    "therapies therapeutic".split()
)
EVALUATION_WORDS = frozenset(
    "diagnosis diagnostic diagnose workup evaluation investigation investigations".split()
)

SECTION_ALIASES = {
    "dose": ["administration", "dosage", "dosing"],
    "doses": ["administration", "dosage", "dosing"],
    "dosage": ["administration", "dosing"],
    "dosing": ["administration", "dosage"],
    "side effects": ["adverse effects"],
    "adverse reactions": ["adverse effects"],
    "overdose": ["toxicity"],
    "mechanism": ["mechanism of action"],
    "uses": ["indications"],
    "indication": ["indications"],
    "contraindication": ["contraindications"],
    **{word: ["treatment management", "management"] for word in TREATMENT_WORDS},
    **{word: ["evaluation"] for word in EVALUATION_WORDS},
}

STOPWORDS = frozenset(
    """
    a an and are as at be by can does do for from has have how in into is it
    its of on or should than that the their there these this to was were what
    when where which who why will with without patient patients
    """.split()
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def name_variants(raw):
    """Names to try for a drug, most literal first, with how each was made."""
    variants = []

    def add(value, how):
        norm = normalize_name(value)
        if norm and norm not in [v for v, _ in variants]:
            variants.append((norm, how))

    add(raw, "exact name")
    without_parens = re.sub(r"\([^)]*\)", " ", str(raw))
    add(without_parens, "name without parenthesized text")
    for inner in re.findall(r"\(([^)]*)\)", str(raw)):
        add(inner, "parenthesized name")
    for base, _how in list(variants):
        tokens = base.split()
        kept = [
            t
            for t in tokens
            if t not in SALT_WORDS
            and t not in FORM_WORDS
            and t not in UNIT_WORDS
            and not t.isdigit()
        ]
        if kept and len(kept) < len(tokens):
            add(" ".join(kept), "name without salt/dosage-form/strength words")
    return variants


def _escaped_len(text):
    return len(json.dumps(text)) - 2


def bound_text(text, limit, hint=""):
    """Cut ``text`` to at most ``limit`` JSON-escaped characters.

    Cuts only at whitespace and appends a marker stating how many characters
    were left out (plus ``hint`` on how to read them). Returns
    ``(text, omitted_chars)``.
    """
    text = text or ""
    if _escaped_len(text) <= limit:
        return text, 0
    marker_template = (
        " [... {n} more characters truncated" + ("; " + hint if hint else "") + " ...]"
    )
    reserve = _escaped_len(marker_template.format(n=len(text)))
    if reserve > limit:
        marker_template = " [... {n} more characters truncated ...]"
        reserve = _escaped_len(marker_template.format(n=len(text)))
        if reserve > limit:
            return "", len(text)
    budget = max(limit - reserve, 0)
    # Map the escaped budget back to a raw prefix length.
    cut, used = 0, 0
    for i, ch in enumerate(text):
        used += _escaped_len(ch)
        if used > budget:
            break
        cut = i + 1
    prefix = text[:cut]
    space = max(prefix.rfind(" "), prefix.rfind("\n"))
    if space > 0 and cut < len(text) and not text[cut].isspace():
        prefix = prefix[:space]
    prefix = prefix.rstrip()
    omitted = len(text) - len(prefix)
    return prefix + marker_template.format(n=omitted), omitted


def paginate(text, page_chars):
    """Split text into pages of at most ``page_chars`` escaped characters,
    breaking only at whitespace (a single longer word gets its own page)."""
    pages, current, size = [], [], 0
    for piece in re.split(r"(\s+)", text or ""):
        if not piece:
            continue
        width = _escaped_len(piece)
        if current and size + width > page_chars and not piece.isspace():
            pages.append("".join(current).strip())
            current, size = [], 0
        if not current and piece.isspace():
            continue
        current.append(piece)
        size += width
    if current:
        pages.append("".join(current).strip())
    return pages or [""]


def allocate(lengths, budget, priority=()):
    """Split ``budget`` characters over items of the given lengths.

    Items whose index is in ``priority`` are served first (in order); the
    rest share what remains by water-filling, so short sections are kept
    whole and only the long ones are cut.
    """
    shares = [0] * len(lengths)
    remaining = budget
    for i in priority:
        shares[i] = min(lengths[i], max(remaining, 0))
        remaining -= shares[i]
    rest = sorted(
        (i for i in range(len(lengths)) if i not in priority), key=lambda i: lengths[i]
    )
    for pos, i in enumerate(rest):
        fair = max(remaining, 0) // (len(rest) - pos)
        shares[i] = min(lengths[i], fair)
        remaining -= shares[i]
    return shares


def share_budget(out, slots, max_chars, overhead_per_slot, priority=()):
    """Cut the texts in ``slots`` ([(container, key, hint)]) so that ``out``
    fits ``max_chars``: what is left after the rest of ``out`` (less
    ``overhead_per_slot`` per slot for flags added afterwards) is shared by
    ``allocate``, and each text is cut at a word with a marker naming
    ``hint``. Returns the number of characters omitted from each slot."""
    lengths = [_escaped_len(c[k]) for c, k, _hint in slots]
    frame = len(json.dumps(out)) - sum(lengths)
    budget = max(max_chars - frame - overhead_per_slot * len(slots) - 64, 0)
    omitted = []
    for (container, key, hint), share in zip(
        slots, allocate(lengths, budget, priority)
    ):
        container[key], cut = bound_text(container[key], share, hint)
        omitted.append(cut)
    return omitted


def fit_result(result, slots, limit=MAX_OUTPUT_CHARS):
    """Shorten the longest string slots until ``json.dumps(result)`` fits.

    ``slots`` is a list of (container, key) pairs whose string values may be
    cut. Used as a final guard; the tools size their text before this.
    """
    for _ in range(50):
        over = len(json.dumps(result)) - limit
        if over <= 0:
            return result
        live = [(c, k) for c, k in slots if isinstance(c.get(k), str) and c.get(k)]
        if not live:
            break
        container, key = max(live, key=lambda ck: _escaped_len(ck[0][ck[1]]))
        current = container[key]
        target = max(_escaped_len(current) - over - 16, 0)
        container[key], _ = bound_text(current, target)
        if container[key] == current:
            container[key] = ""
    return result


class _IndexUnavailable(Exception):
    """The configured index is missing, unreadable or of another schema."""


def _error(message, error_type, **extra):
    out = {"status": "error", "error": message, "error_type": error_type}
    out.update(extra)
    return out


class _BookshelfIndexTool(BaseTool):
    """Opens one of the local Bookshelf indices read-only, per call."""

    SOURCE = ""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.fields = self.tool_config.get("fields") or {}
        self.max_chars = int(self.fields.get("max_output_chars") or MAX_OUTPUT_CHARS)

    @property
    def book(self):
        return BOOKS[self.SOURCE]

    def index_path(self):
        root = Path(self.fields.get("index_dir") or default_index_dir()).expanduser()
        path = root / self.book["index_file"]
        if not path.is_file():
            raise _IndexUnavailable(
                "The local %s index is not installed (%s does not exist). Build it "
                "once with `%s` (downloads %s from NCBI and keeps the index), or "
                "set %s to a directory that holds %s."
                % (
                    self.book["book_title"],
                    path,
                    install_command(self.SOURCE, str(root)),
                    self.book["archive_size"],
                    INDEX_DIR_ENV,
                    self.book["index_file"],
                )
            )
        return path

    def connect(self):
        path = self.index_path()
        try:
            problem = meta_problem(read_meta(path), self.SOURCE, path)
        except (sqlite3.Error, ValueError) as exc:
            problem = "Cannot read the %s index %s: %s" % (
                self.book["book_title"],
                path,
                exc,
            )
        if problem:
            raise _IndexUnavailable(problem)
        # immutable=1: no locking or journal, safe on shared/network storage.
        conn = sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro&immutable=1", uri=True
        )
        conn.row_factory = sqlite3.Row
        return conn

    def chapter_url(self, part_id):
        return "https://www.ncbi.nlm.nih.gov/books/n/%s/%s/" % (
            self.book["url_slug"],
            part_id,
        )

    def source_block(self, part_id=None, title=None, updated=None):
        block = {"book": self.book["book_title"], "book_id": self.book["book_id"]}
        if part_id:
            block["chapter_id"] = part_id
            block["url"] = self.chapter_url(part_id)
        if title:
            block["chapter_title"] = title
        if updated:
            block["last_updated"] = updated
        return block

    def run(self, arguments=None):
        arguments = arguments or {}
        try:
            conn = self.connect()
        except _IndexUnavailable as exc:
            return _error(str(exc), "index_unavailable")
        try:
            result = self.query(conn, arguments)
        except sqlite3.Error as exc:
            problem = sqlite_problem() if self.book.get("needs_fts5") else None
            result = _error(
                "%s index query failed: %s%s"
                % (self.book["book_title"], exc, (". " + problem) if problem else ""),
                "index_error",
            )
        except Exception as exc:  # never raise out of run()
            result = _error(
                "%s lookup failed: %s: %s"
                % (self.book["book_title"], type(exc).__name__, exc),
                "internal_error",
            )
        finally:
            conn.close()
        if len(json.dumps(result)) > self.max_chars:
            result = fit_result(result, self.text_slots(result), self.max_chars)
        return result

    def query(self, conn, arguments):  # pragma: no cover - abstract
        raise NotImplementedError

    @staticmethod
    def text_slots(result):
        """(container, key) pairs of cuttable strings in a result."""
        slots = []
        data = result.get("data")
        items = (
            data if isinstance(data, list) else [data] if isinstance(data, dict) else []
        )
        for item in items:
            if not isinstance(item, dict):
                continue
            for key in ("text", "snippet"):
                if isinstance(item.get(key), str):
                    slots.append((item, key))
            for value in item.values():  # e.g. a management item's "evaluation"
                if isinstance(value, dict) and isinstance(value.get("text"), str):
                    slots.append((value, "text"))
            for section in item.get("sections") or []:
                if isinstance(section, dict) and isinstance(section.get("text"), str):
                    slots.append((section, "text"))
        return slots


# ---------------------------------------------------------------------------
# Drug-record lookups (LactMed, LiverTox)
# ---------------------------------------------------------------------------

# Which kind of name match wins when one name points at several records,
# and how each kind is reported.
_KIND_ORDER = {
    "title": 0,
    "record_id": 1,
    "synonym": 2,
    "trade_name": 2,
    "master_list_ingredient": 3,
}
_KIND_LABEL = {
    "record_id": "record id",
    "synonym": "synonym",
    "trade_name": "trade name",
    "master_list_ingredient": "LiverTox master-list ingredient",
}


def resolve_record(conn, drug_name):
    """Find the record for a drug name.

    Returns ``(record_row, how, other_matches)`` or ``(None, None, suggestions)``.
    Tries the literal name, then the name without parentheses, then without
    salt/dosage-form words; at each step a title match beats a synonym or
    trade-name match, and a drug record beats an overview record.
    """
    for norm, how in name_variants(drug_name):
        rows = conn.execute(
            "SELECT n.kind, n.name, r.* FROM names n JOIN records r USING (record_id)"
            " WHERE n.name_norm = ?",
            (norm,),
        ).fetchall()
        if not rows:
            continue
        best = {}
        for row in rows:
            key = (
                _KIND_ORDER.get(row["kind"], 3),
                row["record_type"] != "drug",
                len(row["title"]),
            )
            if row["record_id"] not in best or key < best[row["record_id"]][0]:
                best[row["record_id"]] = (key, row)
        ranked = [row for _key, row in sorted(best.values(), key=lambda kv: kv[0])]
        top = ranked[0]
        detail = (
            how
            if top["kind"] == "title"
            else "%s, via %s '%s'"
            % (how, _KIND_LABEL.get(top["kind"], top["kind"]), top["name"])
        )
        return top, detail, [r["title"] for r in ranked[1:6]]
    return None, None, suggest_records(conn, drug_name)


def suggest_records(conn, drug_name, limit=6):
    """Close titles/names for a name that matched nothing."""
    norm = normalize_name(drug_name)
    if not norm:
        return []
    titles = {}
    for row in conn.execute(
        "SELECT n.name_norm, r.title FROM names n JOIN records r"
        " USING (record_id) WHERE n.kind IN ('title', 'trade_name')"
    ):
        titles.setdefault(row[0], row[1])
    found = []
    # Each word of a multi-word query (e.g. a combination product) that is
    # itself a record title.
    for token in norm.split():
        if token in titles and titles[token] not in found:
            found.append(titles[token])
    for match in difflib.get_close_matches(norm, list(titles), n=limit, cutoff=0.75):
        if titles[match] not in found:
            found.append(titles[match])
    return found[:limit]


class _DrugRecordTool(_BookshelfIndexTool):
    """Shared shape of LactMed_get_drug / LiverTox_get_drug."""

    PRIORITY_HEADINGS = ()
    HIDDEN_HEADINGS = ()

    def record_sections(self, conn, record_id):
        raise NotImplementedError

    def describe(self, conn, record, drug_name):
        return {}

    def query(self, conn, arguments):
        drug_name = arguments.get("drug_name")
        if not isinstance(drug_name, str) or not drug_name.strip():
            return _error(
                "drug_name is required (a generic or brand drug name).",
                "invalid_argument",
            )
        record, how, others = resolve_record(conn, drug_name)
        if record is None:
            return _error(
                "%s has no record matching '%s' (tried the name as given, without "
                "parentheses, and without salt/dosage-form/strength words). If this is a "
                "brand name, try the generic name. Absence from %s is not evidence about "
                "the drug either way."
                % (
                    self.book["book_title"],
                    drug_name,
                    self.book["book_title"].split(":")[0],
                ),
                "not_found",
                suggestions=others,
                source=self.source_block(),
                license=self.book["citation"],
            )
        sections = [
            s
            for s in self.record_sections(conn, record["record_id"])
            if s["heading"] not in self.HIDDEN_HEADINGS
        ]
        wanted = arguments.get("section")
        data = {"drug": record["title"], "matched": how}
        data.update(self.describe(conn, record, drug_name))
        if others:
            data["other_matching_records"] = others
        source = self.source_block(
            record["record_id"], record["title"], self.updated(record)
        )
        out = {
            "status": "success",
            "data": data,
            "source": source,
            "license": self.book["citation"],
        }

        if isinstance(wanted, str) and wanted.strip():
            chosen = select_sections(wanted, sections)
            if not chosen:
                return _error(
                    "Record '%s' has no section matching '%s'."
                    % (record["title"], wanted),
                    "section_not_found",
                    available_sections=[s["heading"] for s in sections],
                    source=source,
                    license=self.book["citation"],
                )
            data["sections"] = [
                {"heading": s["heading"], "text": s["text"]} for s in chosen
            ]
        else:
            data["sections"] = [
                {"heading": s["heading"], "text": s["text"]} for s in sections
            ]

        # Size the section texts to the budget left after everything else.
        sections = data["sections"]
        originals = [s["text"] for s in sections]
        priority = [
            i
            for h in self.PRIORITY_HEADINGS
            for i, s in enumerate(sections)
            if s["heading"] == h
        ]
        slots = [
            (
                s,
                "text",
                "call again with section='%s' for this section alone" % s["heading"],
            )
            for s in sections
        ]
        omitted = share_budget(out, slots, self.max_chars, 120, priority)
        cut, kept, omitted_sections = [], [], []
        for section, original, lost in zip(sections, originals, omitted):
            if original and not section["text"]:
                omitted_sections.append(section["heading"])
            else:
                kept.append(section)
                if lost:
                    cut.append(section["heading"])
        data["sections"] = kept
        if cut:
            data["truncated_sections"] = cut
        if omitted_sections:
            data["omitted_sections"] = omitted_sections
        # A very small output bound: drop whole sections from the end.
        while kept and len(json.dumps(out)) > self.max_chars:
            data.setdefault("omitted_sections", []).insert(0, kept.pop()["heading"])
        if "omitted_sections" in data:
            data["omitted_note"] = (
                "Sections listed in omitted_sections did not fit; "
                "request one with the section argument."
            )
        return out

    def updated(self, record):
        return record["revised"] if "revised" in record.keys() else record["updated"]


def _contains_words(haystack, needle):
    """Whole-word containment of normalized strings ('uses' is not in 'causes')."""
    return bool(needle) and (" %s " % needle) in (" %s " % haystack)


def _singular(norm):
    return " ".join(
        w[:-1] if len(w) > 3 and w.endswith("s") else w for w in norm.split()
    )


def match_heading(wanted, headings):
    """Pick the heading the caller meant.

    In order: exact (case/punctuation-insensitive), a generic alias such as
    'dosage' -> 'Administration', whole-word containment (shortest heading
    wins), a heading contained in the request, an alias of one word of the
    request, then a close spelling.
    """
    norm = normalize_name(wanted)
    if not norm:
        return None
    normed = [(normalize_name(h), h) for h in headings if h]
    targets = (
        [norm]
        + SECTION_ALIASES.get(norm, [])
        + SECTION_ALIASES.get(_singular(norm), [])
    )
    if _singular(norm) != norm:
        targets.append(_singular(norm))
    for target in targets:
        for n, h in normed:
            if n == target:
                return h
    for target in targets:
        hits = [(len(n), h) for n, h in normed if _contains_words(n, target)]
        if hits:
            return min(hits)[1]
    hits = [(len(n), h) for n, h in normed if _contains_words(norm, n)]
    if hits:
        return max(hits)[1]
    # Aliases of single words of a longer request ('management of overdose',
    # 'treatment options'); the words that only name the treatment section go
    # last, so a more specific word decides.
    words = sorted(
        (w for w in norm.split() if w not in STOPWORDS),
        key=lambda w: w in TREATMENT_WORDS,
    )
    for word in words:
        for target in SECTION_ALIASES.get(word, []) + SECTION_ALIASES.get(
            _singular(word), []
        ):
            hits = [
                (n != target, len(n), h)
                for n, h in normed
                if _contains_words(n, target)
            ]
            if hits:
                return min(hits)[2]
    close = difflib.get_close_matches(norm, [n for n, _ in normed], n=1, cutoff=0.6)
    if close:
        return dict(normed)[close[0]]
    return None


def select_sections(wanted, sections):
    """Sections of a drug record that answer a ``section`` request.

    A heading equal to the request, or every heading that contains it as
    whole words (so 'case report' returns each case and 'Key Points'
    returns the key points of every case); otherwise the single best
    ``match_heading`` result.
    """
    norm = normalize_name(wanted)
    terms = {norm, _singular(norm)} - {""}

    def names(section):
        full = normalize_name(section["heading"])
        last = normalize_name(section["heading"].split(" > ")[-1])
        return {full, last, _singular(full), _singular(last)}

    exact = [s for s in sections if terms & names(s)]
    if exact:
        return exact
    containing = [
        s
        for s in sections
        if any(_contains_words(n, t) for n in names(s) for t in terms)
    ]
    if containing:
        return containing
    heading = match_heading(wanted, [s["heading"] for s in sections])
    return [s for s in sections if s["heading"] == heading]


@register_tool("LactMedDrugTool")
class LactMedDrugTool(_DrugRecordTool):
    """Breastfeeding summary for one drug from the local LactMed index."""

    SOURCE = "lactmed"
    PRIORITY_HEADINGS = ("Summary of Use during Lactation",)

    def record_sections(self, conn, record_id):
        return [
            dict(row)
            for row in conn.execute(
                "SELECT heading, text FROM sections WHERE record_id = ? ORDER BY ord",
                (record_id,),
            )
        ]

    def describe(self, conn, record, drug_name):
        info = {}
        if record["casrn"]:
            info["casrn"] = record["casrn"]
        classes = json.loads(record["drug_classes"] or "[]")
        if classes:
            info["drug_classes"] = classes
        if record["record_type"] != "drug":
            info["record_type"] = record["record_type"]
        return info


@register_tool("LiverToxDrugTool")
class LiverToxDrugTool(_DrugRecordTool):
    """Hepatotoxicity profile and likelihood score from the local LiverTox index."""

    SOURCE = "livertox"
    PRIORITY_HEADINGS = (
        "Introduction",
        "Hepatotoxicity",
        "Mechanism of Injury",
        "Outcome and Management",
    )
    HIDDEN_HEADINGS = ("PRODUCT INFORMATION",)

    def record_sections(self, conn, record_id):
        rows = conn.execute(
            "SELECT heading, path, text FROM sections WHERE record_id = ? ORDER BY ord",
            (record_id,),
        )
        sections = []
        for row in rows:
            # The overview sub-sections are named on their own; case-report
            # parts keep their path ("CASE REPORT > Case 1. ... > Comment").
            heading = row["path"] or row["heading"]
            if heading.startswith("OVERVIEW > "):
                heading = heading[len("OVERVIEW > ") :]
            sections.append({"heading": heading, "text": row["text"]})
        return sections

    def describe(self, conn, record, drug_name):
        info = {"record_type": record["record_type"]}
        statements = json.loads(record["likelihood_statements"] or "[]")
        if record["likelihood_score"]:
            info["likelihood_score"] = record["likelihood_score"]
            if record["likelihood_text"]:
                info["likelihood_score_meaning"] = record["likelihood_text"]
        elif statements:
            # A chapter covering several agents states one score per agent.
            info["likelihood_score"] = None
            info["likelihood_statements"] = statements[:8]
        elif record["record_type"] == "drug":
            info["likelihood_score"] = None
            info["likelihood_note"] = "This chapter states no likelihood score."
        entry = self.master_list_entry(conn, record, drug_name)
        if entry:
            info["master_list_entry"] = entry
        if record["drug_class"]:
            info["drug_class"] = record["drug_class"]
        trade = json.loads(record["trade_names"] or "[]")
        if trade:
            info["trade_names"] = trade[:12]
        return info

    @staticmethod
    def master_list_entry(conn, record, drug_name):
        """The LiverTox master-list row for the requested ingredient, when it
        is covered by a chapter about another or several agents."""
        for norm, _how in name_variants(drug_name):
            row = conn.execute(
                "SELECT * FROM masterlist WHERE ingredient_norm = ? AND record_id = ?",
                (norm, record["record_id"]),
            ).fetchone()
            if row is None:
                continue
            if normalize_name(row["ingredient"]) == normalize_name(record["title"]):
                return None
            entry = {
                "ingredient": row["ingredient"],
                "chapter": record["title"],
                "likelihood_score": row["likelihood_score"] or None,
                "last_update": row["last_update"] or None,
                "source": "LiverTox master list workbook in the same archive",
            }
            return entry
        return None


# ---------------------------------------------------------------------------
# StatPearls
# ---------------------------------------------------------------------------


def fts_query(text, max_terms=16):
    """BM25-friendly FTS5 query: every content word, OR-ed and quoted.

    OR (not FTS5's implicit AND) so a long natural-language question still
    returns the chapters that match most of it, ranked by BM25, instead of
    nothing. Quoting keeps words like NOT/NEAR from being read as operators.
    """
    words = []
    for word in re.findall(r"[0-9a-z]+", normalize_name(text)):
        if word in STOPWORDS or (len(word) < 2 and not word.isdigit()):
            continue
        if word not in words:
            words.append(word)
    return " OR ".join('"%s"' % w for w in words[:max_terms]), words[:max_terms]


@register_tool("StatPearlsSearchTool")
class StatPearlsSearchTool(_BookshelfIndexTool):
    """BM25 search over StatPearls chapter sections, grouped by chapter."""

    SOURCE = "statpearls"
    # bm25() column weights: chapter title, section heading, section text.
    COLUMN_WEIGHTS = (8.0, 3.0, 1.0)
    CANDIDATE_SECTIONS = 400
    SNIPPET_TOKENS = 60

    def query(self, conn, arguments):
        query = arguments.get("query")
        if not isinstance(query, str) or not query.strip():
            return _error(
                "query is required (keywords such as 'amitriptyline dosing').",
                "invalid_argument",
            )
        try:
            limit = int(arguments.get("limit") or 5)
        except (TypeError, ValueError):
            return _error(
                "limit must be an integer between 1 and 10.", "invalid_argument"
            )
        limit = min(max(limit, 1), 10)
        match, words = fts_query(query)
        if not match:
            return _error(
                "query has no searchable words after removing stopwords.",
                "invalid_argument",
            )
        include_archived = arguments.get("include_archived") is True
        order, chapters, info_of = self.rank_chapters(
            conn, query, match, limit, include_archived
        )
        hits = []
        for rank, chapter_id in enumerate(order, 1):
            best = chapters[chapter_id]["best"]
            info = info_of[chapter_id]
            snippet = conn.execute(
                "SELECT snippet(sections_fts, 2, '', '', ' ... ', %d) FROM sections_fts"
                " WHERE sections_fts MATCH ? AND rowid = ?" % self.SNIPPET_TOKENS,
                (match, best["sec_rowid"]),
            ).fetchone()[0]
            hit = {
                "rank": rank,
                "chapter_id": chapter_id,
                "title": info["title"],
                "last_updated": info["updated"],
                "best_section": best["path"]
                or best["heading"]
                or "(chapter introduction)",
                "snippet": " ".join((snippet or "").split()),
                "bm25": round(-best["score"], 3),
            }
            if info["archived"]:
                hit["archived"] = True
            if chapters[chapter_id]["others"]:
                hit["other_matching_sections"] = chapters[chapter_id]["others"]
            hits.append(hit)
        per_hit = (self.max_chars - 900) // max(len(hits), 1) - 420
        for hit in hits:
            hit["snippet"], _ = bound_text(hit["snippet"], max(min(per_hit, 700), 120))
        out = {
            "status": "success",
            "data": hits,
            "metadata": {
                "query_terms": words,
                "matching": "any term (OR), ranked by BM25 over chapter title, "
                "section heading and section text",
                "archived_chapters": "included"
                if include_archived
                else "excluded (StatPearls no longer maintains them; pass "
                "include_archived=true to search them too)",
                "returned": len(hits),
                "next_step": "Read a section with StatPearls_get_chapter_section"
                "(chapter=<chapter_id>, section=<best_section>).",
            },
            "source": self.source_block(),
            "license": self.book["citation"],
        }
        # Under a small output bound, drop the lowest-ranked hits rather
        # than return hits whose snippets were cut to nothing.
        while len(hits) > 1 and len(json.dumps(out)) > self.max_chars:
            hits.pop()
            out["metadata"]["returned"] = len(hits)
            out["metadata"]["dropped_to_fit_output_bound"] = True
        return out

    def rank_chapters(self, conn, query, match, limit, include_archived):
        """Chapters for ``query`` in result order: ``(chapter_ids, best
        sections per chapter, chapter rows)``."""
        weights = ", ".join(str(w) for w in self.COLUMN_WEIGHTS)
        rows = conn.execute(
            "SELECT s.sec_rowid, s.chapter_id, s.heading, s.path,"
            " bm25(sections_fts, %s) AS score"
            " FROM sections_fts JOIN sections s ON s.sec_rowid = sections_fts.rowid"
            " JOIN chapters c ON c.chapter_id = s.chapter_id"
            " WHERE sections_fts MATCH ? %s ORDER BY score LIMIT %d"
            % (
                weights,
                "" if include_archived else "AND c.archived = 0",
                self.CANDIDATE_SECTIONS,
            ),
            (match,),
        ).fetchall()
        chapters, order = {}, []
        self._group(rows, chapters, order, limit)
        # A query that is exactly a chapter title ranks that chapter first,
        # even when shorter sections of another chapter outscore it on BM25.
        exact = conn.execute(
            "SELECT chapter_id FROM chapters WHERE title_norm = ? %s ORDER BY nursing LIMIT 1"
            % ("" if include_archived else "AND archived = 0"),
            (normalize_name(query),),
        ).fetchone()
        if exact and exact[0] not in chapters:
            # Its best sections, to place it although it ranked below the limit.
            own = conn.execute(
                "SELECT s.sec_rowid, s.chapter_id, s.heading, s.path,"
                " bm25(sections_fts, %s) AS score FROM sections_fts JOIN sections s"
                " ON s.sec_rowid = sections_fts.rowid WHERE sections_fts MATCH ?"
                " AND s.chapter_id = ? ORDER BY score LIMIT 4" % weights,
                (match, exact[0]),
            ).fetchall()
            self._group(own, chapters, order, limit + 1)
        if exact and exact[0] in chapters:
            order.remove(exact[0])
            order.insert(0, exact[0])
        info_of = {
            cid: conn.execute(
                "SELECT * FROM chapters WHERE chapter_id = ?", (cid,)
            ).fetchone()
            for cid in order
        }
        order = nursing_after_parent(
            order, {cid: info_of[cid]["title"] for cid in order}
        )
        return order[:limit], chapters, info_of

    @staticmethod
    def _group(rows, chapters, order, limit):
        """Best section per chapter, in score order, up to ``limit`` chapters."""
        for row in rows:
            entry = chapters.get(row["chapter_id"])
            if entry is None:
                if len(order) >= limit:
                    continue
                chapters[row["chapter_id"]] = {"best": row, "others": []}
                order.append(row["chapter_id"])
            elif (
                len(entry["others"]) < 3
                and row["path"] not in entry["others"]
                and row["path"] != entry["best"]["path"]
            ):
                entry["others"].append(row["path"])


def _parent_title(title):
    """'X' for the nursing edition 'X (Nursing)', else None."""
    return title[: -len(" (Nursing)")] if title.endswith(" (Nursing)") else None


def nursing_after_parent(order, titles):
    """Move a chapter 'X' ahead of its nursing edition 'X (Nursing)' when
    both were found; StatPearls derives the nursing edition from the main
    clinical chapter. Everything else keeps its BM25 order."""
    order = list(order)
    for chapter_id in list(order):
        parent_title = _parent_title(titles[chapter_id])
        if parent_title is None:
            continue
        parent = [c for c in order if titles[c] == parent_title]
        if parent and order.index(parent[0]) > order.index(chapter_id):
            order.remove(parent[0])
            order.insert(order.index(chapter_id), parent[0])
    return order


# Top-level StatPearls headings that say how a condition is treated, in the
# order they are tried. Disease chapters use "Treatment / Management";
# procedure chapters "Technique or Treatment"; a few oncology chapters
# "Treatment Planning"; drug chapters "Administration"; anatomy and
# condition-overview chapters "Clinical Significance", "Surgical Considerations"
# or "Issues of Concern";
# short explanation chapters "Summary / Explanation"; nursing editions
# "Medical Management".
MANAGEMENT_HEADINGS = (
    "Treatment / Management",
    "Technique or Treatment",
    "Treatment Planning",
    "Management",
    "Treatment",
    "Medical Management",
    "Administration",
    "Clinical Significance",
    "Surgical Considerations",
    "Issues of Concern",
    "Key Clinical Considerations",
    "Summary / Explanation",
)
EVALUATION_HEADINGS = ("Evaluation", "Diagnosis", "Evaluation and Diagnosis")


@functools.lru_cache(maxsize=None)
def _normalized(headings):
    return tuple(normalize_name(h) for h in headings)


def first_top_section(nodes, headings):
    """Index of the first top-level section named by ``headings`` (tried in
    order, case- and punctuation-insensitively), or None."""
    top = {
        normalize_name(n["heading"]): i
        for i, n in enumerate(nodes)
        if n["level"] == 1 and n["heading"]
    }
    for heading in _normalized(tuple(headings)):
        if heading in top:
            return top[heading]
    return None


def fallback_headings(wanted):
    """The headings to fall back to when no heading matches ``wanted``:
    MANAGEMENT_HEADINGS for a treatment request, EVALUATION_HEADINGS for a
    work-up request, else ()."""
    words = set(normalize_name(wanted).split())
    if words & TREATMENT_WORDS:
        return MANAGEMENT_HEADINGS
    if words & EVALUATION_WORDS:
        return EVALUATION_HEADINGS
    return ()


def chapter_outline(conn, chapter_id):
    """A chapter's sections in reading order."""
    return [
        dict(row)
        for row in conn.execute(
            "SELECT ord, level, heading, path, text FROM sections WHERE chapter_id = ?"
            " ORDER BY ord",
            (chapter_id,),
        )
    ]


def section_text(nodes, index):
    """A section's own text followed by its subsections (with headings)."""
    head = nodes[index]
    parts = [head["text"]] if head["text"] else []
    for node in nodes[index + 1 :]:
        if node["level"] <= head["level"]:
            break
        title = "#" * (node["level"] - head["level"] + 1) + " " + node["heading"]
        parts.append(title + ("\n" + node["text"] if node["text"] else ""))
    return "\n\n".join(parts)


@register_tool("StatPearlsChapterSectionTool")
class StatPearlsChapterSectionTool(_BookshelfIndexTool):
    """Section list or one section's text from a StatPearls chapter."""

    SOURCE = "statpearls"

    def find_chapter(self, conn, chapter):
        """Return (chapter_row, candidates)."""
        text = chapter.strip()
        ident = text.lower()
        if re.fullmatch(r"\d+", ident):
            ident = "article-" + ident
        if re.fullmatch(r"(nurse-)?article-\d+", ident):
            row = conn.execute(
                "SELECT * FROM chapters WHERE chapter_id = ?", (ident,)
            ).fetchone()
            return row, []
        norm = normalize_name(text)
        rows = conn.execute(
            "SELECT * FROM chapters WHERE title_norm = ? ORDER BY archived, nursing",
            (norm,),
        ).fetchall()
        if rows:
            return rows[0], []
        match, _words = fts_query(text)
        if not match:
            return None, []
        # Titles containing every word of the request (stemmed), closest first.
        all_words = " AND ".join(match.split(" OR "))
        rows = conn.execute(
            "SELECT DISTINCT c.* FROM sections_fts JOIN sections s"
            " ON s.sec_rowid = sections_fts.rowid JOIN chapters c USING (chapter_id)"
            " WHERE sections_fts MATCH ? LIMIT 200",
            ("title : (%s)" % all_words,),
        ).fetchall()
        scored = sorted(
            rows,
            key=lambda r: (
                -difflib.SequenceMatcher(None, norm, r["title_norm"]).ratio(),
                r["archived"],
                r["nursing"],
                len(r["title"]),
            ),
        )
        if (
            scored
            and difflib.SequenceMatcher(None, norm, scored[0]["title_norm"]).ratio()
            >= 0.85
        ):
            return scored[0], [r["title"] for r in scored[1:6]]
        return None, ["%s (%s)" % (r["title"], r["chapter_id"]) for r in scored[:8]]

    def query(self, conn, arguments):
        chapter = arguments.get("chapter")
        if not isinstance(chapter, str) or not chapter.strip():
            return _error(
                "chapter is required: a chapter_id from StatPearls_search "
                "(e.g. 'article-17465') or a chapter title.",
                "invalid_argument",
            )
        if re.fullmatch(r"(?i)\s*NBK\d+\s*", chapter):
            return _error(
                "Chapter NBK accession numbers are not part of the StatPearls archive; "
                "use the chapter_id from StatPearls_search (e.g. 'article-17465') or the "
                "chapter title.",
                "invalid_argument",
            )
        row, candidates = self.find_chapter(conn, chapter)
        if row is None:
            return _error(
                "No StatPearls chapter matches '%s'." % chapter,
                "not_found",
                candidates=candidates,
                hint="Use StatPearls_search to find chapters by topic.",
                source=self.source_block(),
                license=self.book["citation"],
            )
        nodes = chapter_outline(conn, row["chapter_id"])
        source = self.source_block(row["chapter_id"], row["title"], row["updated"])
        data = {"chapter_id": row["chapter_id"], "title": row["title"]}
        if row["archived"]:
            data["archived"] = True
        if candidates:
            data["other_matching_chapters"] = candidates
        out = {
            "status": "success",
            "data": data,
            "source": source,
            "license": self.book["citation"],
        }
        wanted = arguments.get("section")
        if not (isinstance(wanted, str) and wanted.strip()):
            data["sections"] = [
                {
                    "heading": n["path"] or "(chapter introduction)",
                    "chars": len(section_text(nodes, i)),
                }
                for i, n in enumerate(nodes)
            ]
            data["next_step"] = (
                "Call again with section=<heading> to read one section "
                "(sub-sections are included)."
            )
            return out
        headings = [n["path"] or "(chapter introduction)" for n in nodes]
        bare = [n["heading"] for n in nodes]
        heading = match_heading(wanted, headings)
        if heading is not None:
            index = headings.index(heading)
        else:
            heading = match_heading(wanted, bare)
            index = bare.index(heading) if heading is not None else None
        if index is None:
            # Procedure, drug and anatomy chapters keep their treatment (or
            # work-up) content under another heading; say which one was used.
            index = first_top_section(nodes, fallback_headings(wanted))
            if index is not None:
                data["section_note"] = (
                    "This chapter has no section matching '%s'; returned '%s', the "
                    "closest section this chapter has." % (wanted, headings[index])
                )
        if index is None:
            return _error(
                "Chapter '%s' has no section matching '%s'." % (row["title"], wanted),
                "section_not_found",
                available_sections=headings,
                source=source,
                license=self.book["citation"],
            )
        heading = headings[index]
        try:
            page = max(int(arguments.get("page") or 1), 1)
        except (TypeError, ValueError):
            page = 1
        frame = dict(
            out, data=dict(data, section=heading, page=1, total_pages=1, text="")
        )
        page_chars = self.max_chars - len(json.dumps(frame)) - 220
        pages = paginate(section_text(nodes, index), max(page_chars, 500))
        page = min(page, len(pages))
        data.update(
            {
                "section": heading,
                "page": page,
                "total_pages": len(pages),
                "text": pages[page - 1],
            }
        )
        if page < len(pages):
            data["text"] += (
                " [... section continues: call again with page=%d of %d ...]"
                % (page + 1, len(pages))
            )
        return out


@register_tool("StatPearlsManagementTool")
class StatPearlsManagementTool(StatPearlsSearchTool):
    """How a condition is managed, from the best-matching StatPearls chapters."""

    CANDIDATES = 10

    def query(self, conn, arguments):
        condition = arguments.get("condition")
        if not isinstance(condition, str) or not condition.strip():
            return _error(
                "condition is required: a disease, injury, procedure or drug "
                "name, e.g. 'intussusception' or 'scaphoid fracture'.",
                "invalid_argument",
            )
        try:
            limit = int(arguments.get("limit") or 2)
        except (TypeError, ValueError):
            return _error(
                "limit must be an integer between 1 and 3.", "invalid_argument"
            )
        limit = min(max(limit, 1), 3)
        match, words = fts_query(condition)
        if not match:
            return _error(
                "condition has no searchable words after removing stopwords.",
                "invalid_argument",
            )
        include_archived = arguments.get("include_archived") is True
        include_evaluation = arguments.get("include_evaluation") is True
        order, _chapters, info_of = self.rank_chapters(
            conn, condition, match, self.CANDIDATES, include_archived
        )
        if not order:
            return _error(
                "No StatPearls chapter matches '%s'." % condition,
                "not_found",
                hint="Try the condition's common name without qualifiers "
                "(e.g. 'ovarian torsion' rather than 'left adnexal "
                "torsion in a 14-year-old').",
                source=self.source_block(),
                license=self.book["citation"],
            )
        data, passed_over = [], []
        titles = {info_of[cid]["title"] for cid in order}
        for chapter_id in order:
            info = info_of[chapter_id]
            # A nursing edition repeats the clinical chapter it is derived from.
            if info["nursing"] and _parent_title(info["title"]) in titles:
                continue
            nodes = chapter_outline(conn, chapter_id)
            index = first_top_section(nodes, MANAGEMENT_HEADINGS)
            if index is None:
                passed_over.append(info["title"])
                continue
            item = {
                "rank": len(data) + 1,
                "chapter_id": chapter_id,
                "title": info["title"],
                "last_updated": info["updated"],
                "url": self.chapter_url(chapter_id),
                "section": nodes[index]["heading"],
                "text": section_text(nodes, index),
            }
            if info["archived"]:
                item["archived"] = True
            shown = {item["section"]}
            evaluation = (
                first_top_section(nodes, EVALUATION_HEADINGS)
                if include_evaluation
                else None
            )
            if evaluation is not None:
                item["evaluation"] = {
                    "heading": nodes[evaluation]["heading"],
                    "text": section_text(nodes, evaluation),
                }
                shown.add(nodes[evaluation]["heading"])
            item["other_sections"] = [
                n["heading"]
                for n in nodes
                if n["level"] == 1 and n["heading"] and n["heading"] not in shown
            ]
            data.append(item)
            if len(data) == limit:
                break
        if not data:
            return _error(
                "The StatPearls chapters matching '%s' have no treatment or management "
                "section." % condition,
                "section_not_found",
                candidates=[info_of[cid]["title"] for cid in order[:8]],
                hint="Read a chapter's sections with StatPearls_get_chapter_section.",
                source=self.source_block(),
                license=self.book["citation"],
            )
        out = {
            "status": "success",
            "data": data,
            "metadata": {
                "condition": condition,
                "query_terms": words,
                "chapter_choice": "best-ranked StatPearls chapters for the condition "
                "(same ranking as StatPearls_search) that have a "
                "treatment or management section",
                "section_preference": list(MANAGEMENT_HEADINGS),
                "returned": len(data),
                "next_step": "Read any section in full with StatPearls_get_chapter_section"
                "(chapter=<chapter_id>, section=<heading>).",
            },
            "source": self.source_block(),
            "license": self.book["citation"],
        }
        if passed_over:
            out["metadata"]["passed_over_without_management_section"] = passed_over
        self._size_texts(out)
        return out

    # Least text worth returning per chapter; below it, fewer chapters are better.
    MIN_TEXT_PER_CHAPTER = 400

    def _size_texts(self, out):
        """Share the output bound across the returned section texts, first
        dropping the lowest-ranked chapters when the bound is too small for
        each to keep some text."""
        data = out["data"]

        def frame_chars():
            texts = [item["text"] for item in data] + [
                item["evaluation"]["text"] for item in data if "evaluation" in item
            ]
            return len(json.dumps(out)) - sum(_escaped_len(text) for text in texts)

        while (
            len(data) > 1
            and frame_chars() + self.MIN_TEXT_PER_CHAPTER * len(data) > self.max_chars
        ):
            data.pop()
            out["metadata"]["returned"] = len(data)
            out["metadata"]["dropped_to_fit_output_bound"] = True
        slots = []
        for item in out["data"]:
            parts = [item] + ([item["evaluation"]] if "evaluation" in item else [])
            for part in parts:
                heading = part.get("section") or part.get("heading")
                hint = (
                    "read the whole section with StatPearls_get_chapter_section"
                    "(chapter='%s', section='%s')" % (item["chapter_id"], heading)
                )
                slots.append((part, "text", hint))
        omitted = share_budget(out, slots, self.max_chars, 160)
        for (part, _key, _hint), lost in zip(slots, omitted):
            if lost:
                part["truncated"] = True
