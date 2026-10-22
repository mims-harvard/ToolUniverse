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
                "status": "error",
                "error": f"Reactome Content Service timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Reactome Content Service",
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                return {
                    "status": "error",
                    "error": f"Entity not found: {arguments.get('identifier', arguments.get('query', ''))}",
                }
            return {
                "status": "error",
                "error": f"Reactome Content Service HTTP error: {code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Reactome Content Service: {str(e)}",
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
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

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
                "status": "error",
                "error": "query parameter is required (e.g., 'apoptosis', 'TP53', 'cell cycle')",
            }

        species = arguments.get("species", "Homo sapiens")
        types = arguments.get("types", "Pathway")
        cluster = arguments.get("cluster", True)
        limit = min(max(int(arguments.get("limit", 30)), 1), 1000)
        offset = max(int(arguments.get("offset", 0)), 0)

        url = f"{REACTOME_CS_BASE_URL}/search/query"
        params = {
            "query": query,
            "species": species,
            "types": types,
            "cluster": str(cluster).lower(),
            # Reactome's documented offset key intentionally contains a space.
            "Start row": offset,
            "rows": limit,
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
        result_groups = []
        for group in results_groups:
            type_name = group.get("typeName", "Unknown")
            entries = group.get("entries", [])
            group_total = group.get("entriesCount")
            if not isinstance(group_total, int):
                group_total = len(entries)
            result_groups.append(
                {
                    "type": type_name,
                    "total": group_total,
                    "returned": len(entries),
                }
            )
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

        total = data.get("numberOfMatches")
        if not isinstance(total, int):
            total = len(all_entries)
        # With cluster=true, Reactome applies rows/start to each result group,
        # not to the flattened result list.  Advance by the requested row
        # count, otherwise summing all groups would skip records.
        has_more = any(
            offset + group["returned"] < group["total"] for group in result_groups
        )
        return {
            "status": "success",
            "data": {
                "query": query,
                "species": species,
                "types_searched": types,
                "total_results": total,
                "returned": len(all_entries),
                "limit": limit,
                "offset": offset,
                "has_more": has_more,
                "truncated": len(all_entries) < total,
                "next_offset": offset + limit if has_more else None,
                "result_groups": result_groups,
                "results": all_entries,
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
                "status": "error",
                "error": "identifier parameter is required (Reactome pathway stable ID, e.g., 'R-HSA-109581')",
            }

        url = f"{REACTOME_CS_BASE_URL}/data/pathway/{identifier}/containedEvents"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        events = response.json()

        # Fix-R18B-1: Reactome's containedEvents endpoint mixes full event
        # dicts with plain integer DB IDs for some sub-pathways -- confirmed
        # live for R-HSA-2219528 ("PI3K/AKT Signaling in Cancer"), where 2 of
        # its 3 real sub-pathways (R-HSA-5674400, R-HSA-2219530) came back as
        # bare ints. Silently skipping them (as before) both dropped real
        # sub-pathways from the hierarchy and made total_events disagree with
        # pathway_count + reaction_count. Batch-resolve any bare IDs via the
        # /data/query/ids endpoint (confirmed live it accepts a comma-joined
        # list and returns full records with schemaClass) instead of
        # discarding them.
        bare_ids = [e for e in events if not isinstance(e, dict)]
        resolved_by_id = {}
        if bare_ids:
            ids_response = requests.post(
                f"{REACTOME_CS_BASE_URL}/data/query/ids",
                headers={
                    "Accept": "application/json",
                    "Content-Type": "text/plain",
                },
                data=",".join(str(i) for i in bare_ids),
                timeout=self.timeout,
            )
            if ids_response.ok:
                for item in ids_response.json():
                    if isinstance(item, dict) and item.get("dbId") is not None:
                        resolved_by_id[item["dbId"]] = item

        pathways = []
        reactions = []
        for e in events:
            if not isinstance(e, dict):
                e = resolved_by_id.get(e)
                if e is None:
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

        reaction_limit = min(max(int(arguments.get("reaction_limit", 50)), 1), 1000)
        reaction_offset = max(int(arguments.get("reaction_offset", 0)), 0)
        reaction_page = reactions[
            reaction_offset : reaction_offset + reaction_limit
        ]
        has_more_reactions = reaction_offset + len(reaction_page) < len(reactions)
        return {
            "status": "success",
            "data": {
                "identifier": identifier,
                "total_events": len(events),
                "pathway_count": len(pathways),
                "reaction_count": len(reactions),
                "pathways": pathways,
                "reactions": reaction_page,
                "reactions_returned": len(reaction_page),
                "reaction_limit": reaction_limit,
                "reaction_offset": reaction_offset,
                "has_more_reactions": has_more_reactions,
                "reactions_truncated": len(reaction_page) < len(reactions),
                "next_reaction_offset": (
                    reaction_offset + len(reaction_page)
                    if has_more_reactions
                    else None
                ),
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
                "status": "error",
                "error": "identifier parameter is required (Reactome pathway stable ID, e.g., 'R-HSA-109581')",
            }

        url = f"{REACTOME_CS_BASE_URL}/data/query/enhanced/{identifier}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        # Extract sub-events (defensive: Reactome occasionally returns ints
        # in hasEvent for terminal references — only descend into dicts).
        sub_events = [
            {
                "stId": e.get("stId"),
                "name": e.get("displayName"),
                "schemaClass": e.get("schemaClass"),
            }
            for e in data.get("hasEvent", [])
            if isinstance(e, dict)
        ]

        # Extract literature
        literature = [
            {
                "title": ref.get("title"),
                "pubMedIdentifier": ref.get("pubMedIdentifier"),
                "year": ref.get("year"),
                "journal": ref.get("journal", {}).get("title")
                if isinstance(ref.get("journal"), dict)
                else None,
            }
            for ref in data.get("literatureReference", [])
            if isinstance(ref, dict)
        ]

        # Extract GO terms
        go_terms = []
        go_bp = data.get("goBiologicalProcess")
        if isinstance(go_bp, list):
            go_terms.extend(
                {"accession": g.get("accession"), "name": g.get("displayName")}
                for g in go_bp
                if isinstance(g, dict)
            )
        elif isinstance(go_bp, dict):
            go_terms.append(
                {"accession": go_bp.get("accession"), "name": go_bp.get("displayName")}
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
            "status": "success",
            "data": {
                "identifier": data.get("stId"),
                "name": data.get("displayName"),
                "species": data.get("speciesName"),
                "schemaClass": data.get("schemaClass"),
                "is_disease": data.get("isInDisease", False),
                "summation": summation if summation else None,
                "summation_characters": len(summation),
                "go_biological_process": go_terms if go_terms else None,
                "sub_events": sub_events,
                "literature_count": len(literature),
                "literature": literature,
            },
            "metadata": {
                "source": "Reactome Content Service - Enhanced Pathway",
                "identifier": identifier,
            },
        }
