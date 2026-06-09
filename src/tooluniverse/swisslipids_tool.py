"""
SwissLipids tool for ToolUniverse.

SwissLipids (swisslipids.org, maintained by the SIB Swiss Institute of
Bioinformatics) is a curated knowledge resource for lipids. It organises
lipids into a structural hierarchy (class -> species -> subspecies) and links
each entry to formula, monoisotopic mass, adduct m/z values (useful for
lipidomics MS), cross-references (ChEBI, HMDB, LIPID MAPS, Rhea, MetaNetX),
and reactions.

It is complementary to the existing LIPID MAPS tools — a different
organisation's independently curated lipid database, with its own hierarchy
and the adduct-m/z table that LIPID MAPS does not provide.

API: https://www.swisslipids.org/api/index.php (public, no key).
"""

from typing import Any, Dict, List

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

SWISSLIPIDS_API = "https://www.swisslipids.org/api/index.php"


@register_tool("SwissLipidsTool")
class SwissLipidsTool(BaseTool):
    """Search SwissLipids and retrieve lipid entries (SIB)."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.operation: str = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation") or self.operation
        if operation == "search":
            return self._search(arguments)
        if operation == "get_lipid":
            return self._get_lipid(arguments)
        if operation == "get_children":
            return self._get_children(arguments)
        return {
            "status": "error",
            "error": f"Unknown operation: {operation}. Supported: search, get_lipid, get_children.",
        }

    def _request(self, path: str, params: Dict[str, Any] | None = None):
        try:
            resp = requests.get(
                f"{SWISSLIPIDS_API}/{path}",
                params=params or {},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.Timeout:
            return None, {
                "status": "error",
                "error": f"SwissLipids request timed out after {self.timeout}s.",
            }
        except requests.exceptions.RequestException as e:
            return None, {
                "status": "error",
                "error": f"Failed to reach SwissLipids: {str(e)}",
            }
        if resp.status_code != 200:
            return None, {
                "status": "error",
                "error": f"SwissLipids returned HTTP {resp.status_code}",
                "detail": resp.text[:300],
            }
        try:
            return resp.json(), None
        except ValueError:
            return None, {
                "status": "error",
                "error": "SwissLipids returned a non-JSON response.",
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        term = arguments.get("query") or arguments.get("term")
        if not term or not str(term).strip():
            return {
                "status": "error",
                "error": "Parameter 'query' is required (a lipid name or abbreviation, e.g. 'PC(16:0/18:1)').",
            }
        try:
            limit = max(1, min(int(arguments.get("limit", 10)), 100))
        except (TypeError, ValueError):
            return {"status": "error", "error": "Parameter 'limit' must be an integer."}

        body, err = self._request("search", {"term": str(term)})
        if err:
            return err
        hits = body if isinstance(body, list) else []
        results = [
            {
                "entity_id": h.get("entity_id"),
                "entity_name": h.get("entity_name"),
                "entity_type": h.get("entity_type"),
                "classification_level": h.get("classification_level"),
            }
            for h in hits[:limit]
        ]
        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "SwissLipids (swisslipids.org, SIB)",
                "query": str(term),
                "total_matches": len(hits),
                "returned": len(results),
            },
        }

    def _get_lipid(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        entity_id = arguments.get("entity_id") or arguments.get("slm_id")
        if not entity_id or not str(entity_id).strip():
            return {
                "status": "error",
                "error": "Parameter 'entity_id' is required (a SwissLipids id, e.g. 'SLM:000000510').",
            }
        entity_id = str(entity_id).strip()
        if not entity_id.upper().startswith("SLM:"):
            entity_id = f"SLM:{entity_id}"

        body, err = self._request(f"entity/{entity_id}")
        if err:
            # The entity endpoint returns HTTP 500 for non-existent or malformed
            # ids, so translate any HTTP error into an actionable not-found.
            if "HTTP" in err.get("error", ""):
                return {
                    "status": "error",
                    "error": f"No SwissLipids entry for '{entity_id}' (it may not exist "
                    "or the id is malformed). Find valid ids with SwissLipids_search.",
                }
            return err
        entry = body[0] if isinstance(body, list) and body else body
        if not isinstance(entry, dict) or not entry.get("entity_id"):
            return {
                "status": "error",
                "error": f"No SwissLipids entry found for {entity_id}.",
            }

        chem = entry.get("chemical_data") or {}
        xrefs: List[Dict[str, Any]] = [
            {"source": x.get("source"), "id": x.get("id"), "url": x.get("url")}
            for x in (entry.get("xrefs") or [])
            if x.get("id")
        ]
        synonyms = [
            s.get("name") for s in (entry.get("synonyms") or []) if s.get("name")
        ]
        classification = []
        for c in entry.get("classification") or []:
            if isinstance(c, dict):
                name = c.get("entity_name") or c.get("name")
                if name:
                    classification.append(name)
        return {
            "status": "success",
            "data": {
                "entity_id": entry.get("entity_id"),
                "entity_name": entry.get("entity_name"),
                "entity_type": entry.get("entity_type"),
                "formula": chem.get("formula"),
                "mass": chem.get("mass"),
                "charge": chem.get("charge"),
                "adduct_mz": chem.get("mz"),
                "classification": classification,
                "synonyms": synonyms,
                "xrefs": xrefs,
            },
            "metadata": {"source": "SwissLipids (swisslipids.org, SIB)"},
        }

    def _get_children(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the direct children of a SwissLipids hierarchy node.

        Descends the lipid structural hierarchy (category -> class -> species ->
        subspecies). The /children endpoint returns a list of single-key dicts
        ({"SLM:...": {entity record}}); this flattens them into a list of
        child entities.
        """
        entity_id = arguments.get("entity_id") or arguments.get("slm_id")
        if not entity_id or not str(entity_id).strip():
            return {
                "status": "error",
                "error": "Parameter 'entity_id' is required (a SwissLipids id, e.g. "
                "'SLM:000001193'). Find ids with SwissLipids_search.",
            }
        entity_id = str(entity_id).strip()
        if not entity_id.upper().startswith("SLM:"):
            entity_id = f"SLM:{entity_id}"

        body, err = self._request("children", {"entity_id": entity_id})
        if err:
            if "HTTP" in err.get("error", ""):
                return {
                    "status": "error",
                    "error": f"No SwissLipids children for '{entity_id}' (the id may not "
                    "exist or be malformed). Find valid ids with SwissLipids_search.",
                }
            return err

        children: List[Dict[str, Any]] = []
        # /children returns a list of {"SLM:...": {record}} single-key dicts.
        records = body if isinstance(body, list) else [body]
        for item in records:
            if not isinstance(item, dict):
                continue
            for child in item.values():
                if isinstance(child, dict) and child.get("entity_id"):
                    children.append(
                        {
                            "entity_id": child.get("entity_id"),
                            "entity_name": child.get("entity_name"),
                            "entity_type": child.get("entity_type"),
                            "formula": child.get("formula"),
                            "mass": child.get("mass"),
                            "inchikey": child.get("inchikey"),
                        }
                    )

        return {
            "status": "success",
            "data": children,
            "metadata": {
                "source": "SwissLipids (swisslipids.org, SIB)",
                "parent_id": entity_id,
                "child_count": len(children),
            },
        }
