"""
Sequence alignment and phylogeny tools for ToolUniverse (EMBL-EBI Job Dispatcher).

ToolUniverse could fetch pre-computed alignments/trees (Rfam, Ensembl Compara)
but had no way to align a user's *own* sequences or build a tree from them. These
two tools close that gap using EMBL-EBI's public Job Dispatcher REST services
(the same submit -> poll -> result pattern used by InterProScan):

  - EBI_msa_align              multiple sequence alignment (Clustal Omega / MUSCLE
                               / MAFFT / Kalign / T-Coffee)
  - EBI_build_phylogenetic_tree  neighbour-joining / UPGMA tree from an alignment

Public, no authentication. API: https://www.ebi.ac.uk/Tools/services/rest/
"""

import re
import time
import requests
from typing import Dict, Any, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool

_EBI_BASE = "https://www.ebi.ac.uk/Tools/services/rest"
_DEFAULT_EMAIL = "tooluniverse@example.com"

# Per-method service config. EBI MSA services do not share a parameter schema:
# the output-format parameter is "outfmt" for Clustal Omega but "format" for the
# others, and MUSCLE auto-detects sequence type (no "stype").
_MSA_METHODS = {
    "clustalo": {"format_param": "outfmt", "fasta_value": "fa", "stype": True},
    "muscle": {"format_param": "format", "fasta_value": "fasta", "stype": False},
    "mafft": {"format_param": "format", "fasta_value": "fasta", "stype": True},
    "kalign": {"format_param": "format", "fasta_value": "fasta", "stype": True},
    "tcoffee": {"format_param": "format", "fasta_value": "fasta", "stype": True},
}

# Poll up to ~2.5 min total; each HTTP call still honours the 30s tool timeout.
_MAX_POLL_ATTEMPTS = 50
_POLL_INTERVAL = 3


def _submit(
    service: str, params: Dict[str, Any], timeout: int
) -> Tuple[Optional[str], Optional[str]]:
    """POST a job to an EBI service. Returns (job_id, error)."""
    resp = requests.post(f"{_EBI_BASE}/{service}/run", data=params, timeout=timeout)
    if resp.status_code != 200:
        return (
            None,
            f"{service} submission failed (HTTP {resp.status_code}): {resp.text[:200]}",
        )
    return resp.text.strip(), None


def _poll(
    service: str, job_id: str, timeout: int
) -> Tuple[Optional[str], Optional[str]]:
    """Poll a job to completion. Returns (final_status, error)."""
    for _ in range(_MAX_POLL_ATTEMPTS):
        resp = requests.get(f"{_EBI_BASE}/{service}/status/{job_id}", timeout=timeout)
        status = resp.text.strip()
        if status == "FINISHED":
            return status, None
        if status in ("ERROR", "FAILURE", "NOT_FOUND"):
            return status, f"{service} job {status.lower()} (job {job_id})"
        time.sleep(_POLL_INTERVAL)
    return (
        None,
        f"{service} job did not finish within {_MAX_POLL_ATTEMPTS * _POLL_INTERVAL}s (job {job_id})",
    )


def _result_types(service: str, job_id: str, timeout: int) -> List[str]:
    resp = requests.get(f"{_EBI_BASE}/{service}/resulttypes/{job_id}", timeout=timeout)
    return re.findall(r"<identifier>([^<]+)</identifier>", resp.text)


def _result(service: str, job_id: str, rtype: str, timeout: int) -> str:
    resp = requests.get(
        f"{_EBI_BASE}/{service}/result/{job_id}/{rtype}", timeout=timeout
    )
    resp.raise_for_status()
    return resp.text


def _count_fasta_records(text: str) -> int:
    return len(re.findall(r"^>", text, flags=re.MULTILINE))


def _guarded_run(
    label: str, timeout: int, run_fn, arguments: Dict[str, Any]
) -> Dict[str, Any]:
    """Call run_fn, converting any exception into a {"status": "error"} envelope.

    Tools must never raise, so every run() routes through here for uniform
    handling of timeouts, connection failures, and unexpected errors.
    """
    try:
        return run_fn(arguments)
    except requests.exceptions.Timeout:
        return {
            "status": "error",
            "error": f"EBI {label} request timed out after {timeout}s",
        }
    except requests.exceptions.ConnectionError:
        return {
            "status": "error",
            "error": "Failed to connect to EBI Job Dispatcher",
        }
    except Exception as e:  # noqa: BLE001 - tools must never raise
        return {"status": "error", "error": f"EBI {label} error: {str(e)}"}


