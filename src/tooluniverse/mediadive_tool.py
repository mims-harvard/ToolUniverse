# mediadive_tool.py
"""
MediaDive cultivation media database tool for ToolUniverse.

MediaDive (DSMZ) holds standardized recipes for over 3,300 microbial growth
media: exact ingredient amounts, preparation steps, pH range, and the
chemical identity (CAS, ChEBI, PubChem) of each ingredient.

ToolUniverse already wraps BacDive (also DSMZ) for strain phenotype and
taxonomy, but has no way to look up what a strain should actually be grown
in, or reproduce a published medium's recipe. This tool closes that gap.

The list endpoints (`media`, `ingredients`) ignore server-side name filters
and always return their full catalogue, so this tool fetches each list once
per process and filters client-side; both are small enough (~1,200 and
~3,300 rows) that this is fast rather than a workaround under a budget, as
the similarly-shaped MCSATool needed for M-CSA's much larger catalogue.

API: https://mediadive.dsmz.de/rest
No authentication required.
"""

import threading
from typing import Dict, Any, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

MEDIADIVE_BASE_URL = "https://mediadive.dsmz.de/rest"


class _Catalogue:
    """Lazily fetches and caches one MediaDive list endpoint per process."""

    def __init__(self, endpoint: str):
        self._endpoint = endpoint
        self._rows: Optional[List[Dict[str, Any]]] = None
        self._lock = threading.Lock()

    def rows(self, timeout: int) -> List[Dict[str, Any]]:
        if self._rows is None:
            with self._lock:
                if self._rows is None:
                    response = requests.get(
                        f"{MEDIADIVE_BASE_URL}/{self._endpoint}", timeout=timeout
                    )
                    response.raise_for_status()
                    self._rows = response.json().get("data") or []
        return self._rows


