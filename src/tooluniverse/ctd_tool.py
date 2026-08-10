"""CTD (Comparative Toxicogenomics Database) tool.

History of this integration, for anyone tempted to "fix" the URL again:

1. CTD's native batchQuery.go now requires an altcha proof-of-work CAPTCHA,
   so direct programmatic access via that endpoint has been blocked for a
   long time.
2. This tool was rewritten to use the NIH-NCATS-Translator-funded RENCI
   Automat mirror at https://automat.renci.org/ctd/ instead.
3. That mirror has since been decommissioned outright: its own registry
   (https://automat.renci.org/registry) no longer lists a "ctd" backend at
   all (confirmed live -- only cam-kp, robokopkg, translatorkg-gandalf,
   icees-kg, ubergraph, cohd, translatorkg, ohd, and robomousekg remain).
   Every request now 404s, not intermittently but always.

Current backend: the BioThings mydisease.info API, which independently
indexes a cached copy of CTD's chemical-disease curation under
`ctd.chemical_related_to_disease` on each disease document. This covers the
chemical<->disease direction only. mychem.info and mygene.info were checked
live and carry no CTD fields at all, so there is currently no free, live
replacement for the gene<->chemical direction; those two tools return an
honest "permanently unavailable" error pointing at DGIdb/OpenTargets instead
of a raw HTTP error, matching the CTD_get_gene_diseases precedent already
established below.
"""

import re
import requests
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

MYDISEASE_BASE = "https://mydisease.info/v1"
HEADERS = {"Accept": "application/json", "User-Agent": "ToolUniverse CTDTool"}
DATA_SOURCE = "mydisease.info (BioThings) cache of CTD chemical-disease curation"

_MESH_ID_RE = re.compile(r"^[CD]\d{6,9}$")  # C=supplementary concept, D=descriptor
_CAS_RN_RE = re.compile(r"^\d{1,7}-\d{2}-\d$")
_MONDO_RE = re.compile(r"^MONDO:\d+$", re.IGNORECASE)

_GENE_CHEMICAL_UNAVAILABLE = (
    "CTD's gene<->chemical data is not available: CTD's native API is CAPTCHA-"
    "blocked for programmatic clients, and the RENCI Automat mirror this tool "
    "used to fall back on has been fully decommissioned (its registry no "
    "longer lists a 'ctd' backend at all). No other free, live source of "
    "CTD's curated gene-chemical interactions was found."
)
_GENE_CHEMICAL_SUGGESTION = (
    "Use DGIdb_get_drug_gene_interactions for drug-gene interactions, or "
    "ChEMBL/OpenTargets tools for target-compound bioactivity data."
)
_CHEMICAL_NAME_SUGGESTION = (
    "CTD's canonical chemical names are MeSH chemical names, so a common "
    "trade name or an informally worded synonym can miss even when the "
    "substance is covered. Retry with the MeSH descriptor/supplementary "
    "concept name, a MeSH chemical ID (e.g. 'D002857', optionally prefixed "
    "'MESH:'), or a CAS Registry Number. ChEBI_get_compound_by_name or "
    "PubChem name lookups can resolve a synonym to a canonical name first."
)


def _term_and_prefix(term: str) -> tuple:
    """Split a 'PREFIX:value' CURIE into (prefix, value); else (None, term)."""
    if ":" in term:
        prefix, _, value = term.partition(":")
        return prefix.upper(), value
    return None, term


def _chemical_match_field(term: str) -> tuple:
    """Pick which mydisease.info nested field to match a chemical term against.

    Returns (field_name, value). CTD's own chemical identifiers are MeSH IDs
    and CAS Registry Numbers; anything else is matched by name.
    """
    prefix, value = _term_and_prefix(term)
    if prefix in ("MESH", "MESH_CHEM"):
        return "mesh_chemical_id", value
    if prefix == "CAS":
        return "cas_registry_number", value
    if _MESH_ID_RE.match(term):
        return "mesh_chemical_id", term
    if _CAS_RN_RE.match(term):
        return "cas_registry_number", term
    return "chemical_name", term