@register_tool("EBIMSATool")
class EBIMSATool(BaseTool):
    """Multiple sequence alignment of user-provided sequences via EMBL-EBI.

    Submits a FASTA set (>=2 records) to a Job Dispatcher MSA service, polls to
    completion, and returns the alignment in FASTA and the tool's native format,
    plus a guide tree when the method emits one.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("MSA", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequences = (arguments.get("sequences") or "").strip()
        if not sequences:
            return {
                "status": "error",
                "error": "sequences is required (FASTA, >=2 records)",
            }
        n = _count_fasta_records(sequences)
        if n < 2:
            return {
                "status": "error",
                "error": f"MSA needs >=2 FASTA records; found {n}. Provide multiple '>'-prefixed sequences.",
            }

        method = (arguments.get("method") or "clustalo").strip().lower()
        cfg = _MSA_METHODS.get(method)
        if cfg is None:
            return {
                "status": "error",
                "error": f"Unknown method '{method}'. Choose one of: {', '.join(_MSA_METHODS)}",
            }

        seq_type = (arguments.get("sequence_type") or "protein").strip().lower()
        if seq_type not in ("protein", "dna", "rna"):
            return {
                "status": "error",
                "error": "sequence_type must be protein, dna, or rna",
            }

        params = {
            "email": arguments.get("email", _DEFAULT_EMAIL),
            "sequence": sequences,
            cfg["format_param"]: cfg["fasta_value"],
        }
        if cfg["stype"]:
            # MAFFT/Kalign use "dna" for nucleotide; treat rna as dna for alignment.
            params["stype"] = "protein" if seq_type == "protein" else "dna"

        job_id, err = _submit(method, params, self.timeout)
        if err:
            return {"status": "error", "error": err}
        _, err = _poll(method, job_id, self.timeout)
        if err:
            return {"status": "error", "error": err}

        rtypes = _result_types(method, job_id, self.timeout)
        aligned_fasta = self._fetch_first(
            method, job_id, rtypes, ("fa", "aln-fasta", "fasta")
        )
        clustal = self._fetch_first(
            method, job_id, rtypes, ("aln-clustal_num", "aln-clustal", "clustal", "out")
        )
        guide_tree = self._fetch_first(method, job_id, rtypes, ("phylotree", "tree"))

        return {
            "status": "success",
            "data": {
                "method": method,
                "num_sequences": n,
                "aligned_fasta": aligned_fasta,
                "alignment_clustal": clustal,
                "guide_tree_newick": (guide_tree or "").strip() or None,
            },
            "metadata": {
                "source": f"EMBL-EBI Job Dispatcher ({method})",
                "sequence_type": seq_type,
                "job_id": job_id,
                "result_url": f"{_EBI_BASE}/{method}/result/{job_id}",
            },
        }

    def _fetch_first(
        self,
        service: str,
        job_id: str,
        available: List[str],
        preferred: Tuple[str, ...],
    ) -> Optional[str]:
        """Fetch the first preferred result type that the job actually produced."""
        for rtype in preferred:
            if rtype in available:
                return _result(service, job_id, rtype, self.timeout)
        return None


@register_tool("EBIPhylogenyTool")
class EBIPhylogenyTool(BaseTool):
    """Build a phylogenetic tree from an alignment via EMBL-EBI simple_phylogeny.

    Takes an aligned FASTA (e.g. the output of EBI_msa_align) and returns a
    Newick tree by neighbour-joining or UPGMA.
    """

    SERVICE = "simple_phylogeny"

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("phylogeny", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        aligned = (arguments.get("aligned_sequences") or "").strip()
        if not aligned:
            return {
                "status": "error",
                "error": "aligned_sequences is required (aligned FASTA, >=2 records, e.g. from EBI_msa_align)",
            }
        n = _count_fasta_records(aligned)
        if n < 2:
            return {
                "status": "error",
                "error": f"A tree needs >=2 aligned records; found {n}.",
            }

        clustering = (arguments.get("clustering") or "Neighbour-joining").strip()
        if clustering.lower() in ("nj", "neighbour-joining", "neighbor-joining"):
            clustering = "Neighbour-joining"
        elif clustering.lower() == "upgma":
            clustering = "UPGMA"
        else:
            return {
                "status": "error",
                "error": "clustering must be 'Neighbour-joining' or 'UPGMA'",
            }

        params = {
            "email": arguments.get("email", _DEFAULT_EMAIL),
            "sequence": aligned,
            "tree": "phylip",
            "clustering": clustering,
            "kimura": str(bool(arguments.get("distance_correction", False))).lower(),
            "tossgaps": str(bool(arguments.get("exclude_gaps", False))).lower(),
        }

        job_id, err = _submit(self.SERVICE, params, self.timeout)
        if err:
            return {"status": "error", "error": err}
        _, err = _poll(self.SERVICE, job_id, self.timeout)
        if err:
            return {"status": "error", "error": err}

        newick = _result(self.SERVICE, job_id, "tree", self.timeout).strip()
        return {
            "status": "success",
            "data": {
                "newick": newick,
                "num_taxa": n,
                "clustering": clustering,
            },
            "metadata": {
                "source": "EMBL-EBI Job Dispatcher (simple_phylogeny)",
                "distance_correction": "Kimura"
                if params["kimura"] == "true"
                else "none",
                "exclude_gap_columns": params["tossgaps"] == "true",
                "job_id": job_id,
                "result_url": f"{_EBI_BASE}/{self.SERVICE}/result/{job_id}",
            },
        }
