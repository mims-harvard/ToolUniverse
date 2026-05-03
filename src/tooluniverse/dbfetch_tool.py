"""
Dbfetch Database Retrieval Tool

This tool provides access to Dbfetch service for retrieving database entries
from multiple databases (UniProt, PDB, etc.) in various formats.
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("DbfetchRESTTool")
class DbfetchRESTTool(BaseTool):
    """
    Dbfetch REST API tool.
    Generic wrapper for Dbfetch API endpoints defined in dbfetch_tools.json.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/Tools/dbfetch/dbfetch"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "*/*", "User-Agent": "ToolUniverse/1.0"})
        self.timeout = 30

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for Dbfetch API"""
        params = {"style": "raw"}  # Always use raw style
        tool_name = self.tool_config.get("name", "")

        if tool_name == "dbfetch_fetch_entry":
            params["db"] = args.get("db", "")
            params["id"] = args.get("id", "")
            params["format"] = args.get("format", "fasta")

        elif tool_name == "dbfetch_fetch_batch":
            params["db"] = args.get("db", "")
            ids = args.get("ids", "")
            # Convert list to comma-separated string
            if isinstance(ids, list):
                ids = ",".join(ids)
            params["id"] = ids
            params["format"] = args.get("format", "fasta")

        elif tool_name == "dbfetch_list_databases":
            # List databases - not supported via REST API, return static list
            return None

        elif tool_name == "dbfetch_list_formats":
            params["db"] = args.get("db", "")
            params["format"] = "default"
            params["style"] = "raw"

        return params

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Dbfetch API call"""
        try:
            params = self._build_params(arguments)
            tool_name = self.tool_config.get("name", "")

            # Handle list_databases specially - not supported via REST API
            if tool_name == "dbfetch_list_databases":
                # Return a static list of common databases
                databases = """Available databases: uniprotkb, pdb, embl, ena_sequence, refseqp, refseqn,
ensemblgene, ensembltranscript, interpro, medline, taxonomy, uniprot,
chembl, afdb, imgtligm, hgnc"""
                return {
                    "status": "success",
                    "data": databases,
                }

            # Handle list_formats specially - not supported via REST API
            if tool_name == "dbfetch_list_formats":
                db = arguments.get("db", "unknown")
                formats = f"""Common formats for {db}: default, fasta, xml, annot, embl, genbank
Note: Exact formats depend on the database. Use dbfetch_fetch_entry to test specific formats."""
                return {
                    "status": "success",
                    "data": formats,
                }

            response = self.session.get(
                self.base_url, params=params, timeout=self.timeout
            )
            response.raise_for_status()

            # Dbfetch returns text (FASTA, XML, etc.) not JSON
            data = response.text

            # Check for error messages in response
            if data.startswith("ERROR") or "<!doctype html>" in data.lower():
                return {
                    "status": "error",
                    "data": f"Dbfetch API error: {data[:200]}",
                }

            return {
                "status": "success",
                "data": data,
            }

        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "data": f"Dbfetch API error: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "data": f"Unexpected error: {str(e)}",
            }
