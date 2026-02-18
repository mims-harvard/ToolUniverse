# reactome_content_tool.py
"""
Reactome Content Service tool for ToolUniverse.

Provides access to Reactome Content Service REST API for searching
pathways/reactions and retrieving detailed pathway event hierarchies.

API: https://reactome.org/ContentService/
No authentication required. Free public access.
"""

import requests
import re
from typing import Dict, Any, Optional
from .base_tool import BaseTool


REACTOME_CS_BASE_URL = "https://reactome.org/ContentService"


class ReactomeContentTool(BaseTool):
    """
    Tool for Reactome Content Service providing pathway search,
    contained event retrieval, and enhanced pathway details.

    Complements existing Reactome tools by adding free-text search
    and hierarchical event decomposition.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "search")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Reactome Content Service API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "error": f"Reactome Content Service timed out after {self.timeout}s"
            }
        except requests.exceptions.ConnectionError:
            return {"error": "Failed to connect to Reactome Content Service"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "error": f"Entity not found: {arguments.get('identifier', arguments.get('query', ''))}"
                }
            return {"error": f"Reactome Content Service HTTP error: {code}"}
        except Exception as e:
            return {
                "error": f"Unexpected error querying Reactome Content Service: {str(e)}"
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "search":
            return self._search(arguments)
        elif self.endpoint == "contained_events":
            return self._get_contained_events(arguments)
        elif self.endpoint == "enhanced_pathway":
            return self._get_enhanced_pathway(arguments)
        else:
            return {"error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _strip_html(text: Optional[str]) -> Optional[str]:
        """Remove HTML tags from text."""
        if not text:
            return text
        return re.sub(r"<[^>]+>", "", text)

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search Reactome for pathways, reactions, and other entities."""
        query = arguments.get("query", "")
        if not query:
            return {
                "error": "query parameter is required (e.g., 'apoptosis', 'TP53', 'cell cycle')"
            }

        species = arguments.get("species", "Homo sapiens")
        types = arguments.get("types", "Pathway")
        cluster = arguments.get("cluster", True)

        url = f"{REACTOME_CS_BASE_URL}/search/query"
        params = {
            "query": query,
            "species": species,
            "types": types,
            "cluster": str(cluster).lower(),
        }
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results_groups = data.get("results", [])
        all_entries = []
        for group in results_groups:
            type_name = group.get("typeName", "Unknown")
            entries = group.get("entries", [])
            for entry in entries:
                all_entries.append(
                    {
                        "type": type_name,
                        "stId": entry.get("stId"),
                        "name": self._strip_html(entry.get("name", "")),
                        "species": entry.get("species", []),
                        "compartments": entry.get("compartmentNames", []),
                        "is_disease": entry.get("isDisease", False),
                    }
                )

        return {
            "data": {
                "query": query,
                "species": species,
                "types_searched": types,
                "total_results": len(all_entries),
                "results": all_entries[:30],
            },
            "metadata": {
                "source": "Reactome Content Service - Search",
                "query": query,
            },
        }

    def _get_contained_events(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get all events (sub-pathways and reactions) contained in a pathway."""
        identifier = arguments.get("identifier", "")
        if not identifier:
            return {
                "error": "identifier parameter is required (Reactome pathway stable ID, e.g., 'R-HSA-109581')"
            }

        url = f"{REACTOME_CS_BASE_URL}/data/pathway/{identifier}/containedEvents"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        events = response.json()

        # Count event types (some elements may be plain integer DB IDs, skip those)
        pathways = []
        reactions = []
        for e in events:
            if not isinstance(e, dict):
                continue
            schema = e.get("schemaClass", "")
            entry = {
                "stId": e.get("stId"),
                "name": e.get("displayName"),
                "schemaClass": schema,
                "is_disease": e.get("isInDisease", False),
            }
            if schema == "Pathway":
                pathways.append(entry)
            else:
                reactions.append(entry)

        return {
            "data": {
                "identifier": identifier,
                "total_events": len(events),
                "pathway_count": len(pathways),
                "reaction_count": len(reactions),
                "pathways": pathways,
                "reactions": reactions[:50],
            },
            "metadata": {
                "source": "Reactome Content Service - Contained Events",
                "identifier": identifier,
            },
        }

    def _get_enhanced_pathway(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get enhanced pathway details including literature, GO terms, and sub-events."""
        identifier = arguments.get("identifier", "")
        if not identifier:
            return {
                "error": "identifier parameter is required (Reactome pathway stable ID, e.g., 'R-HSA-109581')"
            }

        url = f"{REACTOME_CS_BASE_URL}/data/query/enhanced/{identifier}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract sub-events
        sub_events = []
        for e in data.get("hasEvent", []):
            sub_events.append(
                {
                    "stId": e.get("stId"),
                    "name": e.get("displayName"),
                    "schemaClass": e.get("schemaClass"),
                }
            )

        # Extract literature
        literature = []
        for ref in data.get("literatureReference", []):
            literature.append(
                {
                    "title": ref.get("title"),
                    "pubMedIdentifier": ref.get("pubMedIdentifier"),
                    "year": ref.get("year"),
                    "journal": ref.get("journal", {}).get("title")
                    if isinstance(ref.get("journal"), dict)
                    else None,
                }
            )

        # Extract GO terms
        go_terms = []
        go_bp = data.get("goBiologicalProcess")
        if go_bp:
            if isinstance(go_bp, list):
                for g in go_bp:
                    go_terms.append(
                        {
                            "accession": g.get("accession"),
                            "name": g.get("displayName"),
                        }
                    )
            elif isinstance(go_bp, dict):
                go_terms.append(
                    {
                        "accession": go_bp.get("accession"),
                        "name": go_bp.get("displayName"),
                    }
                )

        # Extract summation (description)
        summation = ""
        summ_list = data.get("summation", [])
        if summ_list:
            texts = [
                self._strip_html(s.get("text", "")) for s in summ_list if s.get("text")
            ]
            summation = " ".join(texts)

        return {
            "data": {
                "identifier": data.get("stId"),
                "name": data.get("displayName"),
                "species": data.get("speciesName"),
                "schemaClass": data.get("schemaClass"),
                "is_disease": data.get("isInDisease", False),
                "summation": summation[:2000] if summation else None,
                "go_biological_process": go_terms if go_terms else None,
                "sub_events": sub_events,
                "literature": literature[:20],
            },
            "metadata": {
                "source": "Reactome Content Service - Enhanced Pathway",
                "identifier": identifier,
            },
        }
