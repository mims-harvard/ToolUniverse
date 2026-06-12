"""AMPSphere single-AMP record + sequence-match tools (live REST, keyless).

AMPSphere (Big Data Biology Lab) is a global survey of antimicrobial peptides
(AMPs) computationally predicted from publicly available metagenomes and
metaproteomes — 863,498 non-redundant AMPs grouped into SPHERE families. The
public API at https://ampsphere-api.big-data-biology.org is keyless (no login,
no token) and returns JSON.

This module adds two tools that complement the catalog-browse / family tools in
``ampsphere_tool.py`` (the disjoint single-record and exact-match capabilities):

- ``AMPSphereGetAmpTool`` (AMPSphere_get_amp): full record for one AMP
  accession (sequence, family, physicochemical properties, QC flags, predicted
  secondary structure, gene/sample provenance) via /v1/amps/{accession}.
- ``AMPSphereSequenceMatchTool`` (AMPSphere_sequence_match): exact-sequence
  membership test — does this peptide already exist in AMPSphere? — via
  /v1/search/sequence-match.

API behavior (verified live): an invalid AMP accession returns HTTP 500 with
body ``{"detail": "invalid accession received."}``; the sequence-match endpoint
is case-sensitive (lowercase input misses), so the query is uppercased and
whitespace-stripped, and a non-member returns ``{"query": ..., "result": null}``.
"""

from typing import Any, Dict, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://ampsphere-api.big-data-biology.org/v1"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}
_SOURCE = "AMPSphere (Big Data Biology Lab, ampsphere.big-data-biology.org)"


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _detail(resp: requests.Response) -> str:
    """Extract the API's JSON ``detail`` message if present, else raw text."""
    try:
        body = resp.json()
        if isinstance(body, dict) and body.get("detail"):
            return str(body["detail"])[:200]
    except ValueError:
        pass
    return (resp.text or "")[:200]


def _request(
    url: str, params: Optional[Dict[str, Any]] = None
) -> Tuple[Optional[Any], Optional[Dict[str, Any]]]:
    """GET helper returning (payload, error_dict). Exactly one is non-None."""
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        return None, _err(f"Request to AMPSphere failed: {exc}", url=url)

    if resp.status_code != 200:
        detail = _detail(resp)
        # AMPSphere signals a missing record with an "invalid accession" body
        # (HTTP 400/500); surface that as a clean not-found error.
        if "invalid accession" in detail.lower():
            return None, _err(
                "AMPSphere has no record for the requested accession.",
                url=resp.url,
                response_snippet=detail,
            )
        return None, _err(
            f"AMPSphere returned HTTP {resp.status_code}",
            url=resp.url,
            response_snippet=detail,
        )

    try:
        return resp.json(), None
    except ValueError:
        return None, _err(
            "AMPSphere returned a non-JSON response",
            url=resp.url,
            response_snippet=(resp.text or "")[:200],
        )


