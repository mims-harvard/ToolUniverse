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

import re

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

RHEA_BASE_URL = "https://www.rhea-db.org/rhea"

# Rhea's REST API honours `limit` but ignores `offset`, so paging is done
# client-side by fetching offset+limit rows and slicing.
MAX_ROWS_PER_REQUEST = 1000


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

    @staticmethod
    def _normalize_prefixed_id(value: str, prefix: str) -> str:
        """Normalize an identifier to Rhea's ``PREFIX:local`` query form.

        Accepts the spellings that appear in OWL/OBO files, spreadsheets and
        papers -- ``CHEBI_15724``, ``chebi:15724``, ``EC 1.1.1.1``, a bare
        ``15724`` -- and returns ``CHEBI:15724`` / ``EC:1.1.1.1``. Previously the
        check was a case-sensitive ``startswith``, so ``CHEBI_15724`` became
        ``CHEBI:CHEBI_15724`` (0 results reported as a success) and lowercase
        prefixes produced an upstream HTTP 500.
        """
        text = str(value).strip()
        local = re.sub(rf"^{re.escape(prefix)}\s*[:_ ]?\s*", "", text, flags=re.I)
        return f"{prefix}:{local.strip()}"

    def _total_for_query(self, query: str) -> Optional[int]:
        """Number of Rhea reactions matching `query`, independent of page size.

        Rhea exposes no count endpoint, so this fetches the single ``rhea-id``
        column unlimited -- cheap, and the only way to report a real total
        rather than echoing back the requested ``limit``.
        """
        try:
            response = requests.get(
                RHEA_BASE_URL,
                params={"query": query, "columns": "rhea-id", "format": "tsv"},
                timeout=self.timeout,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None
        return len(self._parse_tsv(response.text))

    def _paged_search(
        self,
        query: str,
        columns: str,
        arguments: Dict[str, Any],
        extra_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Run a Rhea search, reporting an honest total and supporting paging."""
        try:
            limit = int(arguments.get("limit", 20))
            offset = int(arguments.get("offset", 0))
        except (TypeError, ValueError):
            return {
                "status": "error",
                "error": (
                    "limit and offset must be integers, got "
                    f"limit={arguments.get('limit')!r}, "
                    f"offset={arguments.get('offset')!r}"
                ),
            }
        if limit < 1:
            return {"status": "error", "error": f"limit must be >= 1, got {limit}"}
        offset = max(offset, 0)

        total = self._total_for_query(query)

        # Rhea ignores `offset`, so fetch through the requested window and slice.
        fetch = min(offset + limit, MAX_ROWS_PER_REQUEST)
        response = requests.get(
            RHEA_BASE_URL,
            params={
                "query": query,
                "columns": columns,
                "format": "tsv",
                "limit": fetch,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()

        page = self._parse_tsv(response.text)[offset : offset + limit]

        metadata = {
            "source": "Rhea (SIB)",
            # Size of the whole matching result set, not of this page.
            "total_results": total,
            "returned": len(page),
            "offset": offset,
            "limit": limit,
            "has_more": (
                offset + len(page) < total if isinstance(total, int) else None
            ),
            "max_rows_per_request": MAX_ROWS_PER_REQUEST,
        }
        metadata.update(extra_metadata)

        return {"status": "success", "data": page, "metadata": metadata}

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

        return self._paged_search(
            query=query,
            columns="rhea-id,equation,ec",
            arguments=arguments,
            extra_metadata={"query": query},
        )

    def _search_by_ec(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for reactions by EC (Enzyme Commission) number."""
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {
                "status": "error",
                "error": "ec_number parameter is required (e.g., 'EC:1.1.1.1', '3.5.1.50')",
            }

        ec_number = self._normalize_prefixed_id(ec_number, "EC")

        return self._paged_search(
            query=ec_number,
            columns="rhea-id,equation,ec",
            arguments=arguments,
            extra_metadata={"ec_number": ec_number},
        )

    def _search_by_chebi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for reactions involving a specific ChEBI compound."""
        chebi_id = arguments.get("chebi_id", "")
        if not chebi_id:
            return {
                "status": "error",
                "error": "chebi_id parameter is required (e.g., 'CHEBI:17234' for glucose)",
            }

        chebi_id = self._normalize_prefixed_id(chebi_id, "CHEBI")

        return self._paged_search(
            query=chebi_id,
            columns="rhea-id,equation,chebi-id,ec",
            arguments=arguments,
            extra_metadata={"chebi_id": chebi_id},
        )
