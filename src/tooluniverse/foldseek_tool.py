"""
Foldseek API tool for ToolUniverse.

Foldseek is a fast and sensitive protein structure search tool that finds
structural similarities even in the absence of sequence similarity.

API: https://search.foldseek.com/api
No authentication required.

Documentation: https://github.com/steineggerlab/foldseek
"""

import time
import requests
from typing import Any

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

FOLDSEEK_BASE = "https://search.foldseek.com/api"


@register_tool("FoldseekTool")
class FoldseekTool(BaseRESTTool):
    """
    Tool for searching protein structures using Foldseek.

    Supports:
    - Submitting PDB structures for similarity search against AlphaFold DB,
      PDB, and other databases
    - Polling for job completion (async)
    - Retrieving alignment results

    No authentication required.
    """

    def __init__(self, tool_config: dict):
        super().__init__(tool_config)
        self.timeout = 30
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments: dict) -> dict:
        """Execute the Foldseek API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Foldseek request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Foldseek server.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Foldseek error: {str(e)}",
            }

    def _query(self, arguments: dict) -> dict:
        """Route to the appropriate operation."""
        op = self.operation
        if op == "search":
            return self._submit_search(arguments)
        elif op == "get_result":
            return self._get_result(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    def _submit_search(self, arguments: dict) -> dict:
        """Submit a PDB structure for similarity search and wait for results."""
        pdb_id = arguments.get("pdb_id", "").strip().upper()
        # Accept 'query' as alias for 'sequence'
        sequence = (arguments.get("sequence") or arguments.get("query") or "").strip()
        database = arguments.get("database", "afdb50")
        mode = arguments.get("mode", "tmalign")
        max_results = min(int(arguments.get("max_results", 10)), 50)

        if not pdb_id and not sequence:
            return {
                "status": "error",
                "error": "Either pdb_id or sequence (amino acid sequence) is required.",
            }

        data: dict[str, Any] = {"mode": mode, "database[]": database}

        if pdb_id:
            # Fetch PDB structure from RCSB and submit as a file
            pdb_url = f"https://files.rcsb.org/download/{pdb_id}.pdb"
            resp = requests.get(pdb_url, timeout=15)
            if resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Could not fetch PDB file for {pdb_id} from RCSB.",
                }
            resp = requests.post(
                f"{FOLDSEEK_BASE}/ticket",
                files={"q": (f"{pdb_id}.pdb", resp.text)},
                data=data,
                timeout=self.timeout,
            )
        else:
            # Sequence must be in FASTA format for Foldseek
            if not sequence.startswith(">"):
                fasta_seq = f">query\n{sequence}"
            else:
                fasta_seq = sequence
            resp = requests.post(
                f"{FOLDSEEK_BASE}/ticket",
                data={**data, "q": fasta_seq},
                timeout=self.timeout,
            )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"Foldseek submission failed: HTTP {resp.status_code}",
            }

        ticket = resp.json()
        ticket_id = ticket.get("id")
        if not ticket_id:
            return {
                "status": "error",
                "error": "Foldseek did not return a ticket ID.",
            }

        # Poll for completion
        max_wait = 120
        poll_interval = 3
        elapsed = 0
        while elapsed < max_wait:
            status_resp = requests.get(
                f"{FOLDSEEK_BASE}/ticket/{ticket_id}", timeout=15
            )
            if status_resp.status_code != 200:
                return {
                    "status": "error",
                    "error": f"Failed to check job status: HTTP {status_resp.status_code}",
                }
            status_data = status_resp.json()
            job_status = status_data.get("status", "")

            if job_status == "COMPLETE":
                break
            elif job_status == "ERROR":
                if not pdb_id and sequence:
                    return {
                        "status": "error",
                        "error": (
                            "Foldseek sequence search failed. "
                            "Foldseek requires a PDB structure for structure-based search. "
                            "Provide a pdb_id instead of a raw sequence."
                        ),
                    }
                return {
                    "status": "error",
                    "error": "Foldseek search failed on the server.",
                }
            time.sleep(poll_interval)
            elapsed += poll_interval

        if elapsed >= max_wait:
            return {
                "status": "error",
                "error": f"Foldseek search timed out after {max_wait}s. Ticket: {ticket_id}",
            }

        # Get results (database index 0)
        result_resp = requests.get(f"{FOLDSEEK_BASE}/result/{ticket_id}/0", timeout=30)
        if result_resp.status_code != 200:
            return {
                "status": "error",
                "error": f"Failed to retrieve results: HTTP {result_resp.status_code}",
            }

        result_data = result_resp.json()
        return self._parse_results(
            result_data, pdb_id or "query", database, max_results
        )

    def _get_result(self, arguments: dict) -> dict:
        """Get results for a previously submitted Foldseek job."""
        ticket_id = arguments.get("ticket_id", "").strip()
        max_results = min(int(arguments.get("max_results", 10)), 50)

        if not ticket_id:
            return {
                "status": "error",
                "error": "ticket_id is required.",
            }

        # Check status
        status_resp = requests.get(f"{FOLDSEEK_BASE}/ticket/{ticket_id}", timeout=15)
        if status_resp.status_code != 200:
            return {
                "status": "error",
                "error": f"Failed to check job status: HTTP {status_resp.status_code}",
            }
        status_data = status_resp.json()
        job_status = status_data.get("status", "")

        if job_status != "COMPLETE":
            return {
                "status": "success",
                "data": {
                    "ticket_id": ticket_id,
                    "job_status": job_status,
                    "alignments": [],
                    "total_hits": 0,
                },
                "metadata": {
                    "source": "Foldseek",
                    "description": f"Job status: {job_status}. Try again later.",
                },
            }

        result_resp = requests.get(f"{FOLDSEEK_BASE}/result/{ticket_id}/0", timeout=30)
        if result_resp.status_code != 200:
            return {
                "status": "error",
                "error": f"Failed to retrieve results: HTTP {result_resp.status_code}",
            }

        result_data = result_resp.json()
        return self._parse_results(result_data, "query", "unknown", max_results)

    def _parse_results(
        self, result_data: dict, query_id: str, database: str, max_results: int
    ) -> dict:
        """Parse Foldseek result JSON into structured output."""
        all_results = result_data.get("results", [])
        alignments = []

        for db_result in all_results:
            db_name = db_result.get("db", database)
            for alignment_set in db_result.get("alignments", []):
                for aln in (
                    alignment_set
                    if isinstance(alignment_set, list)
                    else [alignment_set]
                ):
                    if not isinstance(aln, dict):
                        continue
                    alignments.append(
                        {
                            "target": aln.get("target", ""),
                            "database": db_name,
                            "seq_identity": aln.get("seqId"),
                            "e_value": aln.get("eval"),
                            "score": aln.get("score"),
                            "query_start": aln.get("qStartPos"),
                            "query_end": aln.get("qEndPos"),
                            "target_start": aln.get("dbStartPos"),
                            "target_end": aln.get("dbEndPos"),
                            "alignment_length": aln.get("alnLength"),
                            "target_description": aln.get("tDescription", ""),
                        }
                    )

        # Sort by e-value (lower is better)
        alignments.sort(key=lambda x: (x.get("e_value") or float("inf")))
        total_hits = len(alignments)
        alignments = alignments[:max_results]

        return {
            "status": "success",
            "data": {
                "query": query_id,
                "alignments": alignments,
                "total_hits": total_hits,
            },
            "metadata": {
                "database": database,
                "source": "Foldseek",
                "description": (
                    "Structural similarity search results. Lower e_value = more "
                    "significant hit. seq_identity = fraction of identical residues."
                ),
            },
        }