@register_tool(
    "AMPSphereGetAmpTool",
    config={
        "name": "AMPSphere_get_amp",
        "type": "AMPSphereGetAmpTool",
        "description": (
            "Get the full AMPSphere record for one antimicrobial peptide (AMP) "
            "by accession. AMPSphere (Big Data Biology Lab) is a global survey "
            "of 863,498 AMPs predicted from metagenomes/metaproteomes. Returns "
            "the amino-acid sequence, SPHERE family, length, physicochemical "
            "properties (molecular_weight, isoelectric_point, charge, "
            "aromaticity, instability_index, gravy), quality-control flags "
            "(Antifam, RNAcode, metaproteomes, metatranscriptomes, coordinates; "
            "each Passed/Failed/Not tested), predicted secondary_structure "
            "(helix/turn/sheet fractions), and a metadata.data[] array of "
            "gene/sample provenance rows (GMSC gene accession, gene sequence, "
            "sample, habitat, microbial source, geography). Keyless public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": (
                        "AMPSphere AMP accession of the form 'AMP10.XXX_XXX'. "
                        "Example: 'AMP10.000_000' (sequence "
                        "KKVKSIFKKALAMMGENEVKAWGIGIK, family SPHERE-III.001_493)."
                    ),
                }
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful AMP lookup.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "description": "Full AMPSphere AMP record.",
                            "properties": {
                                "accession": {"type": "string"},
                                "sequence": {"type": "string"},
                                "family": {"type": ["string", "null"]},
                                "length": {"type": ["integer", "null"]},
                                "molecular_weight": {"type": ["number", "null"]},
                                "isoelectric_point": {"type": ["number", "null"]},
                                "charge": {"type": ["number", "null"]},
                                "aromaticity": {"type": ["number", "null"]},
                                "instability_index": {"type": ["number", "null"]},
                                "gravy": {"type": ["number", "null"]},
                                "Antifam": {"type": ["string", "null"]},
                                "RNAcode": {"type": ["string", "null"]},
                                "metaproteomes": {"type": ["string", "null"]},
                                "metatranscriptomes": {"type": ["string", "null"]},
                                "coordinates": {"type": ["string", "null"]},
                                "num_genes": {"type": ["integer", "null"]},
                                "secondary_structure": {
                                    "type": ["object", "null"],
                                    "properties": {
                                        "helix": {"type": ["number", "null"]},
                                        "turn": {"type": ["number", "null"]},
                                        "sheet": {"type": ["number", "null"]},
                                    },
                                },
                                "metadata": {"type": ["object", "null"]},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "accession": {"type": "string"},
                                "family": {"type": ["string", "null"]},
                                "length": {"type": ["integer", "null"]},
                                "gene_count": {"type": "integer"},
                            },
                        },
                    },
                    "required": ["status", "data"],
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
            {"accession": "AMP10.000_000"},
            {"accession": "AMP10.000_001"},
        ],
        "label": ["AMPSphere", "Antimicrobial Peptide", "AMP", "Metagenome", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "metagenome",
                "metaproteome",
                "physicochemical",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereGetAmpTool(BaseTool):
    """Fetch a single AMPSphere AMP record by accession."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw = (arguments or {}).get("accession")
        if raw is None or str(raw).strip() == "":
            return _err("accession is required (e.g. 'AMP10.000_000').")
        accession = str(raw).strip()

        url = f"{_BASE_URL}/amps/{accession}"
        payload, error = _request(url)
        if error is not None:
            return error
        if not isinstance(payload, dict) or not payload.get("accession"):
            return _err(f"No AMPSphere record for accession {accession!r}.", url=url)

        meta = payload.get("metadata")
        gene_rows = meta.get("data") if isinstance(meta, dict) else None

        return {
            "status": "success",
            "data": payload,
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": payload.get("accession"),
                "family": payload.get("family"),
                "length": payload.get("length"),
                "gene_count": len(gene_rows) if isinstance(gene_rows, list) else 0,
            },
        }


@register_tool(
    "AMPSphereSequenceMatchTool",
    config={
        "name": "AMPSphere_sequence_match",
        "type": "AMPSphereSequenceMatchTool",
        "description": (
            "Check whether an exact amino-acid sequence already exists in "
            "AMPSphere (the global survey of 863,498 metagenomic antimicrobial "
            "peptides) and, if so, return its AMPSphere accession. This is an "
            "exact-match membership test, not a homology search (for homology "
            "use AMPSphere's /search/mmseqs or /search/hmmer endpoints). "
            "Returns {query, result, matched}: result is the AMPSphere "
            "accession (e.g. 'AMP10.000_000') when the sequence is a catalog "
            "member, or null when it is not present. The match is case-"
            "insensitive here (input is uppercased before querying). Keyless "
            "public API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "Amino-acid sequence (single-letter code) to test for "
                        "exact membership. Example: "
                        "'KKVKSIFKKALAMMGENEVKAWGIGIK' -> AMP10.000_000."
                    ),
                }
            },
            "required": ["query"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful exact-match test.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "properties": {
                                "query": {"type": "string"},
                                "result": {"type": ["string", "null"]},
                                "matched": {"type": "boolean"},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "accession": {"type": ["string", "null"]},
                            },
                        },
                    },
                    "required": ["status", "data"],
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
            {"query": "KKVKSIFKKALAMMGENEVKAWGIGIK"},
            {"query": "ACDEFGHIKLMNPQRSTVWYACDEFG"},
        ],
        "label": ["AMPSphere", "Antimicrobial Peptide", "AMP", "Sequence", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "sequence match",
                "exact match",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereSequenceMatchTool(BaseTool):
    """Exact-sequence membership test against the AMPSphere catalog."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        raw = (arguments or {}).get("query")
        if raw is None or str(raw).strip() == "":
            return _err("query (an amino-acid sequence) is required.")
        # The endpoint is case-sensitive and rejects internal whitespace; clean
        # the input to a contiguous uppercase residue string.
        query = "".join(str(raw).split()).upper()
        if not query:
            return _err("query contains no sequence characters.")

        url = f"{_BASE_URL}/search/sequence-match"
        payload, error = _request(url, {"query": query})
        if error is not None:
            return error
        if not isinstance(payload, dict):
            return _err("Unexpected AMPSphere response shape", url=url)

        result = payload.get("result")
        return {
            "status": "success",
            "data": {
                "query": payload.get("query", query),
                "result": result,
                "matched": bool(result),
            },
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": result,
            },
        }
