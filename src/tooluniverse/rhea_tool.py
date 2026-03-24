# rhea_tool.py
"""
Rhea Biochemical Reactions database tool for ToolUniverse.

Rhea is an expert-curated knowledgebase of chemical and transport
reactions of biological interest from SIB Swiss Institute of Bioinformatics.
All reactions are linked to ChEBI (Chemical Entities of Biological Interest)
and EC numbers.

API: https://www.rhea-db.org/help/rest-api
Returns TSV format which is parsed to JSON by this tool.
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

RHEA_BASE_URL = "https://www.rhea-db.org/rhea"


@register_tool("RheaTool")
class RheaTool(BaseTool):
    """
    Tool for querying the Rhea biochemical reaction database.

    Rhea contains over 15,000 manually curated biochemical reactions,
    each linked to ChEBI compounds and EC enzyme numbers. The search
    API returns TSV which is parsed to structured JSON.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search_reactions")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Rhea API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Rhea API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Rhea API."}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Rhea API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Rhea: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Rhea endpoint."""
        if self.endpoint == "search_reactions":
            return self._search_reactions(arguments)
        elif self.endpoint == "search_by_ec":
            return self._search_by_ec(arguments)
        elif self.endpoint == "search_by_chebi":
            return self._search_by_chebi(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _parse_tsv(self, text: str) -> List[Dict[str, str]]:
        """Parse TSV response into list of dicts."""
        lines = text.strip().split("\n")
        if len(lines) < 2:
            return []

        headers = lines[0].split("\t")
        # Normalize header names
        header_map = {
            "Reaction identifier": "rhea_id",
            "Equation": "equation",
            "EC number": "ec_numbers",
            "ChEBI identifier": "chebi_ids",
        }
        normalized_headers = [
            header_map.get(h.strip(), h.strip().lower().replace(" ", "_"))
            for h in headers
        ]

        results = []
        for line in lines[1:]:
            if not line.strip():
                continue
            values = line.split("\t")
            row = {}
            for i, header in enumerate(normalized_headers):
                val = values[i].strip() if i < len(values) else ""
                row[header] = val
            results.append(row)

        return results

    def _search_reactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for biochemical reactions by name, compound, or keyword."""
        query = arguments.get("query", "")
        if not query:
            return {
                "status": "error",
                "error": "query parameter is required (e.g., 'glucose', 'ATP', 'kinase')",
            }

        limit = arguments.get("limit", 20)

        params = {
            "query": query,
            "columns": "rhea-id,equation,ec",
            "format": "tsv",
            "limit": min(limit, 50),
        }

        response = requests.get(RHEA_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        results = self._parse_tsv(response.text)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Rhea (SIB)",
                "query": query,
                "total_results": len(results),
            },
        }

    def _search_by_ec(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for reactions by EC (Enzyme Commission) number."""
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {
                "status": "error",
                "error": "ec_number parameter is required (e.g., 'EC:1.1.1.1', '3.5.1.50')",
            }

        # Normalize EC number format
        if not ec_number.startswith("EC:"):
            ec_number = f"EC:{ec_number}"

        limit = arguments.get("limit", 20)

        params = {
            "query": ec_number,
            "columns": "rhea-id,equation,ec",
            "format": "tsv",
            "limit": min(limit, 50),
        }

        response = requests.get(RHEA_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        results = self._parse_tsv(response.text)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Rhea (SIB)",
                "ec_number": ec_number,
                "total_results": len(results),
            },
        }

    def _search_by_chebi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for reactions involving a specific ChEBI compound."""
        chebi_id = arguments.get("chebi_id", "")
        if not chebi_id:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 'CHEBI:17234' for glucose)",
            }

        # Normalize ChEBI ID format
        if not chebi_id.startswith("CHEBI:"):
            chebi_id = f"CHEBI:{chebi_id}"

        limit = arguments.get("limit", 20)

        params = {
            "query": chebi_id,
            "columns": "rhea-id,equation,chebi-id,ec",
            "format": "tsv",
            "limit": min(limit, 50),
        }

        response = requests.get(RHEA_BASE_URL, params=params, timeout=self.timeout)
        response.raise_for_status()

        results = self._parse_tsv(response.text)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "Rhea (SIB)",
                "chebi_id": chebi_id,
                "total_results": len(results),
            },
        }