@register_tool("MediaDiveTool")
class MediaDiveTool(BaseTool):
    """
    Tool for retrieving microbial cultivation media recipes from MediaDive.

    Supports searching media by name, fetching a medium's full recipe and
    preparation steps, and looking up an ingredient's chemical identifiers.

    No authentication required.
    """

    _media = _Catalogue("media")
    _ingredients = _Catalogue("ingredients")

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 45)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_media"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MediaDive lookup."""
        try:
            if self.operation == "search_media":
                return self._search_media(arguments)
            if self.operation == "get_medium":
                return self._get_medium(arguments)
            if self.operation == "search_ingredients":
                return self._search_ingredients(arguments)
            if self.operation == "get_ingredient":
                return self._get_ingredient(arguments)
            return {
                "status": "error",
                "error": f"Unknown operation: {self.operation}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"MediaDive request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to MediaDive. Check network.",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            return {"status": "error", "error": f"MediaDive returned HTTP {code}"}
        except Exception as e:
            return {"status": "error", "error": f"Error querying MediaDive: {str(e)}"}

    def _search_media(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the medium catalogue by name substring."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required: a medium name or substring, e.g. "
                "'nutrient agar' or 'marine broth'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        wanted = query.lower()
        matches = [
            {
                "medium_id": row.get("id"),
                "name": row.get("name"),
                "source": row.get("source"),
                "min_pH": row.get("min_pH"),
                "max_pH": row.get("max_pH"),
                "description": row.get("description"),
                "reference": row.get("reference"),
            }
            for row in self._media.rows(self.timeout)
            if wanted in (row.get("name") or "").lower()
        ]

        if not matches:
            return {
                "status": "error",
                "error": f"No media matching '{query}' in MediaDive's "
                f"{len(self._media.rows(self.timeout))}-medium catalogue.",
            }

        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "query": query,
                "matches_found": len(matches),
                "returned": len(matches[:limit]),
                "note": "medium_id is what get_medium expects for the full recipe.",
                "source": "MediaDive (DSMZ)",
            },
        }

    def _get_medium(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one medium's full recipe and preparation steps."""
        medium_id = arguments.get("medium_id")
        if medium_id is None or str(medium_id).strip() == "":
            return {
                "status": "error",
                "error": "medium_id is required, e.g. 1 (Nutrient Agar). Use "
                "MediaDive_search_media to find one by name.",
            }

        medium_id = str(medium_id).strip()
        response = requests.get(
            f"{MEDIADIVE_BASE_URL}/medium/{medium_id}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No MediaDive medium with id '{medium_id}'.",
            }
        response.raise_for_status()
        payload = response.json().get("data") or {}
        medium = payload.get("medium") or {}

        solutions = []
        for solution in payload.get("solutions") or []:
            solutions.append(
                {
                    "solution_name": solution.get("name"),
                    "volume_ml": solution.get("volume"),
                    "recipe": [
                        {
                            "compound": ing.get("compound"),
                            "compound_id": ing.get("compound_id"),
                            "amount": ing.get("amount"),
                            "unit": ing.get("unit"),
                            "grams_per_liter": ing.get("g_l"),
                            "optional": bool(ing.get("optional")),
                            "condition": ing.get("condition"),
                        }
                        for ing in solution.get("recipe") or []
                    ],
                    "preparation_steps": [
                        step.get("step")
                        for step in solution.get("steps") or []
                        if step.get("step")
                    ],
                }
            )

        return {
            "status": "success",
            "data": {
                "medium_id": medium.get("id"),
                "name": medium.get("name"),
                "complex_medium": medium.get("complex_medium"),
                "min_pH": medium.get("min_pH"),
                "max_pH": medium.get("max_pH"),
                "source": medium.get("source"),
                "reference_link": medium.get("link"),
                "solutions": solutions,
            },
            "metadata": {
                "medium_id": medium_id,
                "solution_count": len(solutions),
                "note": "compound_id is what get_ingredient expects for chemical "
                "identifiers of a recipe component.",
                "source": "MediaDive (DSMZ)",
            },
        }

    def _search_ingredients(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search the ingredient catalogue by name substring."""
        query = (arguments.get("query") or "").strip()
        if not query:
            return {
                "status": "error",
                "error": "query is required: an ingredient name or substring, "
                "e.g. 'yeast extract' or 'agar'.",
            }

        limit = arguments.get("limit")
        if not isinstance(limit, int) or limit <= 0:
            limit = 25
        limit = min(limit, 100)

        wanted = query.lower()
        matches = [
            {
                "ingredient_id": row.get("id"),
                "name": row.get("name"),
                "cas_number": row.get("CAS-RN"),
                "chebi_id": row.get("ChEBI"),
                "pubchem_id": row.get("PubChem"),
                "formula": row.get("formula"),
            }
            for row in self._ingredients.rows(self.timeout)
            if wanted in (row.get("name") or "").lower()
        ]

        if not matches:
            return {
                "status": "error",
                "error": f"No ingredients matching '{query}' in MediaDive's "
                f"{len(self._ingredients.rows(self.timeout))}-ingredient catalogue.",
            }

        return {
            "status": "success",
            "data": matches[:limit],
            "metadata": {
                "query": query,
                "matches_found": len(matches),
                "returned": len(matches[:limit]),
                "source": "MediaDive (DSMZ)",
            },
        }

    def _get_ingredient(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch one ingredient's chemical identifiers and synonyms."""
        ingredient_id = arguments.get("ingredient_id")
        if ingredient_id is None or str(ingredient_id).strip() == "":
            return {
                "status": "error",
                "error": "ingredient_id is required, e.g. 3 (Agar). Use "
                "MediaDive_search_ingredients to find one by name.",
            }

        ingredient_id = str(ingredient_id).strip()
        response = requests.get(
            f"{MEDIADIVE_BASE_URL}/ingredient/{ingredient_id}", timeout=self.timeout
        )
        if response.status_code == 404:
            return {
                "status": "error",
                "error": f"No MediaDive ingredient with id '{ingredient_id}'.",
            }
        response.raise_for_status()
        data = response.json().get("data") or {}
        media_ids = data.get("media") or []

        return {
            "status": "success",
            "data": {
                "ingredient_id": data.get("id"),
                "name": data.get("name"),
                "synonyms": data.get("synonyms") or [],
                "cas_number": data.get("CAS-RN"),
                "chebi_id": data.get("ChEBI"),
                "kegg_compound": data.get("KEGG-Compound"),
                "pubchem_id": data.get("PubChem"),
                "formula": data.get("formula"),
                "molecular_mass": data.get("mass"),
                "used_in_media_count": len(media_ids),
                "used_in_media_sample": media_ids[:20],
            },
            "metadata": {
                "ingredient_id": ingredient_id,
                "note": "used_in_media_sample lists up to 20 medium_ids using "
                "this ingredient; used_in_media_count is the true total.",
                "source": "MediaDive (DSMZ)",
            },
        }
