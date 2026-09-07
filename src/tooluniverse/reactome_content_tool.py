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

        # Fix-R19-1: Reactome pages its search results and, when `rows` is not
        # sent, returns only its own default page of 10 -- so the tool could
        # never reach result 11 of a 455-hit query. Expose upstream's paging
        # controls. NOTE the offset parameter is literally named "Start row"
        # (with a space), confirmed in Reactome's own OpenAPI document
        # (https://reactome.org/ContentService/v3/api-docs -> /search/query ->
        # 'param: Start row integer - Start row') and confirmed live: sending
        # `start=5` is silently ignored and re-serves page 0, while
        # `Start row=5` serves entries 6-10. Anything that "looks right" here
        # fails silently, so keep the odd upstream spelling.
        rows = arguments.get("rows")
        start = arguments.get("start")
        if rows is not None and not (1 <= int(rows) <= 1000):
            return {
                "status": "error",
                "error": f"rows must be between 1 and 1000 (got {rows}); Reactome rejects larger pages",
            }
        if start is not None and int(start) < 0:
            return {
                "status": "error",
                "error": f"start must be >= 0 (got {start})",
            }

        url = f"{REACTOME_CS_BASE_URL}/search/query"
        params = {
            "query": query,
            "species": species,
            "types": types,
            "cluster": str(cluster).lower(),
        }
        if rows is not None:
            params["rows"] = int(rows)
        if start is not None:
            params["Start row"] = int(start)
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

        # Fix-R19-1: `total_results` is documented in this tool's return_schema
        # as "Total number of results", but was computed as len(all_entries)
        # over a single unpaginated upstream page -- i.e. it reported Reactome's
        # default page size of 10 for every query, no matter how many actually
        # matched. Reactome reports the real figure as `numberOfMatches` in
        # every search response (confirmed live: query='DNA repair',
        # species='Homo sapiens', types='Pathway' -> numberOfMatches 455 while
        # only 10 entries come back); it was parsed into `data` and thrown away.
        # Report the documented quantity, and say plainly how much of it the
        # caller is actually holding.
        limit = int(rows) if rows is not None else 30
        results = all_entries[:limit]
        offset = int(start) if start is not None else 0
        total_matches = data.get("numberOfMatches")
        if not isinstance(total_matches, int):
            total_matches = len(all_entries)

        result = {
            "status": "success",
            "data": {
                "query": query,
                "species": species,
                "types_searched": types,
                "count": len(results),
                "total_results": total_matches,
                "start": offset,
                "has_more": (offset + len(results)) < total_matches,
                "results": results,
            },
            "metadata": {
                "source": "Reactome Content Service - Search",
                "query": query,
            },
        }

        if result["data"]["has_more"]:
            result["truncated"] = True
            result["truncation_note"] = (
                f"Returned {len(results)} of {total_matches} Reactome entries matching "
                f"this query (starting at result {offset + 1}). This is a ranked slice, "
                f"not the full result set -- an entry absent here may still match. Pass "
                f"`rows` (up to 1000) to widen the page and `start` to move through it."
            )
        return result

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

        return {
            "status": "success",
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
