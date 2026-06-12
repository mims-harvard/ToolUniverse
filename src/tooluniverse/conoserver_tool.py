"""ConoServer conopeptide tools (live, keyless).

ConoServer (https://www.conoserver.org) is the reference database of cone-snail
venom peptides (conotoxins/conopeptides). It exposes no per-record JSON/REST
endpoint; the only structured access is the bulk protein export at
``/download/conoserver_protein.xml.gz`` (~8,500 entries). That XML embeds HTML
named entities (``&alpha;``, ``&beta;`` ...), stray control characters, and the
occasional mojibake, so it is not well-formed and stock ``xml.etree`` rejects it.
This module sanitizes those constructs and parses with lxml's recovering parser.

Two tools:

- ``ConoServerGetConopeptideTool`` (ConoServer_get_conopeptide): one record by ID.
- ``ConoServerSearchConopeptidesTool`` (ConoServer_search_conopeptides): filter by
  name / sequence / pharmacological family / gene superfamily / cysteine
  framework / organism / class.
"""

import gzip
import re
from functools import lru_cache
from html.entities import name2codepoint
from typing import Any, Dict, List, Optional

import requests
from lxml import etree

from .base_tool import BaseTool
from .tool_registry import register_tool

_URL = "https://www.conoserver.org/download/conoserver_protein.xml.gz"
_TIMEOUT = 30
_XML_PREDEFINED = {"amp", "lt", "gt", "quot", "apos"}
_NAMED_ENTITY = re.compile(r"&([a-zA-Z][a-zA-Z0-9]*);")
_BARE_AMP = re.compile(r"&(?!(?:amp|lt|gt|quot|apos|#[0-9]+|#x[0-9a-fA-F]+);)")
_INVALID_XML_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")

# ConoServer's own XML uses these (misspelled) tag names verbatim.
_FRAMEWORK_TAG = "cysteineFramewrok"
_PI_TAG = "isoelecticPoint"


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _sanitize_xml(text: str) -> str:
    """Make ConoServer's not-well-formed XML parseable.

    Converts HTML named entities to their unicode characters (leaving the five
    predefined XML entities intact), escapes any remaining bare ``&``, and drops
    control characters that are illegal in XML 1.0.
    """

    def _replace_named(match: "re.Match[str]") -> str:
        name = match.group(1)
        if name in _XML_PREDEFINED:
            return match.group(0)
        codepoint = name2codepoint.get(name)
        return chr(codepoint) if codepoint is not None else f"&amp;{name};"

    text = _NAMED_ENTITY.sub(_replace_named, text)
    text = _BARE_AMP.sub("&amp;", text)
    return _INVALID_XML_CTRL.sub("", text)


def _text(elem, tag: str) -> Optional[str]:
    value = elem.findtext(tag)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_entry(elem) -> Dict[str, Any]:
    """Turn one ConoServer ``<entry>`` element into a JSON-able dict."""
    modifications: List[Dict[str, Any]] = [
        {
            "position": mod.get("position"),
            "symbol": mod.get("symbol"),
            "name": mod.get("name"),
        }
        for mod in elem.findall("./sequenceModifications/modification")
    ]

    references: List[Dict[str, Any]] = [
        {
            "authors": _text(ref, "authors"),
            "year": _text(ref, "year"),
            "title": _text(ref, "title"),
            "journal": _text(ref, "journal"),
            "volume": _text(ref, "volume"),
            "pages": _text(ref, "pages"),
            "pmid": _text(ref, "pmid"),
        }
        for ref in elem.findall("reference")
    ]

    alt_names = [
        a.text.strip()
        for a in elem.findall("./alternativeNames/altName")
        if a.text and a.text.strip()
    ]

    return {
        "id": _text(elem, "id"),
        "name": _text(elem, "name"),
        "alternative_names": alt_names,
        "class": _text(elem, "class"),
        "gene_superfamily": _text(elem, "geneSuperfamily"),
        "cysteine_framework": _text(elem, _FRAMEWORK_TAG),
        "pharmacological_family": _text(elem, "pharmacologicalFamily"),
        "organism_latin": _text(elem, "organismLatin"),
        "organism_diet": _text(elem, "organismDiet"),
        "organism_region": _text(elem, "organismRegion"),
        "sequence": _text(elem, "sequence"),
        "sequence_modifications": modifications,
        "sequence_evidence": _text(elem, "sequenceEvidence"),
        "average_mass": _text(elem, "averageMass"),
        "monoisotopic_mass": _text(elem, "monoisotopicMass"),
        "isoelectric_point": _text(elem, _PI_TAG),
        "extinction_coefficient": _text(elem, "extinctionCoefficient"),
        "references": references,
    }


@lru_cache(maxsize=1)
def _load_entries() -> List[Dict[str, Any]]:
    """Download, sanitize and parse the bulk ConoServer protein export.

    Cached for the process lifetime (the export changes rarely). Raises on a
    network/parse failure so the failure is never cached.
    """
    resp = requests.get(_URL, timeout=_TIMEOUT)
    resp.raise_for_status()
    xml_text = gzip.decompress(resp.content).decode("utf-8", "replace")
    parser = etree.XMLParser(recover=True, huge_tree=True, resolve_entities=False)
    root = etree.fromstring(_sanitize_xml(xml_text).encode("utf-8"), parser=parser)
    if root is None:
        raise ValueError("ConoServer XML could not be parsed")
    return [_parse_entry(e) for e in root.findall("entry")]


