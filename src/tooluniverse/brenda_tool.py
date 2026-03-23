"""
BRENDA Enzyme Database API tool for ToolUniverse.

BRENDA is the largest enzyme database containing functional data like
Km, Vmax, turnover numbers, and inhibitor information.

API: SPARQL endpoint at https://sparql.dsmz.de/brenda
No authentication required.
"""

import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# BRENDA SPARQL endpoint (no auth required)
BRENDA_SPARQL_URL = "https://sparql.dsmz.de/brenda"


@register_tool("BRENDATool")
class BRENDATool(BaseTool):
    """
    Tool for querying BRENDA enzyme database.

    BRENDA provides:
    - Enzyme kinetic parameters (Km, kcat, Ki)
    - Substrate/product information
    - Enzyme inhibitors and activators
    - Organism-specific data

    Uses BRENDA SPARQL endpoint. No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 60)
        self.parameter = tool_config.get("parameter", {})
        self.sparql_url = BRENDA_SPARQL_URL

    def _make_sparql_query(self, query: str) -> Dict[str, Any]:
        """Execute a SPARQL query against BRENDA endpoint."""
        try:
            response = requests.get(
                self.sparql_url,
                params={"query": query, "format": "json"},
                headers={"Accept": "application/sparql-results+json"},
                timeout=self.timeout,
            )
            response.raise_for_status()
            # Feature-84B-006: endpoint sometimes returns HTML instead of JSON
            content_type = response.headers.get("Content-Type", "")
            if "html" in content_type or response.text.strip().startswith("<!"):
                raise Exception(
                    "BRENDA SPARQL endpoint (sparql.dsmz.de/brenda) is currently "
                    "returning HTML instead of JSON results. The endpoint may be "
                    "temporarily unavailable. Try again later or use the BRENDA "
                    "website directly: https://www.brenda-enzymes.org/"
                )
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"SPARQL query failed: {str(e)}")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute BRENDA API call based on operation type."""
        operation = arguments.get("operation", "")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()

        if operation == "get_km":
            return self._get_km(arguments)
        elif operation == "get_kcat":
            return self._get_kcat(arguments)
        elif operation == "get_inhibitors":
            return self._get_inhibitors(arguments)
        elif operation == "get_enzyme_info":
            return self._get_enzyme_info(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: get_km, get_kcat, get_inhibitors, get_enzyme_info",
            }

    def _get_km(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get Km (Michaelis constant) values for an enzyme.

        Args:
            arguments: Dict containing:
                - ec_number: EC number (e.g., 1.1.1.1 for alcohol dehydrogenase)
                - organism: Optional organism filter
        """
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}

        organism = arguments.get("organism", "")

        try:
            # Build SPARQL query for Km values
            organism_filter = (
                f'FILTER(CONTAINS(LCASE(STR(?organism)), "{organism.lower()}"))'
                if organism
                else ""
            )

            query = f"""
            PREFIX brenda: <http://brenda-enzymes.org/brenda/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?km ?substrate ?organism ?comment
            WHERE {{
                ?enzyme brenda:ecNumber "{ec_number}" .
                ?enzyme brenda:kmValue ?kmEntry .
                ?kmEntry brenda:kmValue ?km .
                OPTIONAL {{ ?kmEntry brenda:substrate ?substrate }}
                OPTIONAL {{ ?kmEntry brenda:organism ?organism }}
                OPTIONAL {{ ?kmEntry brenda:commentary ?comment }}
                {organism_filter}
            }}
            LIMIT 100
            """

            result = self._make_sparql_query(query)

            # Parse SPARQL results
            km_values = []
            if "results" in result and "bindings" in result["results"]:
                for binding in result["results"]["bindings"]:
                    km_values.append(
                        {
                            "km_value": binding.get("km", {}).get("value", ""),
                            "substrate": binding.get("substrate", {}).get("value", ""),
                            "organism": binding.get("organism", {}).get("value", ""),
                            "comment": binding.get("comment", {}).get("value", ""),
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism if organism else "all",
                    "km_values": km_values,
                    "count": len(km_values),
                },
                "metadata": {
                    "source": "BRENDA SPARQL",
                    "parameter": "Km (Michaelis constant)",
                    "unit": "mM",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_kcat(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get kcat (turnover number) values for an enzyme.

        Args:
            arguments: Dict containing:
                - ec_number: EC number
                - organism: Optional organism filter
        """
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}

        organism = arguments.get("organism", "")

        try:
            organism_filter = (
                f'FILTER(CONTAINS(LCASE(STR(?organism)), "{organism.lower()}"))'
                if organism
                else ""
            )

            query = f"""
            PREFIX brenda: <http://brenda-enzymes.org/brenda/>

            SELECT ?kcat ?substrate ?organism ?comment
            WHERE {{
                ?enzyme brenda:ecNumber "{ec_number}" .
                ?enzyme brenda:turnoverNumber ?kcatEntry .
                ?kcatEntry brenda:kcatValue ?kcat .
                OPTIONAL {{ ?kcatEntry brenda:substrate ?substrate }}
                OPTIONAL {{ ?kcatEntry brenda:organism ?organism }}
                OPTIONAL {{ ?kcatEntry brenda:commentary ?comment }}
                {organism_filter}
            }}
            LIMIT 100
            """

            result = self._make_sparql_query(query)

            kcat_values = []
            if "results" in result and "bindings" in result["results"]:
                for binding in result["results"]["bindings"]:
                    kcat_values.append(
                        {
                            "kcat_value": binding.get("kcat", {}).get("value", ""),
                            "substrate": binding.get("substrate", {}).get("value", ""),
                            "organism": binding.get("organism", {}).get("value", ""),
                            "comment": binding.get("comment", {}).get("value", ""),
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism if organism else "all",
                    "kcat_values": kcat_values,
                    "count": len(kcat_values),
                },
                "metadata": {
                    "source": "BRENDA SPARQL",
                    "parameter": "kcat (turnover number)",
                    "unit": "1/s",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_inhibitors(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get inhibitor data for an enzyme.

        Args:
            arguments: Dict containing:
                - ec_number: EC number
                - organism: Optional organism filter
        """
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}

        organism = arguments.get("organism", "")

        try:
            organism_filter = (
                f'FILTER(CONTAINS(LCASE(STR(?organism)), "{organism.lower()}"))'
                if organism
                else ""
            )

            query = f"""
            PREFIX brenda: <http://brenda-enzymes.org/brenda/>

            SELECT ?inhibitor ?ki ?organism ?comment
            WHERE {{
                ?enzyme brenda:ecNumber "{ec_number}" .
                ?enzyme brenda:inhibitor ?inhEntry .
                ?inhEntry brenda:inhibitorName ?inhibitor .
                OPTIONAL {{ ?inhEntry brenda:kiValue ?ki }}
                OPTIONAL {{ ?inhEntry brenda:organism ?organism }}
                OPTIONAL {{ ?inhEntry brenda:commentary ?comment }}
                {organism_filter}
            }}
            LIMIT 100
            """

            result = self._make_sparql_query(query)

            inhibitors = []
            if "results" in result and "bindings" in result["results"]:
                for binding in result["results"]["bindings"]:
                    inhibitors.append(
                        {
                            "inhibitor": binding.get("inhibitor", {}).get("value", ""),
                            "ki_value": binding.get("ki", {}).get("value", ""),
                            "organism": binding.get("organism", {}).get("value", ""),
                            "comment": binding.get("comment", {}).get("value", ""),
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "organism": organism if organism else "all",
                    "inhibitors": inhibitors,
                    "count": len(inhibitors),
                },
                "metadata": {
                    "source": "BRENDA SPARQL",
                    "parameter": "Inhibitors and Ki values",
                    "unit": "mM",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}

    def _get_enzyme_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get general enzyme information by EC number.

        Args:
            arguments: Dict containing:
                - ec_number: EC number
        """
        ec_number = arguments.get("ec_number", "")
        if not ec_number:
            return {"status": "error", "error": "Missing required parameter: ec_number"}

        try:
            query = f"""
            PREFIX brenda: <http://brenda-enzymes.org/brenda/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

            SELECT ?name ?systematicName ?reaction ?organism
            WHERE {{
                ?enzyme brenda:ecNumber "{ec_number}" .
                OPTIONAL {{ ?enzyme brenda:recommendedName ?name }}
                OPTIONAL {{ ?enzyme brenda:systematicName ?systematicName }}
                OPTIONAL {{ ?enzyme brenda:reaction ?reaction }}
                OPTIONAL {{ ?enzyme brenda:organism ?organism }}
            }}
            LIMIT 10
            """

            result = self._make_sparql_query(query)

            enzyme_info = []
            if "results" in result and "bindings" in result["results"]:
                for binding in result["results"]["bindings"]:
                    enzyme_info.append(
                        {
                            "name": binding.get("name", {}).get("value", ""),
                            "systematic_name": binding.get("systematicName", {}).get(
                                "value", ""
                            ),
                            "reaction": binding.get("reaction", {}).get("value", ""),
                            "organism": binding.get("organism", {}).get("value", ""),
                        }
                    )

            return {
                "status": "success",
                "data": {
                    "ec_number": ec_number,
                    "info": enzyme_info
                    if enzyme_info
                    else [{"note": "Enzyme found but limited info available"}],
                    "count": len(enzyme_info),
                },
                "metadata": {
                    "source": "BRENDA SPARQL",
                },
            }

        except Exception as e:
            return {"status": "error", "error": f"BRENDA query failed: {str(e)}"}
