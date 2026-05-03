"""
PathwayCommons Tool - Unified Pathway and Interaction Database

Provides access to Pathway Commons REST API (PC2) for searching pathways,
retrieving pathway details, and querying gene interaction neighborhoods
across 22 integrated pathway/interaction databases including Reactome,
KEGG, WikiPathways, PID, BioGRID, IntAct, and more.

API base: https://www.pathwaycommons.org/pc2/
No authentication required.

Reference: Cerami et al., Nucleic Acids Res. 2011; Rodchenkov et al., Nucleic Acids Res. 2020
"""

import requests
from typing import Dict, Any, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool


PC2_BASE_URL = "https://www.pathwaycommons.org/pc2"


@register_tool("PathwayCommonsTool")
class PathwayCommonsTool(BaseTool):
    """
    Tool for querying Pathway Commons (PC2) unified pathway/interaction database.

    Supported operations:
    - search: Search for pathways, interactions, or molecular entities by gene/keyword
    - get_pathway: Get pathway details by URI
    - get_neighborhood: Get interaction neighborhood for a gene (SIF format)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 120

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = (
            arguments.get("operation")
            or self.tool_config.get("fields", {}).get("operation")
            or self.get_schema_const_operation()
        )
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "search": self._search,
            "get_pathway": self._get_pathway,
            "get_neighborhood": self._get_neighborhood,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "PathwayCommons API request timed out"}
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to PathwayCommons API",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "PathwayCommons error: {}".format(str(e)),
            }

    def _search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search PathwayCommons for pathways/interactions by gene or keyword."""
        query = arguments.get("query") or arguments.get("q")
        if not query:
            return {"status": "error", "error": "Missing required parameter: query"}

        params = {"q": query, "format": "json"}

        entity_type = arguments.get("type")
        if entity_type:
            params["type"] = entity_type

        datasource = arguments.get("datasource")
        if datasource:
            params["datasource"] = datasource

        organism = arguments.get("organism")
        if organism:
            params["organism"] = organism

        page = arguments.get("page")
        if page is not None:
            params["page"] = page

        response = self.session.get(
            "{}/search".format(PC2_BASE_URL), params=params, timeout=self.timeout
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "error": "PathwayCommons search returned HTTP {}".format(
                    response.status_code
                ),
            }

        data = response.json()
        hits = data.get("searchHit", [])
        results = []
        for hit in hits:
            results.append(
                {
                    "uri": hit.get("uri"),
                    "name": hit.get("name"),
                    "biopax_class": hit.get("biopaxClass"),
                    "data_source": hit.get("dataSource", []),
                    "organism": hit.get("organism", []),
                    "pathway": hit.get("pathway", []),
                    "num_participants": hit.get("numParticipants"),
                    "num_processes": hit.get("numProcesses"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_hits": data.get("numHits", 0),
                "max_hits_per_page": data.get("maxHitsPerPage", 100),
                "page": data.get("pageNo", 0),
                "query": query,
            },
        }

    def _traverse(self, uri: str, path: str) -> Optional[list]:
        """Helper: call the PC2 traverse endpoint."""
        params = {"uri": uri, "path": path}
        resp = self.session.get(
            "{}/traverse".format(PC2_BASE_URL), params=params, timeout=self.timeout
        )
        if resp.status_code != 200:
            return None
        data = resp.json()
        entries = data.get("traverseEntry", [])
        if entries:
            return entries[0].get("value", [])
        return []

    def _get_pathway(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get pathway details by URI from PathwayCommons using traverse API."""
        uri = arguments.get("uri")
        if not uri:
            return {"status": "error", "error": "Missing required parameter: uri"}

        # Get pathway metadata via traverse endpoint (fast, reliable)
        name = self._traverse(uri, "Pathway/displayName")
        comment = self._traverse(uri, "Pathway/comment")
        organism = self._traverse(uri, "Pathway/organism/displayName")
        data_source = self._traverse(uri, "Pathway/dataSource/displayName")
        sub_pathways = self._traverse(
            uri, "Pathway/pathwayComponent:Pathway/displayName"
        )
        participants = self._traverse(
            uri, "Pathway/pathwayComponent/participant/displayName"
        )

        if name is None:
            return {
                "status": "error",
                "error": "Failed to retrieve pathway data for URI: {}".format(uri),
            }

        result = {
            "pathway": {
                "uri": uri,
                "name": name[0] if name else None,
                "description": comment[0] if comment else None,
                "organism": organism[0] if organism else None,
                "data_source": data_source[0] if data_source else None,
            },
            "sub_pathways": sub_pathways or [],
            "participants": participants or [],
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "uri": uri,
                "sub_pathway_count": len(sub_pathways or []),
                "participant_count": len(participants or []),
            },
        }

    def _get_neighborhood(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get interaction neighborhood for a gene from PathwayCommons (SIF format)."""
        gene = arguments.get("gene") or arguments.get("source")
        if not gene:
            return {"status": "error", "error": "Missing required parameter: gene"}

        limit = arguments.get("limit", 1)
        datasource = arguments.get("datasource")

        params = {
            "source": gene,
            "kind": "neighborhood",
            "format": "TXT",
            "limit": limit,
        }
        if datasource:
            params["datasource"] = datasource

        response = self.session.get(
            "{}/graph".format(PC2_BASE_URL), params=params, timeout=self.timeout
        )

        if response.status_code != 200:
            return {
                "status": "error",
                "error": "PathwayCommons graph returned HTTP {}".format(
                    response.status_code
                ),
            }

        text = response.text.strip()
        if not text:
            return {
                "status": "success",
                "data": {"interactions": [], "gene": gene},
                "metadata": {"gene": gene, "interaction_count": 0},
            }

        lines = text.split("\n")
        header = None
        interactions = []

        for line in lines:
            fields = line.split("\t")
            if header is None:
                header = fields
                continue
            if len(fields) >= 3:
                interaction = {
                    "participant_a": fields[0],
                    "interaction_type": fields[1],
                    "participant_b": fields[2],
                }
                if len(fields) > 3:
                    interaction["data_source"] = fields[3] if fields[3] else None
                if len(fields) > 4:
                    interaction["pubmed_ids"] = fields[4] if fields[4] else None
                if len(fields) > 5:
                    interaction["pathway_names"] = fields[5] if fields[5] else None
                interactions.append(interaction)

        # Collect unique interaction types and partners
        interaction_types = {}
        partners = set()
        for ix in interactions:
            itype = ix["interaction_type"]
            interaction_types[itype] = interaction_types.get(itype, 0) + 1
            if ix["participant_a"].upper() != gene.upper():
                partners.add(ix["participant_a"])
            if ix["participant_b"].upper() != gene.upper():
                partners.add(ix["participant_b"])

        max_return = arguments.get("max_results", 100)
        return {
            "status": "success",
            "data": {
                "gene": gene,
                "interactions": interactions[:max_return],
                "interaction_type_counts": interaction_types,
                "unique_partners": len(partners),
            },
            "metadata": {
                "gene": gene,
                "total_interactions": len(interactions),
                "returned": min(len(interactions), max_return),
                "limit": limit,
            },
        }
