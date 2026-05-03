# uniprot_idmapping_tool.py
"""
UniProt ID Mapping Service tool for ToolUniverse.

Provides cross-database protein/gene identifier conversion using the
canonical UniProt ID Mapping REST API. Supports 100+ databases including
UniProtKB, Gene Names, Ensembl, RefSeq, PDB, ChEMBL, and more.

The service is asynchronous: a mapping job is submitted via POST,
its status is polled, and results are retrieved when complete.

API: https://rest.uniprot.org/idmapping/
No authentication required.
"""

import time
import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

UNIPROT_BASE_URL = "https://rest.uniprot.org"


@register_tool("UniProtIDMappingTool")
class UniProtIDMappingTool(BaseTool):
    """
    Tool for converting identifiers between databases using
    the UniProt ID Mapping service.

    Handles the async submit -> poll -> results workflow automatically.
    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "convert"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the UniProt ID Mapping API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"UniProt ID Mapping API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to UniProt ID Mapping API",
            }
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            body = ""
            try:
                body = e.response.json().get("messages", [""])[0]
            except Exception:
                pass
            return {
                "status": "error",
                "error": f"UniProt ID Mapping HTTP error {status}: {body}",
            }
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint_type == "convert":
            return self._convert(arguments)
        elif self.endpoint_type == "to_pdb":
            return self._to_pdb(arguments)
        elif self.endpoint_type == "gene_to_uniprot":
            return self._gene_to_uniprot(arguments)
        elif self.endpoint_type == "list_databases":
            return self._list_databases(arguments)
        return {
            "status": "error",
            "error": f"Unknown endpoint_type: {self.endpoint_type}",
        }

    def _submit_and_poll(
        self, from_db: str, to_db: str, ids: str, tax_id: int = None
    ) -> Dict:
        """Submit a mapping job and poll for results."""
        # Submit job
        data = {
            "from": from_db,
            "to": to_db,
            "ids": ids,
        }
        if tax_id:
            data["taxId"] = tax_id

        submit_resp = requests.post(
            f"{UNIPROT_BASE_URL}/idmapping/run",
            data=data,
            timeout=self.timeout,
        )
        submit_resp.raise_for_status()
        job_id = submit_resp.json().get("jobId")

        if not job_id:
            return {
                "status": "error",
                "error": "Failed to get job ID from UniProt ID Mapping",
            }

        # Poll for completion (max 60 seconds)
        max_polls = 20
        for _ in range(max_polls):
            status_resp = requests.get(
                f"{UNIPROT_BASE_URL}/idmapping/status/{job_id}",
                timeout=self.timeout,
            )
            status_data = status_resp.json()

            if status_data.get("jobStatus") == "FINISHED":
                break
            if "results" in status_data:
                # Some responses include results directly
                return {"results": status_data["results"], "job_id": job_id}
            if status_data.get("jobStatus") == "ERROR":
                msg = status_data.get("errorMessage", "Unknown error")
                return {
                    "status": "error",
                    "error": f"UniProt mapping job failed: {msg}",
                }

            time.sleep(1.5)
        else:
            return {
                "status": "error",
                "error": "UniProt ID mapping job did not complete within timeout",
            }

        # Get results
        results_resp = requests.get(
            f"{UNIPROT_BASE_URL}/idmapping/results/{job_id}",
            params={"size": 500},
            timeout=self.timeout,
        )
        results_resp.raise_for_status()
        results_data = results_resp.json()

        # Feature-68B-003: extract failedIds so callers can detect unmapped input IDs
        return {
            "status": "success",
            "results": results_data.get("results", []),
            "job_id": job_id,
            "failed_ids": results_data.get("failedIds", []),
        }

    def _convert(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Generic ID conversion between any supported databases."""
        ids = arguments.get("ids", "")
        from_db = arguments.get("from_db", "")
        to_db = arguments.get("to_db", "UniProtKB")
        tax_id = arguments.get("tax_id")

        if not ids:
            return {
                "status": "error",
                "error": "ids parameter is required (e.g., 'TP53,BRCA1')",
            }
        if not from_db:
            return {
                "status": "error",
                "error": "from_db parameter is required (e.g., 'Gene_Name')",
            }

        result = self._submit_and_poll(from_db, to_db, ids, tax_id)
        if "error" in result:
            return result

        raw_results = result.get("results", [])

        # Parse results - handle both simple and complex formats
        parsed = []
        for r in raw_results:
            to_val = r.get("to", "")
            # Some results have nested objects for 'to'
            if isinstance(to_val, dict):
                to_val = to_val.get("primaryAccession", to_val.get("id", str(to_val)))
            parsed.append({"from": r.get("from", ""), "to": str(to_val)})

        return {
            "status": "success",
            "data": {
                "from_db": from_db,
                "to_db": to_db,
                "result_count": len(parsed),
                "results": parsed[:500],
                "failed_ids": result.get("failed_ids", []),
            },
            "metadata": {
                "source": "UniProt ID Mapping Service",
                "job_id": result.get("job_id", ""),
                "endpoint": "idmapping",
            },
        }

    def _to_pdb(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert UniProt accessions to PDB IDs."""
        uniprot_ids = arguments.get("uniprot_ids", "")

        if not uniprot_ids:
            return {
                "status": "error",
                "error": "uniprot_ids is required (e.g., 'P04637')",
            }

        result = self._submit_and_poll("UniProtKB_AC-ID", "PDB", uniprot_ids)
        if "error" in result:
            return result

        raw_results = result.get("results", [])
        parsed = [
            {"from": r.get("from", ""), "to": str(r.get("to", ""))} for r in raw_results
        ]

        return {
            "status": "success",
            "data": {
                "query_ids": uniprot_ids,
                "result_count": len(parsed),
                "results": parsed[:500],
            },
            "metadata": {
                "source": "UniProt ID Mapping Service",
                "endpoint": "idmapping (UniProtKB_AC-ID -> PDB)",
            },
        }

    def _gene_to_uniprot(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Convert gene names to UniProt accessions."""
        gene_names = arguments.get("gene_names", "")
        tax_id = arguments.get("tax_id", 9606)
        reviewed_only = arguments.get("reviewed_only", False)

        if not gene_names:
            return {
                "status": "error",
                "error": "gene_names is required (e.g., 'TP53,BRCA1')",
            }

        to_db = "UniProtKB-Swiss-Prot" if reviewed_only else "UniProtKB"

        result = self._submit_and_poll("Gene_Name", to_db, gene_names, tax_id)
        if "error" in result:
            return result

        raw_results = result.get("results", [])
        parsed = []
        for r in raw_results:
            to_val = r.get("to", "")
            if isinstance(to_val, dict):
                to_val = to_val.get("primaryAccession", str(to_val))
            parsed.append({"from": r.get("from", ""), "to": str(to_val)})

        return {
            "status": "success",
            "data": {
                "gene_names": gene_names,
                "species_taxid": tax_id,
                "result_count": len(parsed),
                "results": parsed[:500],
            },
            "metadata": {
                "source": "UniProt ID Mapping Service",
                "endpoint": f"idmapping (Gene_Name -> {to_db})",
            },
        }

    def _list_databases(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available databases for ID mapping."""
        url = f"{UNIPROT_BASE_URL}/configure/idmapping/fields"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        groups_raw = raw.get("groups", [])
        groups = []
        for g in groups_raw:
            dbs = []
            for item in g.get("items", []):
                dbs.append(
                    {
                        "name": item.get("name", ""),
                        "display_name": item.get("displayName", ""),
                        "from_supported": item.get("from", False),
                    }
                )
            groups.append(
                {
                    "group_name": g.get("groupName", ""),
                    "databases": dbs,
                }
            )

        return {
            "status": "success",
            "data": {
                "group_count": len(groups),
                "groups": groups,
            },
            "metadata": {
                "source": "UniProt ID Mapping Service",
                "endpoint": "configure/idmapping/fields",
            },
        }
