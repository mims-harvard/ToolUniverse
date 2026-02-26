"""
DynaMut2 Tool - Protein Stability Prediction from Mutations

DynaMut2 predicts the effect of single-point mutations on protein stability
and dynamics using Normal Mode Analysis (NMA) and graph-based signatures.
Returns predicted change in Gibbs free energy (ddG in kcal/mol):
  - Positive ddG: stabilizing mutation
  - Negative ddG: destabilizing mutation

API pattern:
1. Download PDB structure from RCSB (user provides 4-character PDB code)
2. POST multipart/form-data with pdb_file + mutation + chain to DynaMut2 API
3. Receive job_id, poll GET endpoint until status == "DONE"
4. Return structured prediction result

Reference: Rodrigues, Pires & Ascher (2021) Nucleic Acids Research
Website: https://biosig.lab.uq.edu.au/dynamut2/
"""

import io
import time
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool

DYNAMUT2_API_BASE = "https://biosig.lab.uq.edu.au/dynamut2/api"
RCSB_DOWNLOAD_URL = "https://files.rcsb.org/download/{pdb_id}.pdb"

# Standard 1-letter to 3-letter amino acid mapping
AA_1TO3 = {
    "A": "ALA",
    "C": "CYS",
    "D": "ASP",
    "E": "GLU",
    "F": "PHE",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "K": "LYS",
    "L": "LEU",
    "M": "MET",
    "N": "ASN",
    "P": "PRO",
    "Q": "GLN",
    "R": "ARG",
    "S": "SER",
    "T": "THR",
    "V": "VAL",
    "W": "TRP",
    "Y": "TYR",
}

# Reverse: 3-letter to 1-letter
AA_3TO1 = {v: k for k, v in AA_1TO3.items()}


