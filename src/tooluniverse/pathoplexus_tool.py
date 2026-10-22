"""
Pathoplexus (LAPIS) tools for ToolUniverse — open pathogen genomic surveillance.

Pathoplexus is an open, community pathogen-sequence database (launched 2024) served
by LAPIS (Lineage API for Sequences). These tools query aggregated sequence counts
and characteristic mutations per organism — genomic-epidemiology surveillance for
emerging pathogens. Distinct from Nextstrain (phylogenetic builds) and BV-BRC.

API: https://lapis.pathoplexus.org/{organism}/sample/...  (public, no authentication)
Known organisms: west-nile, ebola-zaire, ebola-sudan, cchf, mpox (more may be added).
"""

import math
from typing import Any, Dict, Optional, Tuple

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

LAPIS_BASE = "https://lapis.pathoplexus.org"

# Confirmed live: an unsupported organism slug 404s with a bare LAPIS error
# that doesn't name the actual valid slugs, forcing the caller back to the
# tool description. Surface this list directly in the error message too.
KNOWN_ORGANISMS = ["west-nile", "ebola-zaire", "ebola-sudan", "cchf", "mpox"]
_ORGS = ", ".join(KNOWN_ORGANISMS)


def _organism(arguments: Dict[str, Any]) -> str:
    return (arguments.get("organism") or "").strip().lower()


def _bounded_integer(
    arguments: Dict[str, Any],
    name: str,
    default: int,
    minimum: int,
    maximum: int,
) -> Tuple[Optional[int], Optional[Dict[str, str]]]:
    """Read a JSON integer without silently defaulting or clamping bad input."""

    value = arguments.get(name)
    if value is None:
        return default, None
    if isinstance(value, bool) or not isinstance(value, int):
        return None, {
            "status": "error",
            "error": f"'{name}' must be an integer from {minimum} to {maximum}",
        }
    if not minimum <= value <= maximum:
        return None, {
            "status": "error",
            "error": f"'{name}' must be between {minimum} and {maximum} (received {value})",
        }
    return value, None


def _api_info(payload: Any) -> Optional[Dict[str, Any]]:
    """Preserve LAPIS response provenance instead of dropping it."""

    if not isinstance(payload, dict) or not isinstance(payload.get("info"), dict):
        return None
    info = payload["info"]
    return {
        key: info.get(key)
        for key in (
            "dataVersion",
            "lapisVersion",
            "siloVersion",
            "requestId",
            "requestInfo",
        )
        if info.get(key) is not None
    }