@register_tool("CTDTool")
class CTDTool(BaseTool):
    """Query CTD curated chemical-disease relationships via mydisease.info."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        fields = tool_config.get("fields") or {}
        self.input_type = fields.get("input_type", "chem")
        self.report_type = fields.get("report_type", "genes_curated")
        self.timeout = int(fields.get("timeout", 30))

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"mydisease.info timed out after {self.timeout}s",
                "metadata": {"backend": DATA_SOURCE},
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to mydisease.info. Check network.",
                "metadata": {"backend": DATA_SOURCE},
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"mydisease.info HTTP error: {e.response.status_code}",
                "metadata": {"backend": DATA_SOURCE},
            }
        except Exception as e:  # noqa: BLE001
            return {
                "status": "error",
                "error": f"Unexpected error querying mydisease.info: {e}",
                "metadata": {"backend": DATA_SOURCE},
            }

    # -- internals -----------------------------------------------------------

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        input_terms = (
            arguments.get("input_terms")
            or arguments.get("query")
            or arguments.get("gene_symbol")
            or arguments.get("chemical_name")
            or arguments.get("disease_name")
            or ""
        ).strip()
        if not input_terms:
            return {"status": "error", "error": "input_terms parameter is required"}

        input_type = arguments.get("input_type", self.input_type)
        report_type = arguments.get("report_type", self.report_type)
        metadata = {
            "backend": DATA_SOURCE,
            "input_terms": input_terms,
            "input_type": input_type,
            "report_type": report_type,
        }

        if (input_type, report_type) == ("gene", "diseases_curated"):
            return {
                "status": "error",
                "error": (
                    "Gene->disease relationships are not available from CTD "
                    "via this tool (no live curated CTD source covers this "
                    "direction)."
                ),
                "suggestion": (
                    "Use gather_gene_disease_associations (queries DisGeNET, "
                    "OMIM, OpenTargets, GenCC, and ClinVar in one call and "
                    "cross-references them) or "
                    "OpenTargets_get_diseases_phenotypes_by_target_ensembl "
                    "for gene-disease associations."
                ),
                "metadata": metadata,
            }

        if (input_type, report_type) in (("chem", "genes_curated"), ("gene", "chems_curated")):
            return {
                "status": "error",
                "error": _GENE_CHEMICAL_UNAVAILABLE,
                "suggestion": _GENE_CHEMICAL_SUGGESTION,
                "metadata": metadata,
            }

        if input_type == "chem" and report_type == "diseases_curated":
            return self._chemical_to_diseases(input_terms, metadata)
        if input_type == "disease" and report_type == "chems_curated":
            return self._disease_to_chemicals(input_terms, metadata)

        return {
            "status": "error",
            "error": f"Unsupported query: input_type={input_type!r}, report_type={report_type!r}.",
            "metadata": metadata,
        }

    def _chemical_to_diseases(self, term: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        field, value = _chemical_match_field(term)
        metadata["matched_field"] = f"ctd.chemical_related_to_disease.{field}"
        query = f'ctd.chemical_related_to_disease.{field}:"{_escape(value)}"'
        hits = self._search(query, "mondo.label,ctd.chemical_related_to_disease")
        if hits is None:
            return {
                "status": "error",
                "error": f"'{term}' was not found among CTD's curated chemical-disease associations.",
                "suggestion": _CHEMICAL_NAME_SUGGESTION,
                "metadata": metadata,
            }

        edges = _collect_chem_disease_edges(hits, field, value)
        if edges:
            metadata["total_results"] = len(edges)
            return {"status": "success", "data": edges, "metadata": metadata}

        # The upstream phrase query DID match documents, but no nested entry
        # carries `value` verbatim, so the strict post-filter above threw every
        # fetched row away. Returning `success` with `data: []` here would be a
        # lie the caller cannot distinguish from "CTD curates nothing for this
        # chemical" -- exactly the failure seen for "chromium, hexavalent",
        # which matches 55 documents whose entries are all named
        # "chromium hexavalent ion". Elasticsearch matched the caller's phrase
        # as a sub-phrase of the stored value, so reconstruct which stored
        # values could have produced the match and surface them.
        candidates = _phrase_candidates(hits, field, value)
        if len(candidates) == 1:
            resolved = candidates[0]
            edges = _collect_chem_disease_edges(hits, field, resolved)
            if edges:
                key = (
                    "resolved_chemical_name"
                    if field == "chemical_name"
                    else "resolved_match_value"
                )
                metadata[key] = resolved
                metadata["normalization_note"] = (
                    f"No CTD entry is named exactly '{value}'. All "
                    f"{len(hits)} matching CTD document(s) use the single "
                    f"canonical value '{resolved}' for "
                    f"{metadata['matched_field']}, so that value was used "
                    "instead. Re-run with it for an unambiguous query."
                )
                metadata["total_results"] = len(edges)
                return {"status": "success", "data": edges, "metadata": metadata}

        metadata["total_results"] = 0
        if candidates:
            metadata["candidates"] = candidates
            shown = ", ".join(repr(c) for c in candidates[:10])
            extra = "" if len(candidates) <= 10 else f", and {len(candidates) - 10} more"
            return {
                "status": "error",
                "error": (
                    f"'{term}' is not a canonical CTD value for "
                    f"{metadata['matched_field']}. It matched {len(hits)} CTD "
                    f"document(s), but those records are curated under "
                    f"{len(candidates)} different values: {shown}{extra}. "
                    "Re-run with exactly one of these so the result is "
                    "unambiguous."
                ),
                "suggestion": _CHEMICAL_NAME_SUGGESTION,
                "metadata": metadata,
            }
        return {
            "status": "error",
            "error": (
                f"'{term}' matched {len(hits)} CTD document(s) upstream, but "
                f"none of their curated entries carry '{value}' in {field}, "
                "and no canonical CTD value could be derived from them. The "
                "upstream match was a partial text match rather than a real "
                "chemical identity, so no association can be reported."
            ),
            "suggestion": _CHEMICAL_NAME_SUGGESTION,
            "metadata": metadata,
        }

    def _disease_to_chemicals(self, term: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        mondo_id, disease_label = self._resolve_disease(term)
        if not mondo_id:
            return {
                "status": "error",
                "error": f"'{term}' could not be resolved to a disease known to CTD/MONDO.",
                "metadata": metadata,
            }
        metadata["resolved_disease"] = {"mondo_id": mondo_id, "label": disease_label}
        resp = requests.get(
            f"{MYDISEASE_BASE}/disease/{mondo_id}",
            params={"fields": "ctd.chemical_related_to_disease"},
            headers=HEADERS,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        doc = resp.json()
        entries = _ctd_disease_entries(doc)
        edges = [_format_disease_chem_edge(e, mondo_id, disease_label) for e in entries]
        metadata["total_results"] = len(edges)
        return {"status": "success", "data": edges, "metadata": metadata}

    def _resolve_disease(self, term: str) -> tuple:
        """Resolve a disease name, MONDO CURIE, or MeSH ID to (mondo_id, label)."""
        prefix, value = _term_and_prefix(term)
        if _MONDO_RE.match(term):
            mondo_id = term.upper()
        elif prefix == "MESH" or _MESH_ID_RE.match(term):
            mesh_id = value if prefix else term
            hits = self._search(f'mondo.xrefs.mesh:"{_escape(mesh_id)}"', "mondo.label")
            if not hits:
                return None, None
            return hits[0].get("_id"), (hits[0].get("mondo") or {}).get("label")
        else:
            # Plain free-text search over the whole mydisease.info index also
            # matches DOID/OMIM/etc. documents that carry no `mondo` block at
            # all (confirmed live for "asthma" -- the top two hits were DOID
            # documents with no ctd data). Restricting the match to the
            # `mondo.label` field keeps results anchored to MONDO documents,
            # which is what `/v1/disease/<id>` and the ctd cross-reference
            # both expect.
            hits = self._search(f'mondo.label:"{_escape(term)}"', "mondo.label", size=1)
            if not hits:
                return None, None
            return hits[0].get("_id"), (hits[0].get("mondo") or {}).get("label")

        resp = requests.get(
            f"{MYDISEASE_BASE}/disease/{mondo_id}",
            params={"fields": "mondo.label"},
            headers=HEADERS,
            timeout=self.timeout,
        )
        if resp.status_code == 404:
            return None, None
        resp.raise_for_status()
        doc = resp.json()
        return mondo_id, (doc.get("mondo") or {}).get("label")

    def _search(self, query: str, fields: str, size: int = 200) -> Optional[List[Dict[str, Any]]]:
        resp = requests.get(
            f"{MYDISEASE_BASE}/query",
            params={"q": query, "fields": fields, "size": size},
            headers=HEADERS,
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        hits = data.get("hits")
        if not hits:
            return None
        return hits


def _escape(value: str) -> str:
    return value.replace('"', "").replace("\\", "")


def _ctd_disease_entries(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten a mydisease.info document's chemical_related_to_disease entries.

    BioThings occasionally merges more than one source record onto the same
    disease document, in which case `ctd` itself is a list of sub-documents
    instead of a single dict -- confirmed live for MONDO:0002525. Handle both
    shapes and always return a flat list of entry dicts.
    """
    ctd_field = doc.get("ctd") or []
    ctd_docs = ctd_field if isinstance(ctd_field, list) else [ctd_field]
    entries: List[Dict[str, Any]] = []
    for ctd_doc in ctd_docs:
        if not isinstance(ctd_doc, dict):
            continue
        related = ctd_doc.get("chemical_related_to_disease") or []
        entries.extend(related if isinstance(related, list) else [related])
    return entries


