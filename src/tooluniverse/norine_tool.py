"""Norine non-ribosomal peptide (NRP) lookup tool (live REST, keyless).

Norine (https://bioinfo.cristal.univ-lille.fr/norine/, Bonsai Bioinformatics,
Universite de Lille) is the reference knowledgebase for non-ribosomal peptides
(NRPs): bacterial/fungal secondary-metabolite peptides assembled by NRP
synthetases rather than the ribosome. These molecules (e.g. tyrocidine,
microcystin, surfactin) frequently contain non-proteinogenic monomers
(D-amino acids, Orn, ornithine, fatty-acid tails) and are cyclic or branched,
so they are NOT covered by ribosomal / therapeutic / MHC peptide resources.

``NorineGetPeptideTool`` (Norine_get_peptide) looks a record up either by
peptide name (GET /norine/rest/name/json/{name}) or by Norine ID
(GET /norine/rest/id/json/{id}, zero-padded to 5 digits). The two routes wrap
their results differently (name route: top-level ``peptides`` list; id route:
``norine.peptide`` list); this tool normalizes both into a single ``peptides``
list and surfaces the count plus first-record general/structure fields.

The public REST API is keyless. The explicit ``/json/`` path segment is
required to get ``application/json`` (the default routes return HTML).
"""

from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://bioinfo.cristal.univ-lille.fr/norine/rest"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _normalize_id(raw: Any) -> Optional[str]:
    """Coerce a Norine id to a zero-padded 5-digit string.

    Accepts 123, '123', '00123', 'NOR00123' -> '00123'. Returns None if no
    digits are present.
    """
    digits = "".join(ch for ch in str(raw) if ch.isdigit())
    if not digits:
        return None
    # Strip leading zeros then re-pad so 'NOR00123' and 123 both -> '00123'.
    digits = digits.lstrip("0") or "0"
    return digits.zfill(5)


def _extract_peptides(payload: Any) -> Optional[List[Any]]:
    """Normalize name-route ('peptides') vs id-route ('norine.peptide')
    wrapping into one flat list. Returns None if the shape is unrecognized.
    """
    if not isinstance(payload, dict):
        return None
    if isinstance(payload.get("peptides"), list):
        return payload["peptides"]
    norine = payload.get("norine")
    if isinstance(norine, dict) and isinstance(norine.get("peptide"), list):
        return norine["peptide"]
    return None


def _first_record_summary(peptides: List[Any]) -> Dict[str, Any]:
    """Surface general/structure fields of the first record for metadata."""
    if not peptides or not isinstance(peptides[0], dict):
        return {}
    first = peptides[0]
    general = first.get("general")
    structure = first.get("structure")
    if not isinstance(general, dict):
        general = {}
    if not isinstance(structure, dict):
        structure = {}
    return {
        "id": general.get("id"),
        "name": general.get("name"),
        "family": general.get("family"),
        "category": general.get("category"),
        "formula": general.get("formula"),
        "mw": general.get("mw"),
        "activity": general.get("activity"),
        "structure_type": structure.get("type"),
        "structure_size": structure.get("size"),
        "composition": structure.get("composition"),
    }


