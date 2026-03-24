# unichem_tool.py
"""
UniChem REST API tool for ToolUniverse.

UniChem is EBI's unified chemical structure cross-referencing service.
It maps compound identifiers across 40+ chemical databases including
ChEMBL, DrugBank, PDBe, PubChem, KEGG, ChEBI, and HMDB. Given a
chemical structure (InChIKey) or database ID, UniChem returns all
known cross-references instantly.

API: https://www.ebi.ac.uk/unichem/api/v1/
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNICHEM_BASE_URL = "https://www.ebi.ac.uk/unichem/api/v1"


@register_tool("UniChemTool")
class UniChemTool(BaseTool):
    """
    Tool for querying UniChem compound cross-referencing service.

    Maps chemical identifiers across 40+ databases using InChIKey,
    source compound IDs, or UCIs (UniChem Compound Identifiers).

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "search_compound"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniChem API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UniChem API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to UniChem API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"UniChem API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying UniChem: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "search_compound":
            return self._search_compound(arguments)
        elif self.endpoint_type == "list_sources":
            return self._list_sources(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _search_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search UniChem for a compound by InChIKey, sourceID, or UCI."""
        compound = arguments.get("compound", "")
        search_type = arguments.get("type", "inchikey")
        source_id = arguments.get("sourceID", None)

        if not compound:
            return {
                "status": "error",
                "error": "compound parameter is required (e.g., InChIKey 'BSYNRYMUTXBXSQ-UHFFFAOYSA-N')",
            }

        payload = {
            "compound": compound,
            "type": search_type,
        }
        if source_id is not None:
            payload["sourceID"] = source_id

        url = f"{UNICHEM_BASE_URL}/compounds"
        response = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # Extract compound info
        compounds = raw.get("compounds", [])
        if not compounds:
            return {
                "status": "success",
                "data": {
                    "inchi": None,
                    "inchikey": None,
                    "formula": None,
                    "source_count": 0,
                    "sources": [],
                },
                "metadata": {
                    "source": "UniChem",
                    "query": compound,
                    "endpoint": "compounds",
                },
            }

        first = compounds[0]
        inchi_data = first.get("inchi", {})
        inchi_str = (
            inchi_data.get("inchi", None) if isinstance(inchi_data, dict) else None
        )
        formula = (
            inchi_data.get("formula", None) if isinstance(inchi_data, dict) else None
        )

        sources_raw = first.get("sources", [])
        sources = []
        for s in sources_raw:
            sources.append(
                {
                    "source_name": s.get("shortName", ""),
                    "source_long_name": s.get("longName", ""),
                    "compound_id": s.get("compoundId", ""),
                    "url": s.get("url", None),
                }
            )

        # Derive InChIKey from InChI if not directly available
        if inchi_str:
            # Try to find it from sources or connectivity info
            for s in sources_raw:
                pass  # InChIKey might not be directly in compound response

        result = {
            "inchi": inchi_str,
            "inchikey": compound if search_type == "inchikey" else None,
            "formula": formula,
            "source_count": len(sources),
            "sources": sources,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UniChem",
                "query": compound,
                "endpoint": "compounds",
            },
        }

    def _list_sources(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all chemical database sources in UniChem."""
        url = f"{UNICHEM_BASE_URL}/sources/"
        response = requests.get(
            url,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        sources_raw = raw.get("sources", [])
        sources = []
        for s in sources_raw:
            sources.append(
                {
                    "source_id": s.get("sourceID", 0),
                    "name": s.get("name", ""),
                    "long_name": s.get("nameLong", s.get("nameLabel", "")),
                    "description": s.get("description", None),
                    "compound_count": s.get("UCICount", None),
                    "last_updated": s.get("lastUpdated", None),
                }
            )

        result = {
            "source_count": len(sources),
            "sources": sources,
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "UniChem",
                "query": "all_sources",
                "endpoint": "sources",
            },
        }
