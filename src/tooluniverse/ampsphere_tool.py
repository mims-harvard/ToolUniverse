"""AMPSphere antimicrobial-peptide catalogue tools (live REST, keyless).

AMPSphere is the Global Microbial smORF Catalogue of antimicrobial peptides
(AMPs) from the Big Data Biology Lab (2024 Nature paper), containing 863,498
prokaryotic smORF AMPs predicted from metagenomes and genomes. The public REST
API at https://ampsphere-api.big-data-biology.org is keyless (no login, no
API key, no CAPTCHA) and returns clean JSON.

Tools (all keyless GET wrappers):

- ``AMPSphereSearchAmpsTool`` (AMPSphere_search_amps): filter/search the
  catalogue (/v1/amps) by habitat, family, microbial source, peptide length,
  molecular weight, isoelectric point, charge and quality flags, with
  pagination. The companion /v1/all_available_options endpoint enumerates the
  valid filter values and is exposed via the ``list_options`` flag.
- ``AMPSphereGetFamilyTool`` (AMPSphere_get_family): full detail for a SPHERE
  protein family (/v1/families/{accession}) — consensus sequence, member list,
  per-member feature statistics, geo/habitat/source distributions, and the
  family's download URLs (alignment, sequences, HMM, tree).
- ``AMPSphereGetAmpDistributionsTool`` (AMPSphere_get_amp_distributions):
  per-AMP biogeography / habitat / microbial-source distribution
  (/v1/amps/{accession}/distributions).
- ``AMPSphereGetAmpFeaturesTool`` (AMPSphere_get_amp_features): structured
  physicochemical + secondary-structure profile for one AMP
  (/v1/amps/{accession}/features).

Interval filters (pep_length, mw, pI, charge) use a comma-separated
``min,max`` string (e.g. ``8,20``). Error responses from the API are HTTP 400
with a JSON ``{"detail": ...}`` body (e.g. an invalid accession).
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://ampsphere-api.big-data-biology.org/v1"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}
_SOURCE = "AMPSphere (Global Microbial smORF Catalogue)"


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _detail_snippet(resp: requests.Response) -> str:
    """Extract the API's JSON ``detail`` message if present, else raw text."""
    try:
        body = resp.json()
        if isinstance(body, dict) and "detail" in body:
            return str(body["detail"])
    except ValueError:
        pass
    return (resp.text or "")[:200]


def _require_accession(arguments: Dict[str, Any], example: str):
    """Validate the 'accession' arg. Returns (accession, error); one is None."""
    raw = (arguments or {}).get("accession")
    if raw is None or not str(raw).strip():
        return None, _err(f"accession is required (e.g. '{example}')")
    return str(raw).strip(), None


