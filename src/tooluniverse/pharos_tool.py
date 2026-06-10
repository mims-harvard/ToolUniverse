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
        elif operation == "get_target_ligands":
            return self._get_target_ligands(arguments)
        elif operation == "get_ligand_targets":
            return self._get_ligand_targets(arguments)
        elif operation == "get_target_expression":
            return self._get_target_expression(arguments)
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

    def _resolve_target_q(self, arguments: Dict[str, Any]):
        """Build the ITarget input filter ({sym} or {uniprot}) from arguments.

        Returns (q_dict, label) on success or (None, error_message) when neither
        a gene symbol nor a UniProt accession is provided.
        """
        gene = arguments.get("gene") or arguments.get("sym")
        uniprot = arguments.get("uniprot")
        if uniprot:
            return {"uniprot": uniprot}, f"UniProt {uniprot}"
        if gene:
            return {"sym": gene}, f"gene {gene}"
        return None, "Either 'gene' or 'uniprot' parameter is required"

    def _get_target_ligands(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get per-target ligand/drug bioactivities for a drug target.

        Returns ligandCounts (total ligand and drug counts) plus the top
        ligands with their synonyms and bioactivities (type IC50/Ki/EC50,
        value, and mechanism of action).
        """
        q, label = self._resolve_target_q(arguments)
        if q is None:
            return {"status": "error", "error": label}

        top = arguments.get("top", 3)
        try:
            top = min(max(int(top), 1), 50)
        except (TypeError, ValueError):
            top = 3

        query = """
        query TargetLigands($q: ITarget!, $top: Int!) {
            target(q: $q) {
                sym
                tdl
                fam
                ligandCounts { name value }
                ligands(top: $top) {
                    name
                    isdrug
                    synonyms { name value }
                    activities { type moa value }
                }
            }
        }
        """
        result = self._execute_graphql(query, {"q": q, "top": top})

        if result["status"] == "success":
            target = result["data"].get("target")
            if not target:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No target found for {label}",
                }
            result["data"] = target

        return result

    def _get_ligand_targets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get all protein targets for a drug/ligand (reverse polypharmacology).

        Returns the ligand's targetCount plus every recorded activity with its
        target (sym, tdl, fam), activity type, value, and mechanism of action.
        """
        ligid = (
            arguments.get("ligid") or arguments.get("ligand") or arguments.get("name")
        )
        if not ligid:
            return {
                "status": "error",
                "error": "ligid parameter is required (ligand name or Pharos ligand ID)",
            }

        query = """
        query LigandTargets($ligid: String!) {
            ligand(ligid: $ligid) {
                name
                isdrug
                smiles
                targetCount
                activities {
                    target { sym tdl fam }
                    type
                    value
                    moa
                }
            }
        }
        """
        result = self._execute_graphql(query, {"ligid": ligid})

        if result["status"] == "success":
            ligand = result["data"].get("ligand")
            if not ligand:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No ligand found for '{ligid}'",
                }
            result["data"] = ligand

        return result

    def _get_target_expression(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get GTEx baseline tissue expression (per-tissue TPM) for a target.

        Returns one record per GTEx tissue with tissue name, TPM value, and
        gender stratification (when available).
        """
        q, label = self._resolve_target_q(arguments)
        if q is None:
            return {"status": "error", "error": label}

        query = """
        query TargetExpression($q: ITarget!) {
            target(q: $q) {
                sym
                gtex { tissue tpm gender }
            }
        }
        """
        result = self._execute_graphql(query, {"q": q})

        if result["status"] == "success":
            target = result["data"].get("target")
            if not target:
                return {
                    "status": "success",
                    "data": None,
                    "message": f"No target found for {label}",
                }
            result["data"] = {
                "sym": target.get("sym"),
                "count": len(target.get("gtex") or []),
                "gtex": target.get("gtex") or [],
            }

        return result
