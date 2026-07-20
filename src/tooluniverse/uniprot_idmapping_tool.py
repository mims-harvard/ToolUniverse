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

        # Poll for completion (max 60 seconds). The status endpoint sometimes
        # 303-redirects straight into a results page instead of ever
        # reporting jobStatus=="FINISHED" -- that redirected page uses its
        # own default page size (25), not the size=500 this tool needs, so
        # treat its presence as "job done" and always re-fetch the full,
        # paginated result set via _fetch_all_results() below rather than
        # returning that first small page directly. Confirmed live:
        # P00533 -> PDB has 354 real mappings, but the redirected status
        # response only ever carries the first 25 of them.
        max_polls = 20
        for _ in range(max_polls):
            status_resp = requests.get(
                f"{UNIPROT_BASE_URL}/idmapping/status/{job_id}",
                timeout=self.timeout,
            )
            status_data = status_resp.json()

            # For jobs that complete almost instantly, the status endpoint can
            # return results embedded directly instead of a "FINISHED"
            # jobStatus (confirmed live) -- either way, treat it as done and
            # fall through to the paginated results fetch below (size=500).
            # Returning this embedded copy directly previously silently
            # truncated to UniProt's unpaginated default page size (25),
            # even when the job actually had hundreds of matches.
            if status_data.get("jobStatus") == "FINISHED" or "results" in status_data:
                break
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

        results, failed_ids = self._fetch_all_results(job_id)
        return {
            "status": "success",
            "results": results,
            "job_id": job_id,
            "failed_ids": failed_ids,
        }

    def _fetch_all_results(self, job_id: str, max_pages: int = 20):
        """Fetch every page of a completed mapping job's results, following
        the Link header's rel="next" URL so large result sets (e.g. a
        heavily-studied protein with hundreds of PDB structures) aren't
        silently truncated to a single page."""
        results = []
        failed_ids = []
        url = f"{UNIPROT_BASE_URL}/idmapping/results/{job_id}"
        params = {"size": 500}
        for _ in range(max_pages):
            resp = requests.get(url, params=params, timeout=self.timeout)
            resp.raise_for_status()
            page = resp.json()
            results.extend(page.get("results", []))
            failed_ids.extend(page.get("failedIds", []))

            next_url = self._parse_next_link(resp.headers.get("Link"))
            if not next_url:
                break
            url, params = next_url, None
        return results, failed_ids

    @staticmethod
    def _parse_next_link(link_header):
        """Extract the rel="next" URL from an RFC 5988 Link header."""
        if not link_header:
            return None
        for part in link_header.split(","):
            segments = part.split(";")
            if len(segments) >= 2 and 'rel="next"' in segments[1]:
                return segments[0].strip().strip("<>")
        return None

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
                "truncated": len(parsed) > 500,
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
                "truncated": len(parsed) > 500,
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
                "truncated": len(parsed) > 500,
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