def _get(path: str, params: Dict[str, Any] | None = None):
    """GET a JSON resource. Returns (payload, error_dict). One is always None."""
    url = f"{_BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params, headers=_HEADERS, timeout=_TIMEOUT)
    except requests.exceptions.RequestException as exc:
        return None, _err(f"Request to AMPSphere failed: {exc}", url=url)

    if resp.status_code != 200:
        detail = _detail_snippet(resp)
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
    "AMPSphereSearchAmpsTool",
    config={
        "name": "AMPSphere_search_amps",
        "type": "AMPSphereSearchAmpsTool",
        "description": (
            "Filter/search the AMPSphere catalogue (863,498 prokaryotic smORF "
            "antimicrobial peptides from the 2024 Global Microbial smORF "
            "Catalogue, Big Data Biology Lab) by habitat, SPHERE family, "
            "microbial source, peptide length, molecular weight, isoelectric "
            "point, charge, and quality-control flags (exp_evidence, antifam, "
            "RNAcode, coordinates), with pagination. Returns a paginated list of "
            "AMPs, each with its accession, amino-acid sequence, physicochemical "
            "properties (length, MW, pI, charge, aromaticity, instability index, "
            "GRAVY) and quality flags. Interval filters use a 'min,max' string "
            "(e.g. pep_length_interval='8,20'). Set list_options=true to instead "
            "return the valid filter values (habitats, microbial sources, "
            "quality labels, and min/max ranges) from /v1/all_available_options. "
            "Keyless AMPSphere REST API."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "list_options": {
                    "type": "boolean",
                    "description": (
                        "If true, ignore all other filters and return the valid "
                        "filter enumerations from /v1/all_available_options "
                        "(quality labels, habitat list, microbial_source list, "
                        "and min/max ranges for pep_length, molecular_weight, "
                        "isoelectric_point, charge_at_pH_7). Use this first to "
                        "discover valid habitat / microbial_source values."
                    ),
                },
                "habitat": {
                    "type": "string",
                    "description": (
                        "Environmental habitat filter, e.g. 'human gut', 'soil', "
                        "'marine'. Must match an AMPSphere habitat label (see "
                        "list_options)."
                    ),
                },
                "family": {
                    "type": "string",
                    "description": (
                        "SPHERE family accession filter, e.g. "
                        "'SPHERE-III.001_396'. Returns the AMPs in that family."
                    ),
                },
                "microbial_source": {
                    "type": "string",
                    "description": (
                        "Microbial taxonomic source filter (GTDB-style name), "
                        "e.g. 'Faecalibacterium'. See list_options for valid "
                        "values."
                    ),
                },
                "exp_evidence": {
                    "type": "string",
                    "description": (
                        "Experimental-evidence quality flag filter: 'Passed', "
                        "'Failed', or 'Not tested'."
                    ),
                },
                "antifam": {
                    "type": "string",
                    "description": (
                        "Antifam quality flag filter: 'Passed', 'Failed', or "
                        "'Not tested' (Antifam = not a spurious/false ORF)."
                    ),
                },
                "RNAcode": {
                    "type": "string",
                    "description": (
                        "RNAcode coding-potential quality flag filter: 'Passed', "
                        "'Failed', or 'Not tested'."
                    ),
                },
                "coordinates": {
                    "type": "string",
                    "description": (
                        "Genomic-coordinates quality flag filter: 'Passed', "
                        "'Failed', or 'Not tested'."
                    ),
                },
                "pep_length_interval": {
                    "type": "string",
                    "description": (
                        "Peptide-length range as 'min,max' (residues), e.g. "
                        "'8,20'. Catalogue range is 8-99."
                    ),
                },
                "mw_interval": {
                    "type": "string",
                    "description": (
                        "Molecular-weight range as 'min,max' (Da), e.g. "
                        "'800,3000'. Catalogue range is ~813-12286."
                    ),
                },
                "pI_interval": {
                    "type": "string",
                    "description": (
                        "Isoelectric-point range as 'min,max', e.g. '9,12'. "
                        "Catalogue range is ~4-12."
                    ),
                },
                "charge_interval": {
                    "type": "string",
                    "description": (
                        "Net-charge-at-pH-7 range as 'min,max', e.g. '0,10'. "
                        "Catalogue range is ~-57 to 44."
                    ),
                },
                "page_size": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "Results per page (default 20).",
                },
                "page": {
                    "type": "integer",
                    "minimum": 0,
                    "description": "Zero-based page index (default 0).",
                },
            },
            "required": [],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful AMP search or options listing.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "description": (
                                "List of AMP records (search), or the "
                                "filter-options object (list_options)."
                            )
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "mode": {"type": "string"},
                                "current_page": {"type": ["integer", "null"]},
                                "page_size": {"type": ["integer", "null"]},
                                "total_page": {"type": ["integer", "null"]},
                                "total_item": {"type": ["integer", "null"]},
                                "returned_count": {"type": ["integer", "null"]},
                                "has_more": {"type": ["boolean", "null"]},
                                "next_page": {"type": ["integer", "null"]},
                                "result_set_complete": {"type": ["boolean", "null"]},
                                "filters": {"type": "object"},
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
            {"habitat": "human gut", "page_size": 2, "page": 0},
            {"family": "SPHERE-III.001_396", "page_size": 3, "page": 0},
            {"list_options": True},
        ],
        "label": ["AMPSphere", "Antimicrobial Peptide", "AMP", "smORF", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "smORF",
                "metagenome",
                "microbiome",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereSearchAmpsTool(BaseTool):
    """Filter/search the AMPSphere AMP catalogue; paginated list + totals."""

    # user-arg -> AMPSphere /v1/amps query parameter.
    _PARAM_MAP = {
        "habitat": "habitat",
        "family": "family",
        "microbial_source": "microbial_source",
        "exp_evidence": "exp_evidence",
        "antifam": "antifam",
        "RNAcode": "RNAcode",
        "coordinates": "coordinates",
        "pep_length_interval": "pep_length_interval",
        "mw_interval": "mw_interval",
        "pI_interval": "pI_interval",
        "charge_interval": "charge_interval",
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        list_options = arguments.get("list_options", False)
        if not isinstance(list_options, bool):
            return _err("list_options must be a boolean")
        if list_options:
            payload, error = _get("/all_available_options")
            if error is not None:
                return error
            return {
                "status": "success",
                "data": payload,
                "metadata": {
                    "source": _SOURCE,
                    "url": f"{_BASE_URL}/all_available_options",
                    "mode": "options",
                },
            }

        def _provided(key: str) -> bool:
            val = arguments.get(key)
            return val is not None and str(val).strip() != ""

        params: Dict[str, Any] = {}
        filters: Dict[str, Any] = {}
        for arg_key, api_key in self._PARAM_MAP.items():
            if _provided(arg_key):
                if not isinstance(arguments[arg_key], str):
                    return _err(f"{arg_key} must be a string")
                params[api_key] = arguments[arg_key].strip()
                filters[arg_key] = params[api_key]

        page_size = arguments.get("page_size", 20)
        page = arguments.get("page", 0)
        if (
            isinstance(page_size, bool)
            or not isinstance(page_size, int)
            or page_size < 1
        ):
            return _err("page_size must be a positive integer")
        if isinstance(page, bool) or not isinstance(page, int) or page < 0:
            return _err("page must be a non-negative integer")
        params["page_size"] = page_size
        params["page"] = page

        payload, error = _get("/amps", params=params)
        if error is not None:
            return error

        if not isinstance(payload, dict):
            return _err("Unexpected AMPSphere response shape")

        info = payload.get("info") or {}
        records = payload.get("data") or []
        current_page = info.get("currentPage")
        total_pages = info.get("totalPage")
        total_items = info.get("totalItem")
        has_more = bool(
            isinstance(current_page, int)
            and isinstance(total_pages, int)
            and current_page + 1 < total_pages
        )
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": _SOURCE,
                "url": f"{_BASE_URL}/amps",
                "mode": "search",
                "current_page": current_page,
                "page_size": info.get("pageSize"),
                "total_page": total_pages,
                "total_item": total_items,
                "returned_count": len(records),
                "has_more": has_more,
                "next_page": current_page + 1 if has_more else None,
                "truncated": bool((current_page or 0) > 0 or has_more),
                "result_set_complete": bool(
                    current_page == 0
                    and isinstance(total_items, int)
                    and len(records) == total_items
                ),
                "pagination_stalled": bool(has_more and not records),
                "filters": filters,
            },
        }