class _PathoplexusBase(BaseTool):
    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("fields", {}).get("timeout", 30)

    def _get(
        self, organism: str, endpoint: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        resp = requests.get(
            f"{LAPIS_BASE}/{organism}/sample/{endpoint}",
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_text(
        self, organism: str, endpoint: str, params: Dict[str, Any], accept: str
    ) -> str:
        resp = requests.get(
            f"{LAPIS_BASE}/{organism}/sample/{endpoint}",
            params=params,
            headers={"Accept": accept},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.text

    @staticmethod
    def _http_error_response(
        e: requests.exceptions.HTTPError, hint: str
    ) -> Dict[str, Any]:
        return {
            "status": "error",
            "error": f"Pathoplexus HTTP {e.response.status_code} — check the organism slug (known organisms: {_ORGS}) and {hint}",
        }

    @staticmethod
    def _common_filters(arguments: Dict[str, Any]) -> Dict[str, Any]:
        params: Dict[str, Any] = {}
        country = (arguments.get("country") or "").strip()
        if country:
            params["geoLocCountry"] = country
        lineage = (arguments.get("lineage") or "").strip()
        if lineage:
            params["lineage"] = lineage
        return params


@register_tool("PathoplexusCountTool")
class PathoplexusCountTool(_PathoplexusBase):
    """Pathoplexus organism queries.

    The ``fields.mode`` config selects the LAPIS endpoint:
      - ``"aggregated"`` (default): aggregated sequence counts (original behavior)
      - ``"details"``: per-sequence metadata table (accession, country, date, ...)
      - ``"fasta"``: download unaligned/aligned nucleotide or amino-acid FASTA
    All modes are served by this one registered class so no new registration is
    needed; the original aggregated behavior is unchanged when ``mode`` is absent.
    """

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        mode = (self.tool_config.get("fields", {}) or {}).get("mode", "aggregated")
        if mode == "details":
            return self._run_details(arguments)
        if mode == "fasta":
            return self._run_fasta(arguments)
        return self._run_aggregated(arguments)

    def _run_aggregated(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = _organism(arguments)
        if not organism:
            return {
                "status": "error",
                "error": "'organism' is required (e.g. 'west-nile', 'mpox', 'ebola-zaire', 'cchf')",
            }
        filters = self._common_filters(arguments)
        params = dict(filters)
        group_by = (arguments.get("group_by") or "").strip()
        if group_by:
            params["fields"] = group_by
        # NOTE: the LAPIS /aggregated endpoint rejects limit/offset (its output is
        # unordered), so we do not paginate it; grouped output is bounded by the
        # number of distinct field values.

        try:
            payload = self._get(organism, "aggregated", params)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Pathoplexus request timed out after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return self._http_error_response(e, "filter fields")
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pathoplexus request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Pathoplexus returned a non-JSON response",
            }

        rows = payload.get("data", []) if isinstance(payload, dict) else []
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "organism": organism,
                "grouped_by": group_by or None,
                "filters": filters or None,
                "returned": len(rows),
                "api_info": _api_info(payload),
                "source": "Pathoplexus (LAPIS)",
            },
        }

    def _run_details(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = _organism(arguments)
        if not organism:
            return {
                "status": "error",
                "error": "'organism' is required (e.g. 'west-nile', 'mpox', 'ebola-zaire', 'cchf')",
            }
        filters = self._common_filters(arguments)
        params = dict(filters)

        fields = (arguments.get("fields") or "").strip()
        if fields:
            params["fields"] = [f.strip() for f in fields.split(",") if f.strip()]

        limit, error = _bounded_integer(arguments, "limit", 50, 1, 1000)
        if error:
            return error
        offset, error = _bounded_integer(arguments, "offset", 0, 0, 10_000_000)
        if error:
            return error
        assert limit is not None and offset is not None
        # Ask for one sentinel row so the wrapper can state definitively whether
        # another page exists.  Previously a full page looked complete and the
        # available LAPIS offset parameter was not reflected in metadata.
        params["limit"] = limit + 1
        if offset:
            params["offset"] = offset

        try:
            payload = self._get(organism, "details", params)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Pathoplexus request timed out after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return self._http_error_response(e, "field names")
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pathoplexus request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Pathoplexus returned a non-JSON response",
            }

        raw_rows = payload.get("data", []) if isinstance(payload, dict) else []
        rows = raw_rows[:limit] if isinstance(raw_rows, list) else []
        has_more = isinstance(raw_rows, list) and len(raw_rows) > limit
        return {
            "status": "success",
            "data": rows,
            "metadata": {
                "organism": organism,
                "filters": filters or None,
                "returned": len(rows),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + limit if has_more else None,
                "pagination_supported": True,
                "api_info": _api_info(payload),
                "source": "Pathoplexus (LAPIS)",
            },
        }

    def _run_fasta(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = _organism(arguments)
        if not organism:
            return {
                "status": "error",
                "error": "'organism' is required (e.g. 'west-nile', 'mpox', 'ebola-zaire', 'cchf')",
            }
        filters = self._common_filters(arguments)
        params = dict(filters)
        params["dataFormat"] = "FASTA"

        limit, error = _bounded_integer(arguments, "limit", 1, 1, 100)
        if error:
            return error
        offset, error = _bounded_integer(arguments, "offset", 0, 0, 10_000_000)
        if error:
            return error
        assert limit is not None and offset is not None
        params["limit"] = limit
        if offset:
            params["offset"] = offset

        raw_seq_type = arguments.get("sequence_type")
        seq_type = "nucleotide" if raw_seq_type is None else raw_seq_type
        if not isinstance(seq_type, str) or seq_type.lower() not in {
            "nucleotide",
            "aminoacid",
        }:
            return {
                "status": "error",
                "error": "'sequence_type' must be 'nucleotide' or 'aminoAcid'",
            }
        raw_aligned = arguments.get("aligned")
        if raw_aligned is not None and not isinstance(raw_aligned, bool):
            return {"status": "error", "error": "'aligned' must be a boolean"}
        aligned = False if raw_aligned is None else raw_aligned
        if seq_type.lower() == "aminoacid":
            endpoint = (
                "alignedAminoAcidSequences"
                if aligned
                else "unalignedAminoAcidSequences"
            )
        else:
            endpoint = (
                "alignedNucleotideSequences"
                if aligned
                else "unalignedNucleotideSequences"
            )

        try:
            text = self._get_text(organism, endpoint, params, "text/x-fasta")
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Pathoplexus request timed out after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return self._http_error_response(e, "filter fields")
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pathoplexus request failed: {e}"}

        if not text or not text.lstrip().startswith(">"):
            return {
                "status": "error",
                "error": "Pathoplexus returned no FASTA records for this query",
            }

        n_records = text.count(">")
        page_completeness = "complete" if n_records < limit else "unknown"
        return {
            "status": "success",
            "data": {"fasta": text, "num_records": n_records},
            "metadata": {
                "organism": organism,
                "endpoint": endpoint,
                "filters": filters or None,
                "returned": n_records,
                "limit": limit,
                "offset": offset,
                "pagination_supported": True,
                "has_more": False if page_completeness == "complete" else None,
                "next_offset": (
                    None if page_completeness == "complete" else offset + limit
                ),
                "page_completeness": page_completeness,
                "pagination_note": (
                    "A short page is complete. For a full page, use next_offset to "
                    "probe the next sequence page; LAPIS FASTA responses do not "
                    "include a total count, so has_more remains unknown."
                ),
                "source": "Pathoplexus (LAPIS)",
            },
        }


@register_tool("PathoplexusMutationsTool")
class PathoplexusMutationsTool(_PathoplexusBase):
    """Characteristic amino-acid or nucleotide mutations for a Pathoplexus organism."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        organism = _organism(arguments)
        if not organism:
            return {
                "status": "error",
                "error": "'organism' is required (e.g. 'west-nile', 'mpox', 'ebola-zaire', 'cchf')",
            }
        filters = self._common_filters(arguments)
        params = dict(filters)
        raw_min_proportion = arguments.get("min_proportion")
        if raw_min_proportion is None:
            min_proportion = 0.8
        elif isinstance(raw_min_proportion, bool) or not isinstance(
            raw_min_proportion, (int, float)
        ):
            return {
                "status": "error",
                "error": "'min_proportion' must be a number from 0 to 1",
            }
        else:
            min_proportion = float(raw_min_proportion)
            if not math.isfinite(min_proportion) or not 0 <= min_proportion <= 1:
                return {
                    "status": "error",
                    "error": "'min_proportion' must be between 0 and 1",
                }
        # Do not use ``value or 0.8`` here: zero is the valid LAPIS threshold
        # that requests all observed mutations.
        params["minProportion"] = min_proportion

        limit, error = _bounded_integer(arguments, "limit", 50, 1, 500)
        if error:
            return error
        offset, error = _bounded_integer(arguments, "offset", 0, 0, 10_000_000)
        if error:
            return error
        assert limit is not None and offset is not None
        params["limit"] = limit + 1
        if offset:
            params["offset"] = offset

        raw_mtype = arguments.get("mutation_type")
        mtype = "aminoAcid" if raw_mtype is None else raw_mtype
        if not isinstance(mtype, str) or mtype.lower() not in {
            "aminoacid",
            "nucleotide",
        }:
            return {
                "status": "error",
                "error": "'mutation_type' must be 'aminoAcid' or 'nucleotide'",
            }
        endpoint = (
            "nucleotideMutations"
            if mtype.lower() == "nucleotide"
            else "aminoAcidMutations"
        )

        try:
            payload = self._get(organism, endpoint, params)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Pathoplexus request timed out after {self.timeout}s",
            }
        except requests.exceptions.HTTPError as e:
            return self._http_error_response(e, "filter fields")
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pathoplexus request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Pathoplexus returned a non-JSON response",
            }

        raw_rows = payload.get("data", []) if isinstance(payload, dict) else []
        rows = raw_rows[:limit] if isinstance(raw_rows, list) else []
        has_more = isinstance(raw_rows, list) and len(raw_rows) > limit
        muts = [
            {
                "mutation": m.get("mutation"),
                "gene": m.get("sequenceName"),
                "position": m.get("position"),
                "from": m.get("mutationFrom"),
                "to": m.get("mutationTo"),
                "proportion": m.get("proportion"),
                "count": m.get("count"),
                "coverage": m.get("coverage"),
            }
            for m in rows
            if isinstance(m, dict)
        ]
        return {
            "status": "success",
            "data": muts,
            "metadata": {
                "organism": organism,
                "mutation_type": endpoint,
                "min_proportion": params["minProportion"],
                "filters": filters or None,
                "returned": len(muts),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + limit if has_more else None,
                "pagination_supported": True,
                "api_info": _api_info(payload),
                "source": "Pathoplexus (LAPIS)",
            },
        }