def _pubmed_ids(entry: Dict[str, Any]) -> Any:
    """CTD entries usually carry one PMID but sometimes a list of several."""
    pubmed = entry.get("pubmed")
    if isinstance(pubmed, list):
        return pubmed
    return [pubmed] if pubmed else []


def _entry_values(entry: Dict[str, Any], field: str) -> List[str]:
    """Every non-empty string value an entry carries for `field`.

    BioThings sometimes collapses repeated sub-fields into a list, so a single
    entry's `chemical_name` may be either a scalar or a list of scalars.
    """
    raw = entry.get(field)
    if raw is None:
        return []
    values = raw if isinstance(raw, list) else [raw]
    return [str(v).strip() for v in values if v is not None and str(v).strip()]


def _entry_matches(entry: Dict[str, Any], field: str, value: str) -> bool:
    """Strict, case-insensitive full-string match -- the preferred match.

    Deliberately NOT a substring match: `"chromium"` must keep meaning the CTD
    chemical named `Chromium` and must never silently widen to
    `"chromium hexavalent ion"`. Callers that find zero strict matches against
    a non-empty hit set go through `_phrase_candidates` instead, which
    discloses the widening.
    """
    wanted = value.strip().lower()
    return any(v.lower() == wanted for v in _entry_values(entry, field))