@register_tool(
    "ConoServerGetConopeptideTool",
    config={
        "name": "ConoServer_get_conopeptide",
        "type": "ConoServerGetConopeptideTool",
        "description": (
            "Get a full ConoServer conopeptide (cone-snail venom peptide) record "
            "by its ConoServer protein ID (e.g. P00001). Returns the sequence, "
            "post-translational modifications, cysteine framework, gene "
            "superfamily, pharmacological family, source Conus species/diet/"
            "region, average and monoisotopic mass, pI, extinction coefficient, "
            "and literature references. Data from the keyless ConoServer bulk "
            "protein export (conoserver.org)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "conoserver_id": {
                    "type": "string",
                    "description": (
                        "ConoServer protein ID, e.g. 'P00001' (alpha-conotoxin "
                        "SI, sequence ICCNPACGPKYSCX, from Conus striatus). "
                        "Case-insensitive."
                    ),
                }
            },
            "required": ["conoserver_id"],
        },
    },
)
class ConoServerGetConopeptideTool(BaseTool):
    """Fetch a single ConoServer conopeptide record by ID."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw = arguments.get("conoserver_id")
        if raw is None or not str(raw).strip():
            return _err("conoserver_id is required")
        target = str(raw).strip().upper()

        try:
            entries = _load_entries()
        except Exception as exc:  # network / decompress / parse
            return _err(f"Failed to load ConoServer data: {exc}", url=_URL)

        for entry in entries:
            if (entry.get("id") or "").upper() == target:
                return {
                    "status": "success",
                    "data": entry,
                    "metadata": {
                        "source": "ConoServer",
                        "url": _URL,
                        "id": entry.get("id"),
                        "name": entry.get("name"),
                        "sequence": entry.get("sequence"),
                        "organism_latin": entry.get("organism_latin"),
                    },
                }
        return _err(f"No ConoServer conopeptide found with id {target!r}", url=_URL)


_SUBSTRING_FILTERS = {
    "name": "name",
    "sequence": "sequence",
    "pharmacological_family": "pharmacological_family",
    "gene_superfamily": "gene_superfamily",
    "cysteine_framework": "cysteine_framework",
    "organism": "organism_latin",
    "conopeptide_class": "class",
}


@register_tool(
    "ConoServerSearchConopeptidesTool",
    config={
        "name": "ConoServer_search_conopeptides",
        "type": "ConoServerSearchConopeptidesTool",
        "description": (
            "Search ConoServer conopeptides (cone-snail venom peptides) by one or "
            "more case-insensitive substring filters: name, sequence, "
            "pharmacological_family (e.g. 'alpha conotoxin'), gene_superfamily "
            "(e.g. 'A superfamily'), cysteine_framework (e.g. 'I'), organism "
            "(Conus species, e.g. 'Conus geographus'), or conopeptide_class. "
            "Returns matching records (sequence, modifications, masses, organism, "
            "references). Keyless ConoServer bulk export (conoserver.org)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Peptide name substring."},
                "sequence": {
                    "type": "string",
                    "description": "Amino-acid sequence substring (e.g. 'GCCS').",
                },
                "pharmacological_family": {
                    "type": "string",
                    "description": "e.g. 'alpha conotoxin', 'omega conotoxin'.",
                },
                "gene_superfamily": {
                    "type": "string",
                    "description": "e.g. 'A superfamily', 'O1 superfamily'.",
                },
                "cysteine_framework": {
                    "type": "string",
                    "description": "Cysteine framework, e.g. 'I', 'III', 'VI/VII'.",
                },
                "organism": {
                    "type": "string",
                    "description": "Source Conus species, e.g. 'Conus geographus'.",
                },
                "conopeptide_class": {
                    "type": "string",
                    "description": "Conopeptide class, e.g. 'conotoxin'.",
                },
                "limit": {
                    "type": "integer",
                    "description": "Max records to return (default 25, max 200).",
                },
            },
        },
    },
)
class ConoServerSearchConopeptidesTool(BaseTool):
    """Filter ConoServer conopeptides by substring on indexed fields."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        filters = {}
        for arg_name, field in _SUBSTRING_FILTERS.items():
            value = arguments.get(arg_name)
            if value is not None and str(value).strip():
                filters[field] = str(value).strip().lower()
        if not filters:
            return _err(
                "Provide at least one filter: " + ", ".join(_SUBSTRING_FILTERS.keys())
            )

        limit = arguments.get("limit", 25)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 25
        limit = max(1, min(200, limit))

        try:
            entries = _load_entries()
        except Exception as exc:
            return _err(f"Failed to load ConoServer data: {exc}", url=_URL)

        matched = [
            entry
            for entry in entries
            if all(
                needle in (entry.get(field) or "").lower()
                for field, needle in filters.items()
            )
        ]

        return {
            "status": "success",
            "data": {
                "count": len(matched),
                "returned": min(len(matched), limit),
                "results": matched[:limit],
            },
            "metadata": {
                "source": "ConoServer",
                "url": _URL,
                "filters": {
                    k: value for k in _SUBSTRING_FILTERS if (value := arguments.get(k))
                },
                "total_matched": len(matched),
                "limit": limit,
            },
        }
