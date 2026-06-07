"""
Pathoplexus (LAPIS) tools for ToolUniverse — open pathogen genomic surveillance.

Pathoplexus is an open, community pathogen-sequence database (launched 2024) served
by LAPIS (Lineage API for Sequences). These tools query aggregated sequence counts
and characteristic mutations per organism — genomic-epidemiology surveillance for
emerging pathogens. Distinct from Nextstrain (phylogenetic builds) and BV-BRC.

API: https://lapis.pathoplexus.org/{organism}/sample/...  (public, no authentication)
Known organisms: west-nile, ebola-zaire, ebola-sudan, cchf, mpox (more may be added).
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

LAPIS_BASE = "https://lapis.pathoplexus.org"


def _organism(arguments: Dict[str, Any]) -> str:
    return (arguments.get("organism") or "").strip().lower()


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
    """Aggregated sequence counts for a Pathoplexus organism."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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
            return {
                "status": "error",
                "error": f"Pathoplexus HTTP {e.response.status_code} — check the organism slug and filter fields",
            }
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
        try:
            params["minProportion"] = float(arguments.get("min_proportion") or 0.8)
        except (TypeError, ValueError):
            params["minProportion"] = 0.8
        try:
            params["limit"] = max(1, min(int(arguments.get("limit") or 50), 500))
        except (TypeError, ValueError):
            params["limit"] = 50

        mtype = (arguments.get("mutation_type") or "aminoAcid").strip()
        endpoint = (
            "nucleotideMutations"
            if mtype.lower().startswith("nucl")
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
            return {
                "status": "error",
                "error": f"Pathoplexus HTTP {e.response.status_code} — check the organism slug and filter fields",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pathoplexus request failed: {e}"}
        except ValueError:
            return {
                "status": "error",
                "error": "Pathoplexus returned a non-JSON response",
            }

        rows = payload.get("data", []) if isinstance(payload, dict) else []
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
                "source": "Pathoplexus (LAPIS)",
            },
        }
