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


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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
                    "type": ["integer", "string"],
                    "description": "Results per page (default 20).",
                },
                "page": {
                    "type": ["integer", "string"],
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

        if arguments.get("list_options"):
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
                params[api_key] = str(arguments[arg_key]).strip()
                filters[arg_key] = params[api_key]

        page_size = _as_int(arguments.get("page_size", 20), 20)
        page = _as_int(arguments.get("page", 0), 0)
        if page_size <= 0:
            page_size = 20
        if page < 0:
            page = 0
        params["page_size"] = page_size
        params["page"] = page

        payload, error = _get("/amps", params=params)
        if error is not None:
            return error

        if not isinstance(payload, dict):
            return _err("Unexpected AMPSphere response shape")

        info = payload.get("info") or {}
        records = payload.get("data") or []
        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": _SOURCE,
                "url": f"{_BASE_URL}/amps",
                "mode": "search",
                "current_page": info.get("currentPage"),
                "page_size": info.get("pageSize"),
                "total_page": info.get("totalPage"),
                "total_item": info.get("totalItem"),
                "returned_count": len(records),
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
