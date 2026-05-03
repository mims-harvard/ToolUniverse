"""
SIMBAD Tool for ToolUniverse

This tool provides access to the SIMBAD astronomical database,
allowing queries for astronomical objects by name, coordinates, or identifiers.
"""

import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("SIMBADTool")
class SIMBADTool(BaseTool):
    """
    Query the SIMBAD astronomical database for object information.

    SIMBAD (Set of Identifications, Measurements, and Bibliography for Astronomical Data)
    is a comprehensive database of astronomical objects beyond the Solar System.
    """

    def __init__(
        self,
        tool_config,
        base_url="https://simbad.cds.unistra.fr/simbad/sim-script",
    ):
        super().__init__(tool_config)
        self.base_url = base_url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a SIMBAD query based on the provided arguments.

        Args:
            arguments: Dictionary containing query parameters

        Returns:
            Dictionary containing query results or error information
        """
        query_type = arguments.get("query_type", "object_name")

        if query_type == "object_name":
            return self._query_by_name(arguments)
        elif query_type == "coordinates":
            return self._query_by_coordinates(arguments)
        elif query_type == "identifier":
            return self._query_by_identifier(arguments)
        else:
            return {"status": "error", "error": f"Unknown query_type: {query_type}"}

    def _query_by_name(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query SIMBAD by object name.

        Args:
            arguments: Must contain 'object_name' parameter

        Returns:
            Dictionary containing object information
        """
        object_name = arguments.get("object_name")
        if not object_name:
            return {
                "status": "error",
                "data": {
                    "error": "object_name parameter is required for query_type='object_name'"
                },
            }

        output_format = arguments.get("output_format", "basic")

        # Build SIMBAD script query
        script_lines = [
            "output console=off script=off",
            f'format object "{self._get_format_string(output_format)}"',
            f"query id {object_name}",
        ]

        script = "\n".join(script_lines)

        return self._execute_query(script, object_name)

    def _query_by_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query SIMBAD by coordinates.

        Args:
            arguments: Must contain 'ra', 'dec', and optional 'radius' parameters

        Returns:
            Dictionary containing objects near the specified coordinates
        """
        ra = arguments.get("ra")
        dec = arguments.get("dec")
        radius = arguments.get("radius", 1.0)  # Default 1 arcmin

        if ra is None or dec is None:
            return {
                "status": "error",
                "data": {
                    "error": "Both 'ra' and 'dec' parameters are required for query_type='coordinates'"
                },
            }

        output_format = arguments.get("output_format", "basic")
        max_results = arguments.get("max_results", 10)

        # Build SIMBAD script query for coordinate search
        script_lines = [
            "output console=off script=off",
            f'format object "{self._get_format_string(output_format)}"',
            f"query coo {ra} {dec} radius={radius}m",
        ]

        script = "\n".join(script_lines)

        return self._execute_query(
            script, f"coordinates: RA={ra}, DEC={dec}, radius={radius}m", max_results
        )

    def _query_by_identifier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Query SIMBAD by identifier pattern.

        Args:
            arguments: Must contain 'identifier' parameter

        Returns:
            Dictionary containing matching objects
        """
        identifier = arguments.get("identifier")
        if not identifier:
            return {
                "status": "error",
                "data": {
                    "error": "identifier parameter is required for query_type='identifier'"
                },
            }

        output_format = arguments.get("output_format", "basic")
        max_results = arguments.get("max_results", 10)

        # Build SIMBAD script query
        script_lines = [
            "output console=off script=off",
            f'format object "{self._get_format_string(output_format)}"',
            f"query id wildcard {identifier}",
        ]

        script = "\n".join(script_lines)

        return self._execute_query(script, identifier, max_results)

    def _get_format_string(self, output_format: str) -> str:
        """
        Get SIMBAD format string based on requested output format.

        Args:
            output_format: One of 'basic', 'detailed', or 'full'

        Returns:
            SIMBAD format string
        """
        if output_format == "basic":
            return "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"
        elif output_format == "detailed":
            return "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE | %SP | %FLUXLIST(V)"
        elif output_format == "full":
            return "%IDLIST(1) | %COO(A D;ICRS;J2000) | %OTYPE | %SP | %FLUXLIST(U;B;V;R;I;J;H;K) | %PM | %PLX | %RV | %MT"
        else:
            return "%IDLIST(1) | %COO(A D;ICRS) | %OTYPE"

    def _execute_query(
        self, script: str, query_description: str, max_results: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a SIMBAD script query.

        Args:
            script: SIMBAD script to execute
            query_description: Description of the query for error messages
            max_results: Maximum number of results to return

        Returns:
            Dictionary containing query results or error information
        """
        try:
            response = requests.post(self.base_url, data={"script": script}, timeout=30)
            response.raise_for_status()
        except requests.Timeout:
            return {
                "status": "error",
                "data": {
                    "error": "Request to SIMBAD timed out",
                    "query": query_description,
                },
            }
        except requests.RequestException as e:
            return {
                "status": "error",
                "data": {
                    "error": f"Network error querying SIMBAD: {str(e)}",
                    "query": query_description,
                },
            }

        # Parse the response
        result_text = response.text.strip()

        # Parse the results
        lines = result_text.strip().split("\n")

        # Filter out SIMBAD metadata lines (starting with ::)
        data_lines = [line for line in lines if line and not line.startswith("::")]

        # Check for errors in response
        if any(
            "error" in line.lower() or "not found" in line.lower()
            for line in data_lines
        ):
            return {
                "status": "error",
                "data": {
                    "error": "Object not found in SIMBAD",
                    "query": query_description,
                    "raw_response": result_text[:500],  # First 500 chars for debugging
                },
            }

        if not data_lines:
            return {
                "status": "error",
                "data": {"error": "No results found", "query": query_description},
            }

        # Parse results
        results = []
        for line in data_lines[:max_results] if max_results else data_lines:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3:
                result_dict = {
                    "main_id": parts[0],
                    "coordinates": parts[1] if len(parts) > 1 else "",
                    "object_type": parts[2] if len(parts) > 2 else "",
                }

                # Add additional fields if present
                if len(parts) > 3:
                    result_dict["spectral_type"] = parts[3]
                if len(parts) > 4:
                    result_dict["flux"] = parts[4]
                if len(parts) > 5:
                    result_dict["additional_data"] = parts[5:]

                results.append(result_dict)

        result_data = {
            "success": True,
            "query": query_description,
            "count": len(results),
            "results": results,
        }
        return {"status": "success", "data": result_data}


@register_tool("SIMBADAdvancedTool")
class SIMBADAdvancedTool(BaseTool):
    """
    Advanced SIMBAD queries using TAP (Table Access Protocol) for complex queries.

    This tool allows ADQL (Astronomical Data Query Language) queries
    for more sophisticated database searches.
    """

    def __init__(
        self,
        tool_config,
        tap_url="https://simbad.cds.unistra.fr/simbad/sim-tap/sync",
    ):
        super().__init__(tool_config)
        self.tap_url = tap_url

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute an ADQL query on SIMBAD via TAP.

        Args:
            arguments: Dictionary containing 'adql_query' parameter

        Returns:
            Dictionary containing query results
        """
        adql_query = arguments.get("adql_query")
        if not adql_query:
            return {
                "status": "error",
                "data": {"error": "adql_query parameter is required"},
            }

        max_results = arguments.get("max_results", 100)
        output_format = arguments.get("format", "json")

        try:
            params = {
                "REQUEST": "doQuery",
                "LANG": "ADQL",
                "QUERY": adql_query,
                "FORMAT": "json" if output_format == "json" else "votable",
                "MAXREC": max_results,
            }

            response = requests.post(self.tap_url, data=params, timeout=60)
            response.raise_for_status()

            if output_format == "json":
                try:
                    result_data = {
                        "success": True,
                        "query": adql_query,
                        "results": response.json(),
                    }
                    return {"status": "success", "data": result_data}
                except ValueError:
                    result_data = {
                        "success": True,
                        "query": adql_query,
                        "results": response.text,
                    }
                    return {"status": "success", "data": result_data}
            else:
                result_data = {
                    "success": True,
                    "query": adql_query,
                    "results": response.text,
                }
                return {"status": "success", "data": result_data}

        except requests.Timeout:
            return {
                "status": "error",
                "data": {"error": "TAP query timed out", "query": adql_query},
            }
        except requests.RequestException as e:
            return {
                "status": "error",
                "data": {
                    "error": f"Network error executing TAP query: {str(e)}",
                    "query": adql_query,
                },
            }