_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _tokens(value: str) -> List[str]:
    return _TOKEN_RE.findall(str(value).lower())


def _is_subphrase(needle: List[str], haystack: List[str]) -> bool:
    """True if `needle` occurs as a contiguous run of tokens within `haystack`."""
    if not needle or len(needle) > len(haystack):
        return False
    return any(
        haystack[i : i + len(needle)] == needle
        for i in range(len(haystack) - len(needle) + 1)
    )


def _phrase_candidates(
    hits: List[Dict[str, Any]], field: str, value: str
) -> List[str]:
    """Distinct stored values that could have produced the upstream match.

    mydisease.info runs the tool's `field:"<value>"` query as an Elasticsearch
    phrase query over an analysed text field, so it matches whenever the
    caller's tokens appear as a contiguous run inside the stored value --
    `"chromium, hexavalent"` matches the stored `"chromium hexavalent ion"`.
    Reconstructing that same sub-phrase rule locally tells us which stored
    values the caller actually reached, without inventing a synonym table and
    without loosening the strict match in `_entry_matches`. Order of first
    appearance is preserved and comparison is case-insensitive.
    """
    needle = _tokens(value)
    found: Dict[str, str] = {}
    for hit in hits:
        for entry in _ctd_disease_entries(hit):
            for text in _entry_values(entry, field):
                key = text.lower()
                if key in found:
                    continue
                if _is_subphrase(needle, _tokens(text)):
                    found[key] = text
    return list(found.values())


def _collect_chem_disease_edges(
    hits: List[Dict[str, Any]], field: str, value: str
) -> List[Dict[str, Any]]:
    """Format every nested CTD entry across `hits` that strictly matches `value`."""
    edges: List[Dict[str, Any]] = []
    for hit in hits:
        disease_id = hit.get("_id")
        disease_name = (hit.get("mondo") or {}).get("label")
        for entry in _ctd_disease_entries(hit):
            if not _entry_matches(entry, field, value):
                continue
            edges.append(_format_chem_disease_edge(entry, disease_id, disease_name))
    return edges


_EVIDENCE_TO_PREDICATE = {
    "marker/mechanism": "biolink:contributes_to",
    "therapeutic": "biolink:treats",
}


def _format_chem_disease_edge(
    entry: Dict[str, Any], disease_id: Optional[str], disease_name: Optional[str]
) -> Dict[str, Any]:
    mesh_chem = entry.get("mesh_chemical_id")
    cas = entry.get("cas_registry_number")
    source_id = f"MESH:{mesh_chem}" if mesh_chem else (f"CAS:{cas}" if cas else None)
    direct_evidence = entry.get("direct_evidence")
    return {
        "source_id": source_id,
        "source_name": entry.get("chemical_name"),
        "target_id": disease_id,
        "target_name": disease_name,
        "predicate": None,
        "qualified_predicate": _EVIDENCE_TO_PREDICATE.get(direct_evidence),
        "object_direction_qualifier": None,
        "knowledge_level": "knowledge_assertion",
        "agent_type": "manual_agent",
        "primary_knowledge_source": "infores:ctd",
        "direct_evidence": direct_evidence,
        "pubmed_ids": _pubmed_ids(entry),
    }


def _format_disease_chem_edge(
    entry: Dict[str, Any], disease_id: str, disease_name: Optional[str]
) -> Dict[str, Any]:
    mesh_chem = entry.get("mesh_chemical_id")
    cas = entry.get("cas_registry_number")
    target_id = f"MESH:{mesh_chem}" if mesh_chem else (f"CAS:{cas}" if cas else None)
    direct_evidence = entry.get("direct_evidence")
    return {
        "source_id": disease_id,
        "source_name": disease_name,
        "target_id": target_id,
        "target_name": entry.get("chemical_name"),
        "predicate": None,
        "qualified_predicate": _EVIDENCE_TO_PREDICATE.get(direct_evidence),
        "object_direction_qualifier": None,
        "knowledge_level": "knowledge_assertion",
        "agent_type": "manual_agent",
        "primary_knowledge_source": "infores:ctd",
        "direct_evidence": direct_evidence,
        "pubmed_ids": _pubmed_ids(entry),
    }