@register_tool(
    "AMPSphereGetFamilyTool",
    config={
        "name": "AMPSphere_get_family",
        "type": "AMPSphereGetFamilyTool",
        "description": (
            "Retrieve full detail for an AMPSphere protein family (SPHERE "
            "cluster) by accession (e.g. 'SPHERE-III.001_396'): the consensus "
            "sequence, member count, the full member-AMP accession list, "
            "per-member feature statistics, geographic / habitat / "
            "microbial-source distributions, and ready-to-use download URLs for "
            "the family's alignment (.aln), member sequences (.faa), HMM profile "
            "(.hmm), and phylogenetic tree (.nwk / ASCII figure). Keyless "
            "AMPSphere REST API (/v1/families/{accession})."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": (
                        "SPHERE family accession. Example: 'SPHERE-III.001_396' "
                        "(23 member AMPs, consensus "
                        "'GDKLXXXXXVDXXXXGGLIVKXGSRMXDXSLXXKLXXLXXAMKXXG')."
                    ),
                }
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful family lookup.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "description": "Full AMPSphere family record.",
                            "properties": {
                                "accession": {"type": "string"},
                                "consensus_sequence": {"type": ["string", "null"]},
                                "num_amps": {"type": ["integer", "null"]},
                                "downloads": {"type": "object"},
                                "associated_amps": {"type": "array"},
                                "feature_statistics": {"type": "object"},
                                "distributions": {"type": "object"},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "accession": {"type": "string"},
                                "num_amps": {"type": ["integer", "null"]},
                                "member_count": {"type": "integer"},
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
            {"accession": "SPHERE-III.001_396"},
            {"accession": "SPHERE-III.001_493"},
        ],
        "label": ["AMPSphere", "Protein Family", "SPHERE", "AMP", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "protein family",
                "SPHERE",
                "consensus",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereGetFamilyTool(BaseTool):
    """Fetch a single AMPSphere SPHERE family record by accession."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession, error = _require_accession(arguments, "SPHERE-III.001_396")
        if error is not None:
            return error

        url = f"{_BASE_URL}/families/{accession}"
        payload, error = _get(f"/families/{accession}")
        if error is not None:
            return error

        if not isinstance(payload, dict) or not payload.get("accession"):
            return _err(
                f"No AMPSphere family record for accession {accession!r}", url=url
            )

        members = payload.get("associated_amps") or []
        return {
            "status": "success",
            "data": payload,
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": payload.get("accession"),
                "num_amps": payload.get("num_amps"),
                "member_count": len(members),
            },
        }


@register_tool(
    "AMPSphereGetAmpDistributionsTool",
    config={
        "name": "AMPSphere_get_amp_distributions",
        "type": "AMPSphereGetAmpDistributionsTool",
        "description": (
            "Retrieve the ecological and geographic distribution of a single "
            "AMPSphere AMP by accession (e.g. 'AMP10.000_000'): where it has "
            "been observed as a bubble-map of lat/lon coordinates with sample "
            "counts, across which habitats, and from which microbial taxonomic "
            "sources. Returns three blocks: geo (type='bubble map' with parallel "
            "lat/lon/size arrays), habitat (labels + values), and "
            "microbial_source (labels + values). Keyless AMPSphere REST API "
            "(/v1/amps/{accession}/distributions)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": (
                        "AMPSphere AMP accession. Example: 'AMP10.000_000'."
                    ),
                }
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful distribution lookup.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "description": "Per-AMP distribution record.",
                            "properties": {
                                "geo": {"type": "object"},
                                "habitat": {"type": "object"},
                                "microbial_source": {"type": "object"},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "accession": {"type": "string"},
                                "geo_point_count": {"type": ["integer", "null"]},
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
            {"accession": "AMP10.000_000"},
            {"accession": "AMP10.000_001"},
        ],
        "label": ["AMPSphere", "Biogeography", "Habitat", "AMP", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "biogeography",
                "habitat",
                "microbial source",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereGetAmpDistributionsTool(BaseTool):
    """Fetch per-AMP geographic / habitat / microbial-source distribution."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession, error = _require_accession(arguments, "AMP10.000_000")
        if error is not None:
            return error

        url = f"{_BASE_URL}/amps/{accession}/distributions"
        payload, error = _get(f"/amps/{accession}/distributions")
        if error is not None:
            return error

        if not isinstance(payload, dict):
            return _err(
                f"Unexpected AMPSphere distributions shape for {accession!r}", url=url
            )

        geo = payload.get("geo") or {}
        lat = geo.get("lat") if isinstance(geo, dict) else None
        geo_point_count = len(lat) if isinstance(lat, list) else None
        return {
            "status": "success",
            "data": payload,
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": accession,
                "geo_point_count": geo_point_count,
            },
        }


@register_tool(
    "AMPSphereGetAmpFeaturesTool",
    config={
        "name": "AMPSphere_get_amp_features",
        "type": "AMPSphereGetAmpFeaturesTool",
        "description": (
            "Retrieve the full physicochemical feature profile of a single "
            "AMPSphere AMP by accession (e.g. 'AMP10.000_000'): molecular "
            "weight, length, molar extinction (reduced cysteines / cystine "
            "residues), aromaticity, GRAVY hydrophobicity, instability index, "
            "isoelectric point, net charge at pH 7, and predicted "
            "secondary-structure fractions (helix / turn / sheet). The same "
            "GRAVY / instability / pI / charge values are also available as "
            "fields on AMPSphere_search_amps; this tool adds molar extinction "
            "and secondary-structure fractions. Keyless AMPSphere REST API "
            "(/v1/amps/{accession}/features)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": (
                        "AMPSphere AMP accession. Example: 'AMP10.000_000'."
                    ),
                }
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful feature lookup.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "description": "Physicochemical feature profile.",
                            "properties": {
                                "MW": {"type": ["number", "null"]},
                                "Length": {"type": ["number", "null"]},
                                "Molar_extinction": {"type": "object"},
                                "Aromaticity": {"type": ["number", "null"]},
                                "GRAVY": {"type": ["number", "null"]},
                                "Instability_index": {"type": ["number", "null"]},
                                "Isoelectric_point": {"type": ["number", "null"]},
                                "Charge_at_pH_7": {"type": ["number", "null"]},
                                "Secondary_structure": {"type": "object"},
                            },
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "accession": {"type": "string"},
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
            {"accession": "AMP10.000_000"},
            {"accession": "AMP10.000_001"},
        ],
        "label": [
            "AMPSphere",
            "Physicochemical",
            "Secondary Structure",
            "AMP",
            "Peptide",
        ],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "physicochemical",
                "GRAVY",
                "secondary structure",
                "peptide",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereGetAmpFeaturesTool(BaseTool):
    """Fetch the physicochemical + secondary-structure profile of one AMP."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession, error = _require_accession(arguments, "AMP10.000_000")
        if error is not None:
            return error

        url = f"{_BASE_URL}/amps/{accession}/features"
        payload, error = _get(f"/amps/{accession}/features")
        if error is not None:
            return error

        if not isinstance(payload, dict) or "MW" not in payload:
            return _err(
                f"No AMPSphere feature profile for accession {accession!r}", url=url
            )

        return {
            "status": "success",
            "data": payload,
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": accession,
            },
        }


@register_tool(
    "AMPSphereStatisticsTool",
    config={
        "name": "AMPSphere_get_statistics",
        "type": "AMPSphereStatisticsTool",
        "description": (
            "Get AMPSphere's catalogue-wide totals from /v1/statistics: how "
            "many AMPs the resource holds (num_amps), how many predicted smORF "
            "genes they were called from (num_genes), how many SPHERE families "
            "they cluster into (num_families), and how many habitats, genomes "
            "and metagenomes they were surveyed across. Use it to size the "
            "resource before a filtered search, to report a denominator "
            "alongside a hit count, or to check whether a cached figure is "
            "still current -- the other AMPSphere tools quote 863,498 AMPs in "
            "their descriptions and that number comes from here. Takes no "
            "parameters. Keyless AMPSphere REST API."
        ),
        "parameter": {"type": "object", "properties": {}, "required": []},
        "return_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": '"success" or "error".'},
                "data": {
                    "type": "object",
                    "properties": {
                        "num_amps": {
                            "type": "integer",
                            "description": "Antimicrobial peptides in the catalogue.",
                        },
                        "num_genes": {
                            "type": "integer",
                            "description": "Predicted smORF genes the AMPs were called from.",
                        },
                        "num_families": {
                            "type": "integer",
                            "description": "SPHERE families the AMPs cluster into.",
                        },
                        "num_habitats": {
                            "type": "integer",
                            "description": "Distinct habitat labels represented.",
                        },
                        "num_genomes": {
                            "type": "integer",
                            "description": "Genomes contributing at least one AMP.",
                        },
                        "num_metagenomes": {
                            "type": "integer",
                            "description": "Metagenomes contributing at least one AMP.",
                        },
                    },
                },
                "metadata": {"type": "object"},
                "error": {"type": "string"},
            },
        },
        "test_examples": [{}],
        "label": ["AMPSphere", "Statistics", "Catalogue", "AMP", "Peptide"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "statistics",
                "catalogue size",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereStatisticsTool(BaseTool):
    """Catalogue-wide totals, which no other AMPSphere tool exposed.

    `/v1/statistics` is the only place the resource states its own size, and
    three tool descriptions quote one of its numbers (863,498 AMPs) as a
    literal. A caller that wants the denominator for a hit count, or that
    wants to know whether the literal is still true, had no way to ask.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{_BASE_URL}/statistics"
        payload, error = _get("/statistics")
        if error is not None:
            return error

        if not isinstance(payload, dict) or "num_amps" not in payload:
            return _err("AMPSphere /v1/statistics returned no totals.", url=url)

        return {
            "status": "success",
            "data": payload,
            "metadata": {"source": _SOURCE, "url": url},
        }


@register_tool(
    "AMPSphereCopredictionTool",
    config={
        "name": "AMPSphere_get_amp_coprediction",
        "type": "AMPSphereCopredictionTool",
        "description": (
            "Get the per-predictor antimicrobial scores for one AMPSphere "
            "peptide: how each of the seven independent AMP predictors scored "
            "it (APIN, AI4AMP, AMPScanner2, AMPlify, ampir, Macrel, amPEPpy). "
            "AMPSphere's own membership is a Macrel call, and the predictors "
            "DISAGREE -- AMP10.000_000 reads 1.0 from APIN and 0.989 from "
            "AI4AMP but 0.604 from Macrel and 0.601 from amPEPpy -- so this is "
            "the evidence for the question the resource exists to answer, and "
            "it was not reachable from any tool. Treat a peptide scored high "
            "by one predictor and low by six as weakly supported. Keyless "
            "AMPSphere REST API (/v1/amps/{accession}/coprediction)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": "AMPSphere AMP accession. Example: 'AMP10.000_000'.",
                }
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "accession": {"type": "string"},
                        "predictions": {
                            "type": "array",
                            "description": "One entry per predictor, as returned.",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "predictor": {
                                        "type": "string",
                                        "description": "APIN, AI4AMP, AMPScanner2, AMPlify, ampir, Macrel or amPEPpy.",
                                    },
                                    "value": {
                                        "type": ["number", "null"],
                                        "description": "That predictor's score. The scales are NOT comparable between predictors: each is its own model's probability or score, so read the spread as agreement or disagreement, not as an average.",
                                    },
                                },
                            },
                        },
                        "predictors_agreeing": {
                            "type": "integer",
                            "description": "How many predictors scored above 0.5. Reported beside the count of predictors so the denominator is never missing.",
                        },
                        "predictors_total": {"type": "integer"},
                        "score_range": {
                            "type": ["array", "null"],
                            "description": "[lowest, highest] score, so disagreement is visible without reading every row.",
                        },
                    },
                    "required": ["accession", "predictions"],
                },
                {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
            ]
        },
        "test_examples": [
            {"accession": "AMP10.000_000"},
            {"accession": "AMP10.000_001"},
        ],
        "label": ["AMPSphere", "AMP", "Prediction", "Peptide", "Antimicrobial"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "prediction",
                "coprediction",
                "Macrel",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereCopredictionTool(BaseTool):
    """Seven independent predictors' scores for one peptide.

    /v1/amps/{accession}/coprediction is a real endpoint that no tool
    reached. Whether a peptide IS antimicrobial is the question AMPSphere
    exists to answer, the seven predictors disagree about it, and a caller
    had no way to see the disagreement.
    """

    _THRESHOLD = 0.5

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession, error = _require_accession(arguments, "AMP10.000_000")
        if error is not None:
            return error

        url = f"{_BASE_URL}/amps/{accession}/coprediction"
        payload, error = _get(f"/amps/{accession}/coprediction")
        if error is not None:
            return error

        rows = payload if isinstance(payload, list) else []
        if not rows:
            return _err(
                f"AMPSphere returned no co-prediction scores for {accession!r}",
                url=url,
            )

        scores = [
            row.get("value")
            for row in rows
            if isinstance(row, dict) and isinstance(row.get("value"), (int, float))
        ]
        return {
            "status": "success",
            "data": {
                "accession": accession,
                "predictions": rows,
                "predictors_total": len(rows),
                "predictors_agreeing": sum(1 for s in scores if s > self._THRESHOLD),
                "score_range": [min(scores), max(scores)] if scores else None,
            },
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": accession,
                "agreement_threshold": self._THRESHOLD,
                "note": (
                    "The seven predictors are independent models on their own "
                    "scales, so `predictors_agreeing` counts how many exceed "
                    f"{self._THRESHOLD} and is not a consensus probability. Do "
                    "not average the scores."
                ),
            },
        }