@register_tool("DynaMut2Tool")
class DynaMut2Tool(BaseTool):
    """
    Tool for predicting the effect of single-point mutations on protein
    stability and dynamics using the DynaMut2 web server.

    Supports two operations:
    - predict_stability: Submit a stability prediction for a PDB structure
      with a specified single-point mutation. Downloads the PDB file from
      RCSB, uploads to DynaMut2, and polls for results.
    - get_job: Retrieve results for a previously submitted DynaMut2 job
      by job ID.

    The prediction returns ddG (change in Gibbs free energy, kcal/mol).
    Positive values indicate stabilizing mutations; negative values
    indicate destabilizing mutations.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ToolUniverse/DynaMut2 (Python requests)",
                "Accept": "application/json",
            }
        )

    def run(self, arguments):
        """Execute the DynaMut2 tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        operation_handlers = {
            "predict_stability": self._predict_stability,
            "get_job": self._get_job,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": "DynaMut2 request timed out. The server may be busy.",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Could not connect to DynaMut2. Service may be temporarily unavailable.",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": "DynaMut2 error: {}".format(str(e)),
            }

    # ---- predict_stability ----

    def _predict_stability(self, arguments):
        """
        Predict the stability effect of a single-point mutation on a protein.

        Steps:
        1. Download PDB file from RCSB
        2. Upload to DynaMut2 with mutation and chain
        3. Poll for results
        4. Return structured prediction
        """
        pdb_id = arguments.get("pdb_id")
        mutation = arguments.get("mutation")
        chain = arguments.get("chain")

        if not pdb_id:
            return {"status": "error", "error": "Missing required parameter: pdb_id"}
        if not mutation:
            return {"status": "error", "error": "Missing required parameter: mutation"}
        if not chain:
            return {"status": "error", "error": "Missing required parameter: chain"}

        # Validate mutation format: single letter + number + single letter (e.g., V1A, E346K)
        mutation = mutation.strip().upper()
        if len(mutation) < 3:
            return {
                "status": "error",
                "error": "Invalid mutation format '{}'. Expected format: WtPosNew (e.g., V1A, E346K)".format(
                    mutation
                ),
            }
        wt_aa = mutation[0]
        new_aa = mutation[-1]
        pos_str = mutation[1:-1]
        if wt_aa not in AA_1TO3 or new_aa not in AA_1TO3:
            return {
                "status": "error",
                "error": "Invalid amino acid in mutation '{}'. Use single-letter codes (A-Y).".format(
                    mutation
                ),
            }
        if not pos_str.isdigit():
            return {
                "status": "error",
                "error": "Invalid position in mutation '{}'. Position must be numeric.".format(
                    mutation
                ),
            }

        # Step 1: Download PDB file from RCSB
        pdb_id_upper = pdb_id.strip().upper()
        pdb_url = RCSB_DOWNLOAD_URL.format(pdb_id=pdb_id_upper)

        try:
            pdb_resp = self.session.get(pdb_url, timeout=30)
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to download PDB {}: {}".format(pdb_id_upper, str(e)),
            }

        if pdb_resp.status_code == 404:
            return {
                "status": "error",
                "error": "PDB ID '{}' not found in RCSB PDB.".format(pdb_id_upper),
            }
        if pdb_resp.status_code != 200:
            return {
                "status": "error",
                "error": "Failed to download PDB {} (HTTP {}).".format(
                    pdb_id_upper, pdb_resp.status_code
                ),
            }

        pdb_content = pdb_resp.content

        # Step 2: Submit to DynaMut2
        submit_url = "{}/prediction_single".format(DYNAMUT2_API_BASE)
        chain_clean = chain.strip().upper()

        try:
            submit_resp = self.session.post(
                submit_url,
                files={
                    "pdb_file": (
                        "{}.pdb".format(pdb_id_upper),
                        io.BytesIO(pdb_content),
                        "chemical/x-pdb",
                    ),
                },
                data={
                    "mutation": mutation,
                    "chain": chain_clean,
                },
                timeout=60,
            )
        except Exception as e:
            return {
                "status": "error",
                "error": "DynaMut2 submission failed: {}".format(str(e)),
            }

        if submit_resp.status_code != 200:
            return {
                "status": "error",
                "error": "DynaMut2 submission returned HTTP {}: {}".format(
                    submit_resp.status_code, submit_resp.text[:200]
                ),
            }

        try:
            submit_data = submit_resp.json()
        except Exception:
            return {
                "status": "error",
                "error": "DynaMut2 returned non-JSON response: {}".format(
                    submit_resp.text[:200]
                ),
            }

        # Check for API error
        if "error" in submit_data:
            return {
                "status": "error",
                "error": "DynaMut2 error: {}".format(submit_data["error"]),
            }

        job_id = submit_data.get("job_id")
        if not job_id:
            return {
                "status": "error",
                "error": "DynaMut2 did not return a job_id: {}".format(
                    str(submit_data)[:200]
                ),
            }

        job_id_str = str(job_id)

        # Step 3: Poll for results
        result = self._poll_job_status("prediction_single", job_id_str)
        if result is None:
            return {
                "status": "error",
                "error": "DynaMut2 job {} timed out after 300 seconds.".format(
                    job_id_str
                ),
            }

        if "error" in result:
            return {"status": "error", "error": result["error"]}

        # Step 4: Format and return
        prediction = result.get("prediction")
        try:
            ddg = float(prediction)
        except (TypeError, ValueError):
            ddg = prediction

        wild_type_3 = result.get("wild-type", AA_1TO3.get(wt_aa, wt_aa))
        mutant_3 = result.get("mutant", AA_1TO3.get(new_aa, new_aa))
        position = result.get("position", pos_str)

        # Convert 3-letter back to 1-letter for compact display
        wt_1 = (
            AA_3TO1.get(wild_type_3, wt_aa) if isinstance(wild_type_3, str) else wt_aa
        )
        mut_1 = AA_3TO1.get(mutant_3, new_aa) if isinstance(mutant_3, str) else new_aa

        effect = (
            "stabilizing"
            if isinstance(ddg, (int, float)) and ddg > 0
            else "destabilizing"
        )

        return {
            "status": "success",
            "data": {
                "pdb_id": pdb_id_upper,
                "chain": chain_clean,
                "mutation": "{}{}{}".format(wt_1, position, mut_1),
                "wild_type": wild_type_3,
                "mutant": mutant_3,
                "position": str(position),
                "ddg_prediction": ddg,
                "effect": effect,
                "job_id": job_id_str,
                "results_page": result.get("results_page", ""),
            },
        }

    # ---- get_job ----

    def _get_job(self, arguments):
        """Retrieve results for a previously submitted DynaMut2 job."""
        job_id = arguments.get("job_id")
        if not job_id:
            return {"status": "error", "error": "Missing required parameter: job_id"}

        job_id_str = str(job_id).strip()
        endpoint = arguments.get("endpoint", "prediction_single")

        result_url = "{}/{}?job_id={}".format(DYNAMUT2_API_BASE, endpoint, job_id_str)

        try:
            resp = self.session.get(result_url, timeout=30)
        except Exception as e:
            return {
                "status": "error",
                "error": "Failed to retrieve DynaMut2 job {}: {}".format(
                    job_id_str, str(e)
                ),
            }

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": "DynaMut2 returned HTTP {} for job {}".format(
                    resp.status_code, job_id_str
                ),
            }

        try:
            data = resp.json()
        except Exception:
            return {
                "status": "error",
                "error": "DynaMut2 returned non-JSON response for job {}".format(
                    job_id_str
                ),
            }

        status = data.get("status", "")

        if status == "RUNNING":
            return {
                "status": "success",
                "data": {
                    "job_id": job_id_str,
                    "job_status": "RUNNING",
                    "message": "Job is still processing. Try again in a few seconds.",
                },
            }

        if status == "DONE":
            prediction = data.get("prediction")
            try:
                ddg = float(prediction)
            except (TypeError, ValueError):
                ddg = prediction

            wild_type_3 = data.get("wild-type", "")
            mutant_3 = data.get("mutant", "")
            position = data.get("position", "")
            chain = data.get("chain", "")

            wt_1 = AA_3TO1.get(wild_type_3, "?")
            mut_1 = AA_3TO1.get(mutant_3, "?")
            effect = (
                "stabilizing"
                if isinstance(ddg, (int, float)) and ddg > 0
                else "destabilizing"
            )

            return {
                "status": "success",
                "data": {
                    "pdb_id": "",
                    "chain": chain,
                    "mutation": "{}{}{}".format(wt_1, position, mut_1),
                    "wild_type": wild_type_3,
                    "mutant": mutant_3,
                    "position": str(position),
                    "ddg_prediction": ddg,
                    "effect": effect,
                    "job_id": job_id_str,
                    "results_page": data.get("results_page", ""),
                },
            }

        # Unknown status or error
        if "error" in data:
            return {
                "status": "error",
                "error": "DynaMut2 job error: {}".format(data["error"]),
            }

        return {
            "status": "error",
            "error": "Unexpected DynaMut2 response for job {}: {}".format(
                job_id_str, str(data)[:200]
            ),
        }

    # ---- Polling helper ----

    def _poll_job_status(self, endpoint, job_id, max_wait=300, interval=10):
        """
        Poll DynaMut2 job status until completion or timeout.

        Args:
            endpoint: API endpoint (e.g., 'prediction_single')
            job_id: Job ID string
            max_wait: Maximum seconds to wait
            interval: Seconds between poll attempts

        Returns:
            dict with result data if complete, or None if timeout
        """
        status_url = "{}/{}?job_id={}".format(DYNAMUT2_API_BASE, endpoint, job_id)
        elapsed = 0

        while elapsed < max_wait:
            try:
                resp = self.session.get(status_url, timeout=30)
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "")

                    if status == "DONE":
                        return data

                    if status == "ERROR" or "error" in data:
                        return {"error": data.get("error", "Job failed")}

                    # Still running, continue polling
            except Exception:
                pass  # Transient error, retry

            time.sleep(interval)
            elapsed += interval

        return None