@register_tool(
    "NorineGetPeptideTool",
    config={
        "name": "Norine_get_peptide",
        "type": "NorineGetPeptideTool",
        "description": (
            "Programmatic keyless lookup of non-ribosomal peptide (NRP) records "
            "from Norine (Nonribosomal Peptides Database, Universite de Lille) "
            "by peptide name or Norine ID. Returns the curated structure "
            "(monomer composition, cyclic/linear type, monomer graph), "
            "molecular formula/weight, SMILES, biological activity, source "
            "organism (taxId), and literature references (PMIDs). NRPs are "
            "bacterial/fungal peptides made by NRP synthetases (not the "
            "ribosome) and often contain non-proteinogenic monomers and "
            "cyclic/branched backbones (e.g. tyrocidine, microcystin, "
            "surfactin), so they are NOT covered by ribosomal/therapeutic/MHC "
            "peptide resources. Provide 'name' (e.g. 'tyrocidine' -> 4 records) "
            "OR 'norine_id' (e.g. '00123', zero-padded to 5 digits). The name "
            "route may return several peptides of a family; the id route "
            "returns one. Keyless Norine REST API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "name": {
                    "type": ["string", "null"],
                    "description": (
                        "Peptide (or family) name to look up. Example: "
                        "'tyrocidine' returns 4 records (tyrocidine A-D). "
                        "Case-insensitive partial-family matching is handled by "
                        "Norine. Provide either 'name' or 'norine_id', not both."
                    ),
                },
                "norine_id": {
                    "type": ["string", "integer", "null"],
                    "description": (
                        "Norine peptide ID. Accepts a bare number, a "
                        "zero-padded 5-digit string, or a 'NOR00123'-style ID "
                        "(digits are extracted and zero-padded to 5 digits). "
                        "Example: '00123' (microcystin family, category PK-NRP, "
                        "organism Anabaena, taxId 1163). Provide either 'name' "
                        "or 'norine_id', not both."
                    ),
                },
            },
            "required": [],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful Norine peptide lookup.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "properties": {
                                "peptides": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "cite": {"type": "array"},
                                            "general": {
                                                "type": "object",
                                                "properties": {
                                                    "id": {"type": "string"},
                                                    "name": {"type": "string"},
                                                    "family": {"type": "string"},
                                                    "syno": {"type": "array"},
                                                    "category": {"type": "string"},
                                                    "formula": {"type": "string"},
                                                    "mw": {
                                                        "type": ["string", "number"]
                                                    },
                                                    "comment": {"type": "string"},
                                                    "status": {"type": "string"},
                                                    "activity": {"type": "array"},
                                                    "source": {"type": "string"},
                                                    "doi": {"type": "string"},
                                                },
                                            },
                                            "structure": {
                                                "type": "object",
                                                "properties": {
                                                    "type": {"type": "string"},
                                                    "size": {
                                                        "type": ["integer", "string"]
                                                    },
                                                    "composition": {"type": "string"},
                                                    "graph": {"type": "string"},
                                                    "smiles": {"type": "string"},
                                                },
                                            },
                                            "organism": {"type": "array"},
                                            "reference": {"type": "array"},
                                        },
                                    },
                                    "description": (
                                        "Normalized list of Norine NRP records "
                                        "(name route 'peptides' and id route "
                                        "'norine.peptide' merged here)."
                                    ),
                                }
                            },
                            "required": ["peptides"],
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "lookup_mode": {"type": "string"},
                                "query": {"type": "string"},
                                "count": {"type": "integer"},
                                "first_record": {"type": "object"},
                            },
                        },
                    },
                    "required": ["status", "data", "metadata"],
                },
                {
                    "type": "object",
                    "description": "Error result.",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "error": {"type": "string"},
                        "url": {"type": "string"},
                        "response_snippet": {"type": "string"},
                    },
                    "required": ["status", "error"],
                },
            ]
        },
        "test_examples": [
            {"name": "tyrocidine"},
            {"norine_id": "00123"},
        ],
        "label": [
            "Norine",
            "Non-ribosomal Peptide",
            "NRP",
            "Cyclic Peptide",
            "Peptide",
        ],
        "metadata": {
            "tags": [
                "Norine",
                "non-ribosomal peptide",
                "NRP",
                "cyclic peptide",
                "monomer",
                "SMILES",
                "peptide",
            ],
            "estimated_execution_time": "1-10 seconds",
        },
    },
)
class NorineGetPeptideTool(BaseTool):
    """Look up a Norine NRP record by peptide name or Norine ID."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        name = arguments.get("name")
        if isinstance(name, str):
            name = name.strip() or None

        raw_id = arguments.get("norine_id")
        if isinstance(raw_id, str):
            raw_id = raw_id.strip() or None

        has_name = name is not None
        has_id = raw_id is not None

        if has_name and has_id:
            return _err("Provide either 'name' or 'norine_id', not both.")
        if not has_name and not has_id:
            return _err("One of 'name' or 'norine_id' is required.")

        if has_id:
            norine_id = _normalize_id(raw_id)
            if norine_id is None:
                return _err(f"Invalid norine_id: {raw_id!r} (no numeric ID found).")
            lookup_mode = "id"
            query = norine_id
            url = f"{_BASE_URL}/id/json/{norine_id}"
        else:
            lookup_mode = "name"
            query = name
            url = f"{_BASE_URL}/name/json/{requests.utils.quote(name, safe='')}"

        try:
            resp = requests.get(url, headers=_HEADERS, timeout=_TIMEOUT)
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to Norine failed: {exc}", url=url)

        if resp.status_code == 404:
            return _err(f"No Norine record found ({lookup_mode}={query}).", url=url)
        if resp.status_code != 200:
            return _err(
                f"Norine returned HTTP {resp.status_code}",
                url=url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "Norine returned a non-JSON response (ensure the /json/ route "
                "is used; default routes return HTML).",
                url=url,
                response_snippet=(resp.text or "")[:200],
            )

        peptides = _extract_peptides(payload)
        if peptides is None:
            return _err(
                "Unexpected Norine response shape (no 'peptides' or "
                "'norine.peptide' list found).",
                url=url,
                response_snippet=(resp.text or "")[:200],
            )

        # Both routes return HTTP 200 with an empty list when nothing matches.
        if not peptides:
            return _err(f"No Norine peptide found ({lookup_mode}={query}).", url=url)

        return {
            "status": "success",
            "data": {"peptides": peptides},
            "metadata": {
                "source": "Norine (Nonribosomal Peptides Database, "
                "Universite de Lille)",
                "url": url,
                "lookup_mode": lookup_mode,
                "query": str(query),
                "count": len(peptides),
                "first_record": _first_record_summary(peptides),
            },
        }
