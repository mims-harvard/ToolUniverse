"""
T3DB Tool - Toxin and Toxin-Target Database

Provides access to T3DB (www.t3db.ca) for toxin information including
chemical properties, targets, health effects, and mechanisms of toxicity.

API: https://www.t3db.ca/toxins/{id}.xml
No authentication required.

Reference: Wishart et al., Nucleic Acids Res. 2015
"""

import requests
import xmltodict
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


T3DB_BASE = "https://www.t3db.ca"


@register_tool("T3DBTool")
class T3DBTool(BaseTool):
    """
    Tool for querying the Toxin and Toxin-Target Database (T3DB).

    Supported operations:
    - get_toxin: Get detailed toxin info by T3DB ID
    - search_toxins: Search toxins by name
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_toxin"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "ToolUniverse/1.0", "Accept": "application/xml"}
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.endpoint_type == "get_toxin":
                return self._get_toxin(arguments)
            elif self.endpoint_type == "search_toxins":
                return self._search_toxins(arguments)
            return {
                "status": "error",
                "error": f"Unknown endpoint: {self.endpoint_type}",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "T3DB API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to T3DB"}
        except Exception as e:
            return {"status": "error", "error": f"T3DB error: {str(e)}"}

    def _get_toxin(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        toxin_id = arguments.get("toxin_id") or arguments.get("id", "")
        if not toxin_id:
            return {
                "status": "error",
                "error": "toxin_id is required (e.g., 'T3D0001')",
            }

        if not toxin_id.startswith("T3D"):
            toxin_id = f"T3D{toxin_id.zfill(4)}"

        resp = self.session.get(
            f"{T3DB_BASE}/toxins/{toxin_id}.xml", timeout=self.timeout
        )
        if resp.status_code == 404:
            return {"status": "error", "error": f"Toxin {toxin_id} not found"}
        resp.raise_for_status()

        data = xmltodict.parse(resp.text)
        compound = data.get("compound", {})

        # Extract targets — T3DB stores targets as text with embedded UniProt IDs
        import re

        targets = []
        target_text = compound.get("target", "")
        if isinstance(target_text, str) and target_text.strip():
            # Parse "Protein Name (UniProt_ID)" patterns
            entries = re.findall(
                r"([^()\n]+?)\s*\(([A-Z][A-Z0-9]{4}[0-9])\)", target_text
            )
            for name, uniprot in entries:
                targets.append({"name": name.strip(), "uniprot_id": uniprot})
        elif isinstance(target_text, dict):
            targets.append(
                {
                    "name": target_text.get("name"),
                    "uniprot_id": target_text.get("uniprot-id"),
                }
            )

        return {
            "status": "success",
            "data": {
                "id": toxin_id,
                "name": compound.get("common-name"),
                "description": (compound.get("description") or "")[:500],
                "cas": compound.get("cas"),
                "pubchem_id": compound.get("pubchem-id"),
                "formula": compound.get("chemical-formula"),
                "weight": compound.get("weight"),
                "route_of_exposure": compound.get("route-of-exposure"),
                "mechanism_of_toxicity": (compound.get("mechanism-of-toxicity") or "")[
                    :500
                ],
                "health_effects": (compound.get("health-effects") or "")[:500],
                "targets": targets,
            },
            "metadata": {"source": "T3DB", "toxin_id": toxin_id},
        }

    def _search_toxins(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query") or arguments.get("name", "")
        if not query:
            return {"status": "error", "error": "query is required"}

        # T3DB doesn't have a search API — use the unison search page
        resp = self.session.get(
            f"{T3DB_BASE}/unearth/q",
            params={"query": query, "searcher": "toxins", "button": ""},
            timeout=self.timeout,
        )

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"T3DB search returned HTTP {resp.status_code}. "
                "Try searching by T3DB ID directly (e.g., T3D0001).",
            }

        # Parse HTML to extract toxin IDs and names
        import re

        ids = re.findall(r'href="/toxins/(T3D\d+)"', resp.text)
        names = re.findall(r'<td class="name"[^>]*>([^<]+)</td>', resp.text)

        results = []
        for i, tid in enumerate(ids[:10]):
            results.append(
                {
                    "id": tid,
                    "name": names[i] if i < len(names) else None,
                }
            )

        if not results:
            # Fallback: try extracting from result links
            links = re.findall(r'href="/toxins/(T3D\d+)"[^>]*>([^<]+)<', resp.text)
            for tid, name in links[:10]:
                results.append({"id": tid, "name": name.strip()})

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "query": query,
                "returned": len(results),
                "source": "T3DB",
                "note": "Use T3DB_get_toxin with the ID for detailed info",
            },
        }
