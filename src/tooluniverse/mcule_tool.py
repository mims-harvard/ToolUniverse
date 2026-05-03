"""
Mcule Compound Purchasing Platform Tool

Provides access to the Mcule REST API for searching and retrieving
information about commercially available compounds from 30M+ molecules
across multiple suppliers.

Mcule aggregates purchasable compounds from hundreds of chemical vendors,
enabling compound sourcing for drug discovery and chemical biology.

Public endpoints (no auth, rate-limited: 10/min burst, 100/day):
- Compound lookup by SMILES, InChIKey, or Mcule ID
- Compound detail (SMILES, formula, properties, CAS numbers)
- Database file listings (downloadable compound libraries)

Auth-required endpoints (MCULE_API_KEY):
- Exact structure search (batch up to 1000)
- Similarity search
- Substructure search
- Pricing and availability
- Quote management

API base: https://mcule.com/api/v1/
Reference: https://doc.mcule.com/doku.php?id=api
"""

import os
import requests
from typing import Dict, Any, Optional, List
from .base_tool import BaseTool
from .tool_registry import register_tool


MCULE_BASE_URL = "https://mcule.com/api/v1"


@register_tool("MculeTool")
class MculeTool(BaseTool):
    """
    Tool for querying the Mcule compound purchasing platform.

    Mcule is a compound vendor aggregator with 30M+ purchasable molecules.
    It provides compound lookup, property data, and database file access.

    Supported operations:
    - lookup_compound: Look up compounds by SMILES, InChIKey, or Mcule ID
    - get_compound: Get detailed compound info (properties, formula, CAS)
    - list_databases: List available compound database files
    - get_database: Get detail for a specific database file
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        # Check for optional API key
        api_key = os.environ.get("MCULE_API_KEY")
        if api_key:
            self.session.headers.update({"Authorization": "Token {}".format(api_key)})
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Mcule API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "lookup_compound": self._lookup_compound,
            "get_compound": self._get_compound,
            "list_databases": self._list_databases,
            "get_database": self._get_database,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}".format(operation),
                "available_operations": list(operation_handlers.keys()),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "Mcule API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to Mcule API"}
        except Exception as e:
            return {
                "status": "error",
                "error": "Mcule operation failed: {}".format(str(e)),
            }

    def _make_request(
        self, path: str, params: Optional[Dict] = None, method: str = "GET"
    ) -> Dict[str, Any]:
        """Make request to Mcule API."""
        url = "{}/{}".format(MCULE_BASE_URL, path.lstrip("/"))
        try:
            if method == "GET":
                response = self.session.get(
                    url, params=params or {}, timeout=self.timeout
                )
            else:
                response = self.session.post(
                    url, json=params or {}, timeout=self.timeout
                )

            if response.status_code == 200:
                try:
                    data = response.json()
                    return {"ok": True, "data": data}
                except ValueError:
                    return {
                        "ok": False,
                        "error": "Invalid JSON response from Mcule API",
                    }
            elif response.status_code == 401:
                return {
                    "ok": False,
                    "error": "Authentication required. Set MCULE_API_KEY environment variable.",
                }
            elif response.status_code == 404:
                return {"ok": False, "error": "Resource not found"}
            elif response.status_code == 429:
                detail = ""
                try:
                    detail = response.json().get("detail", "")
                except Exception:
                    pass
                return {
                    "ok": False,
                    "error": "Rate limit exceeded. {}".format(detail),
                }
            else:
                return {
                    "ok": False,
                    "error": "Mcule API returned status {}".format(
                        response.status_code
                    ),
                }
        except requests.exceptions.RequestException as e:
            return {"ok": False, "error": str(e)}

    def _lookup_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Look up compounds by SMILES, InChIKey, or Mcule ID.

        Uses the /search/lookup/ endpoint which accepts any of:
        - SMILES string (e.g., CC(=O)Oc1ccccc1C(=O)O)
        - InChIKey (e.g., BSYNRYMUTXBXSQ-UHFFFAOYSA-N)
        - Mcule ID (e.g., MCULE-3199019536)
        """
        query = arguments.get("query")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        result = self._make_request("search/lookup/", {"query": query})
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        results = result["data"].get("results", [])
        if not results:
            return {
                "status": "success",
                "data": [],
                "message": "No compounds found matching '{}'".format(query),
            }

        compounds = []
        for r in results:
            compounds.append(
                {
                    "mcule_id": r.get("mcule_id"),
                    "url": r.get("url"),
                    "smiles": r.get("smiles"),
                }
            )

        return {
            "status": "success",
            "data": compounds,
            "count": len(compounds),
        }

    def _get_compound(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed compound information by Mcule ID.

        Returns SMILES, InChIKey, formula, molecular properties,
        CAS numbers, and stereo type.
        """
        mcule_id = arguments.get("mcule_id")
        if not mcule_id:
            return {"status": "error", "error": "mcule_id parameter is required"}

        # Normalize Mcule ID format
        mcule_id = mcule_id.strip().upper()
        if not mcule_id.startswith("MCULE-"):
            mcule_id = "MCULE-" + mcule_id

        result = self._make_request("compound/{}/".format(mcule_id))
        if not result["ok"]:
            return {
                "status": "error",
                "error": "Compound {} not found: {}".format(mcule_id, result["error"]),
            }

        data = result["data"]
        properties = data.get("properties", {})

        compound = {
            "mcule_id": data.get("mcule_id", mcule_id),
            "url": data.get("url"),
            "smiles": data.get("smiles"),
            "inchi_key": data.get("inchi_key"),
            "std_inchi": data.get("std_inchi"),
            "formula": data.get("formula"),
            "stereo_type": data.get("stereo_type"),
            "cas_numbers": data.get("cas_numbers", []),
            "properties": {
                "mol_mass": properties.get("mol_mass"),
                "logp": properties.get("logp"),
                "h_bond_acceptors": properties.get("h_bond_acceptors"),
                "h_bond_donors": properties.get("h_bond_donors"),
                "rotatable_bonds": properties.get("rotatable_bonds"),
                "psa": properties.get("psa"),
                "r5_violations": properties.get("r5_violations"),
                "rings": properties.get("rings"),
                "heavy_atoms": properties.get("heavy_atoms"),
                "stereocenters": properties.get("stereocenters"),
            },
        }

        return {
            "status": "success",
            "data": compound,
        }

    def _list_databases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available compound database files from Mcule.

        Returns database name, description, entry count, last updated date,
        and downloadable file information.
        """
        result = self._make_request("database-files/")
        if not result["ok"]:
            return {"status": "error", "error": result["error"]}

        raw_data = result["data"]
        databases_raw = raw_data.get("results", [])

        # Filter to public databases only
        public_filter = arguments.get("public_only", True)
        databases = []
        for db in databases_raw:
            if public_filter and not db.get("public", False):
                continue
            files = []
            for f in db.get("files", []):
                files.append(
                    {
                        "filename": f.get("filename"),
                        "file_type": f.get("file_type"),
                        "size_mb": f.get("size_mb"),
                        "download_url": f.get("download_url"),
                    }
                )
            databases.append(
                {
                    "id": db.get("id"),
                    "name": db.get("name"),
                    "description": db.get("description"),
                    "entry_count": db.get("entry_count"),
                    "last_updated": db.get("last_updated"),
                    "public": db.get("public"),
                    "group": db.get("group"),
                    "files": files,
                }
            )

        return {
            "status": "success",
            "data": databases,
            "count": len(databases),
        }

    def _get_database(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detail for a specific database file by ID.

        Returns database name, description, entry count, last updated,
        and file download links.
        """
        database_id = arguments.get("database_id")
        if database_id is None:
            return {"status": "error", "error": "database_id parameter is required"}

        result = self._make_request("database-files/{}/".format(database_id))
        if not result["ok"]:
            return {
                "status": "error",
                "error": "Database {} not found: {}".format(
                    database_id, result["error"]
                ),
            }

        db = result["data"]
        files = []
        for f in db.get("files", []):
            files.append(
                {
                    "filename": f.get("filename"),
                    "file_type": f.get("file_type"),
                    "size_mb": f.get("size_mb"),
                    "download_url": f.get("download_url"),
                }
            )

        database = {
            "id": db.get("id"),
            "name": db.get("name"),
            "description": db.get("description"),
            "entry_count": db.get("entry_count"),
            "last_updated": db.get("last_updated"),
            "public": db.get("public"),
            "group": db.get("group"),
            "files": files,
        }

        return {
            "status": "success",
            "data": database,
        }
