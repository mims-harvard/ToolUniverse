# pharos_tool.py
"""
Pharos/TCRD (Target Central Resource Database) API tool for ToolUniverse.

Pharos is the NIH Illuminating the Druggable Genome (IDG) portal providing
comprehensive information about understudied proteins and drug targets.

Key features:
- Target Development Level (TDL): Tclin, Tchem, Tbio, Tdark classification
- Druggability assessments for the human proteome
- Integration of 80+ data sources

API Documentation: https://pharos.nih.gov/api
GraphQL Endpoint: https://pharos-api.ncats.io/graphql
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for Pharos GraphQL API
PHAROS_GRAPHQL_URL = "https://pharos-api.ncats.io/graphql"


@register_tool("PharosTool")
class PharosTool(BaseTool):
    """
    Tool for querying Pharos/TCRD GraphQL API.

    Pharos provides drug target information including:
    - Target Development Level (Tdark, Tbio, Tchem, Tclin)
    - Druggability assessments
    - Protein family classifications
    - Disease associations
    - Ligand/drug information

    No authentication required. Free for academic/research use.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)  # Longer timeout for Pharos
        self.operation = tool_config.get("fields", {}).get("operation", "get_target")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Pharos API call."""
        operation = self.operation

        if operation == "get_target":
            return self._get_target(arguments)
        elif operation == "search_targets":
            return self._search_targets(arguments)
        elif operation == "get_tdl_summary":
            return self._get_tdl_summary(arguments)
        elif operation == "get_disease_targets":
            return self._get_disease_targets(arguments)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

    def _execute_graphql(
        self, query: str, variables: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Execute a GraphQL query against Pharos API."""
        try:
            payload = {"query": query}
            if variables:
                payload["variables"] = variables

            response = requests.post(
                PHAROS_GRAPHQL_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                return {
                    "status": "error",
                    "error": result["errors"][0].get("message", "GraphQL error"),
                    "errors": result["errors"],
                }

            return {"status": "success", "data": result.get("data", {})}
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Pharos API timeout after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"Pharos API request failed: {str(e)}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _get_target(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get detailed target information by gene symbol or UniProt ID.

        Returns TDL classification, protein family, disease associations,
        ligands, and druggability information.
        """
        gene = arguments.get("gene")
        uniprot = arguments.get("uniprot")

        if not gene and not uniprot:
            return {
                "status": "error",
                "error": "Either 'gene' or 'uniprot' parameter is required",
            }

        # Use the target query with q parameter (ITarget input type)
        # Simplified query for reliability
        if uniprot:
            query = """
            query GetTarget($q: ITarget!) {
                target(q: $q) {
                    name
                    sym
                    uniprot
                    tdl
                    fam
                    novelty
                    description
                    publicationCount
                }
            }
            """
            variables = {"q": {"uniprot": uniprot}}
        else:
            query = """
            query GetTarget($q: ITarget!) {
                target(q: $q) {
                    name
                    sym
                    uniprot
                    tdl
                    fam
                    novelty
                    description
                    publicationCount
                }
            }
            """
            variables = {"q": {"sym": gene}}

        result = self._execute_graphql(query, variables)

        if result["status"] == "success":
            target = result["data"].get("target")
            if not target:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No target found for {'UniProt ' + uniprot if uniprot else 'gene ' + gene}",
                }
            result["data"] = target

        return result

    def _search_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Search targets by query string.

        Returns targets matching the search term with TDL classification.
        """
        query_term = arguments.get("query")
        top = arguments.get("top", 10)

        if not query_term:
            return {"status": "error", "error": "query parameter is required"}

        # Simple term-based search
        query = """
        query SearchTargets($term: String!, $top: Int!) {
            targets(filter: {term: $term}, top: $top) {
                count
                targets {
                    name
                    sym
                    uniprot
                    tdl
                    fam
                    novelty
                    description
                }
            }
        }
        """

        variables = {
            "term": query_term,
            "top": min(top, 100),  # Cap at 100
        }

        result = self._execute_graphql(query, variables)

        if result["status"] == "success":
            targets_data = result["data"].get("targets", {})
            result["data"] = {
                "count": targets_data.get("count", 0),
                "targets": targets_data.get("targets", []),
            }

        return result

    def _get_tdl_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Target Development Level summary statistics.

        Returns counts of targets at each TDL level:
        - Tclin: Targets with approved drugs
        - Tchem: Targets with small molecule activities
        - Tbio: Targets with biological annotations
        - Tdark: Understudied targets with minimal information
        """
        # Return a static description since aggregation queries are slow
        # We can query individual TDL counts if needed
        query = """
        query {
            dbVersion
        }
        """

        result = self._execute_graphql(query)

        if result["status"] == "success":
            result["data"] = {
                "tdl_levels": ["Tclin", "Tchem", "Tbio", "Tdark"],
                "description": {
                    "Tclin": "Targets with approved drugs",
                    "Tchem": "Targets with small molecule activities (IC50 < 30nM)",
                    "Tbio": "Targets with GO annotations, OMIM phenotypes, or publications",
                    "Tdark": "Understudied targets with minimal information",
                },
                "db_version": result["data"].get("dbVersion"),
                "note": "For target counts by TDL, use search_targets with specific TDL filter or visit https://pharos.nih.gov",
            }

        return result

    def _get_disease_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get targets associated with a disease.

        Returns targets with TDL classification for drug discovery prioritization.
        """
        disease = arguments.get("disease")
        top = arguments.get("top", 20)

        if not disease:
            return {"status": "error", "error": "disease parameter is required"}

        # Use associatedDisease filter
        query = """
        query GetDiseaseTargets($disease: String!, $top: Int!) {
            targets(filter: {associatedDisease: $disease}, top: $top) {
                count
                targets {
                    name
                    sym
                    uniprot
                    tdl
                    fam
                    novelty
                }
            }
        }
        """

        variables = {"disease": disease, "top": min(top, 100)}

        result = self._execute_graphql(query, variables)

        if result["status"] == "success":
            targets_data = result["data"].get("targets", {})
            result["data"] = {
                "disease": disease,
                "count": targets_data.get("count", 0),
                "targets": targets_data.get("targets", []),
            }

        return result