@register_tool(
    "AMPSphereAmpMetadataTool",
    config={
        "name": "AMPSphere_get_amp_metadata",
        "type": "AMPSphereAmpMetadataTool",
        "description": (
            "Page through the samples one AMPSphere peptide was observed in: "
            "per sample, the GMSC gene accession and gene sequence, the sample "
            "id, whether it is metagenomic, the geographic location with "
            "latitude/longitude, the habitat (general_envo_name, "
            "environment_material) and the microbial source resolved down the "
            "taxonomy (domain to species). This is where a peptide's ecology "
            "and host range live, and nothing reached it: AMP10.000_000 has "
            "15,523 such rows and AMPSphere_get_amp embeds five. Returns one "
            "page plus the totals, so a page is never mistaken for the set. "
            "Keyless AMPSphere REST API (/v1/amps/{accession}/metadata)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": "AMPSphere AMP accession. Example: 'AMP10.000_000'.",
                },
                "page": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "Zero-based page number.",
                },
                "page_size": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100,
                    "default": 20,
                    "description": "Rows per page (upstream default 20).",
                },
            },
            "required": ["accession"],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "accession": {"type": "string"},
                        "samples": {
                            "type": "array",
                            "description": "One row per observation of this peptide in a sample.",
                            "items": {"type": "object"},
                        },
                        "returned": {"type": "integer"},
                        "total_samples": {
                            "type": ["integer", "null"],
                            "description": "How many rows there are in all, across every page.",
                        },
                        "total_pages": {"type": ["integer", "null"]},
                        "page": {"type": ["integer", "null"]},
                        "page_size": {"type": ["integer", "null"]},
                        "has_more": {"type": "boolean"},
                        "next_page": {"type": ["integer", "null"]},
                    },
                    "required": ["accession", "samples", "returned"],
                },
                {
                    "type": "object",
                    "properties": {"error": {"type": "string"}},
                    "required": ["error"],
                },
            ]
        },
        "test_examples": [
            {"accession": "AMP10.000_000", "page_size": 5},
            {"accession": "AMP10.000_001"},
        ],
        "label": ["AMPSphere", "AMP", "Sample", "Habitat", "Taxonomy"],
        "metadata": {
            "tags": [
                "antimicrobial peptide",
                "AMP",
                "AMPSphere",
                "habitat",
                "metagenome",
                "taxonomy",
            ],
            "estimated_execution_time": "1-3 seconds",
        },
    },
)
class AMPSphereAmpMetadataTool(BaseTool):
    """The samples a peptide was seen in, paged, with the totals beside them."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession, error = _require_accession(arguments, "AMP10.000_000")
        if error is not None:
            return error

        arguments = arguments or {}
        try:
            page = max(0, int(arguments.get("page") or 0))
        except (TypeError, ValueError):
            return _err("page must be a non-negative integer")
        try:
            page_size = int(arguments.get("page_size") or 20)
        except (TypeError, ValueError):
            return _err("page_size must be an integer")
        page_size = max(1, min(page_size, 100))

        url = f"{_BASE_URL}/amps/{accession}/metadata"
        payload, error = _get(
            f"/amps/{accession}/metadata",
            {"page": page, "page_size": page_size},
        )
        if error is not None:
            return error

        if not isinstance(payload, dict):
            return _err(f"No AMPSphere sample metadata for {accession!r}", url=url)

        rows = payload.get("data") or []
        info = payload.get("info") or {}
        total = info.get("totalItem")
        total_pages = info.get("totalPage")
        has_more = bool(total is not None and (page + 1) * page_size < total) or bool(
            total_pages is not None and page + 1 < total_pages
        )

        return {
            "status": "success",
            "data": {
                "accession": accession,
                "samples": rows,
                "returned": len(rows),
                "total_samples": total,
                "total_pages": total_pages,
                "page": info.get("currentPage", page),
                "page_size": info.get("pageSize", page_size),
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
            },
            "metadata": {
                "source": _SOURCE,
                "url": url,
                "accession": accession,
                "count_semantics": "rows_on_this_page_not_total; total_samples is the total",
            },
        }
