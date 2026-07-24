"""IUCN Red List conservation-status tool for ToolUniverse.

The IUCN Red List is the authoritative source for species extinction-risk
(conservation) status. The ecology/biodiversity workflows need it, but GBIF and
the other occurrence tools do not return Red List categories.

API: https://api.iucnredlist.org/api/v4/  (free; requires a token, read from the
IUCN_API_KEY environment variable, sent as an Authorization header).
Register: https://api.iucnredlist.org/
"""

import os
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

IUCN_URL = "https://api.iucnredlist.org/api/v4"
_CATEGORIES = {
    "EX": "Extinct",
    "EW": "Extinct in the Wild",
    "CR": "Critically Endangered",
    "EN": "Endangered",
    "VU": "Vulnerable",
    "NT": "Near Threatened",
    "LC": "Least Concern",
    "DD": "Data Deficient",
    "NE": "Not Evaluated",
}


@register_tool("IUCNTool")
class IUCNTool(BaseTool):
    """Get IUCN Red List conservation status for a species by scientific name."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.token = os.environ.get("IUCN_API_KEY", "")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if not self.token:
            return {
                "status": "error",
                "error": (
                    "IUCN Red List requires a free API token. Register at "
                    "https://api.iucnredlist.org/ and set the IUCN_API_KEY "
                    "environment variable."
                ),
            }
        name = (
            arguments.get("scientific_name") or arguments.get("species") or ""
        ).strip()
        genus = (arguments.get("genus_name") or "").strip()
        species = (arguments.get("species_name") or "").strip()
        if name and not (genus and species):
            parts = name.split()
            if len(parts) >= 2:
                genus, species = parts[0], parts[1]
        if not (genus and species):
            return {
                "status": "error",
                "error": "Provide scientific_name 'Genus species' (e.g. 'Panthera leo') "
                "or genus_name + species_name.",
            }

        headers = {"Authorization": self.token, "Accept": "application/json"}
        url = f"{IUCN_URL}/taxa/scientific_name"
        params = {"genus_name": genus, "species_name": species}
        try:
            resp = requests.get(
                url, params=params, headers=headers, timeout=self.timeout
            )
            if resp.status_code == 401 or resp.status_code == 403:
                return {
                    "status": "error",
                    "error": "IUCN API rejected the token (HTTP %d)" % resp.status_code,
                }
            if resp.status_code == 404:
                return {
                    "status": "success",
                    "data": None,
                    "metadata": {
                        "source": "IUCN Red List",
                        "query": f"{genus} {species}",
                        "note": "No IUCN assessment found for this scientific name.",
                    },
                }
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"IUCN API returned HTTP {resp.status_code}",
                }
            data = resp.json()
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"IUCN API timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"IUCN API request failed: {e}"}

        assessments = data.get("assessments") or []
        # Prefer the latest / globally-scoped assessment.
        latest = None
        for a in assessments:
            if a.get("latest") or latest is None:
                latest = a
        code = (latest or {}).get("red_list_category_code") or (latest or {}).get(
            "category"
        )
        result = {
            "scientific_name": f"{genus} {species}",
            "red_list_category_code": code,
            "red_list_category": _CATEGORIES.get(code, code),
            "year_published": (latest or {}).get("year_published"),
            "assessment_id": (latest or {}).get("assessment_id"),
            "scopes": (latest or {}).get("scopes"),
            "n_assessments": len(assessments),
        }
        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "IUCN Red List",
                "query": f"{genus} {species}",
                "interpretation": (
                    "Threatened categories are CR (Critically Endangered) > EN "
                    "(Endangered) > VU (Vulnerable); NT near-threatened; LC least "
                    "concern; DD data deficient; EX/EW extinct."
                ),
            },
        }
