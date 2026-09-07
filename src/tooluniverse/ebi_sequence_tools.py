# ebi_sequence_tools.py
"""
EMBL-EBI Job Dispatcher sequence-analysis tools for ToolUniverse.

ToolUniverse already wraps three Job Dispatcher services: multiple sequence
alignment (EBI_msa_align, covering Clustal Omega, MUSCLE, MAFFT, Kalign and
T-Coffee), phylogeny (EBI_build_phylogenetic_tree), and InterProScan. This
module adds the remaining widely used services on the same submit -> poll ->
result protocol:

  pairwise alignment    emboss_needle, emboss_stretcher, emboss_matcher
  sequence translation  emboss_transeq, emboss_backtranseq, emboss_sixpack
  domain scanning       pfamscan
  membrane topology     phobius
  profile search        hmmer3_phmmer, psiblast

The submit/poll/result helpers are imported from ebi_alignment_tool rather
than duplicated, so all EBI services share one implementation of the
protocol.

API: https://www.ebi.ac.uk/Tools/services/rest
Public, no authentication.
"""

import json
import re
from typing import Dict, Any, List

from .base_tool import BaseTool
from .tool_registry import register_tool
from .ebi_alignment_tool import (
    _DEFAULT_EMAIL,
    _guarded_run,
    _poll,
    _result,
    _result_types,
    _submit,
)

# service -> (label, whether the service takes an stype parameter)
_PAIRWISE_METHODS = {
    "needle": ("emboss_needle", "Needleman-Wunsch global alignment"),
    "stretcher": ("emboss_stretcher", "memory-efficient global alignment"),
    "matcher": ("emboss_matcher", "Smith-Waterman local alignment"),
}

_TRANSLATE_MODES = {
    "dna_to_protein": ("emboss_transeq", "translate nucleotide to protein"),
    "protein_to_dna": ("emboss_backtranseq", "back-translate protein to nucleotide"),
    "six_frame": ("emboss_sixpack", "six-frame translation with ORF detection"),
}

_PROFILE_METHODS = {
    "phmmer": (
        "hmmer3_phmmer",
        "HMMER3 profile search of a sequence against a database",
    ),
    "psiblast": ("psiblast", "PSI-BLAST iterative profile search"),
}

_PHMMER_DATABASES = [
    "swissprot", "uniprotkb", "uniprotrefprot", "rp75", "rp55", "rp15",
]
_PSIBLAST_DATABASES = [
    "uniprotkb", "uniprotkb_swissprot", "uniprotkb_reference_proteomes",
]


def _first_result(service: str, job_id: str, timeout: int) -> str:
    """Fetch the primary text result, preferring the 'out' result type."""
    types = _result_types(service, job_id, timeout)
    for preferred in ("out", "aln", "sequence"):
        if preferred in types:
            return _result(service, job_id, preferred, timeout)
    return _result(service, job_id, types[0], timeout) if types else ""


def _run_job(
    service: str, params: Dict[str, Any], timeout: int
) -> Dict[str, Any]:
    """Submit, poll, and fetch a job. Returns {'text': ...} or an error dict."""
    params.setdefault("email", _DEFAULT_EMAIL)
    job_id, error = _submit(service, params, timeout)
    if error:
        return {"status": "error", "error": error}
    _, error = _poll(service, job_id, timeout)
    if error:
        return {"status": "error", "error": error}
    return {"text": _first_result(service, job_id, timeout), "job_id": job_id}


def _require_sequence(arguments: Dict[str, Any], name: str = "sequence") -> str:
    return (arguments.get(name) or "").strip()


def _int(value: str) -> Any:
    """Parse an integer field, returning None when the column is malformed."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float(value: str) -> Any:
    """Parse a float field, returning None when the column is malformed."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


@register_tool("EBIPairwiseAlignTool")
class EBIPairwiseAlignTool(BaseTool):
    """Align exactly two sequences via EMBL-EBI EMBOSS services."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("pairwise alignment", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        seq_a = _require_sequence(arguments, "sequence_a")
        seq_b = _require_sequence(arguments, "sequence_b")
        if not seq_a or not seq_b:
            return {
                "status": "error",
                "error": "sequence_a and sequence_b are both required, each a "
                "single sequence in FASTA or raw form.",
            }

        algorithm = (arguments.get("algorithm") or "needle").lower()
        if algorithm not in _PAIRWISE_METHODS:
            return {
                "status": "error",
                "error": f"Unknown algorithm '{algorithm}'. "
                f"Choose one of: {', '.join(sorted(_PAIRWISE_METHODS))}.",
            }
        service, description = _PAIRWISE_METHODS[algorithm]

        params: Dict[str, Any] = {
            "asequence": seq_a,
            "bsequence": seq_b,
            "stype": arguments.get("sequence_type") or "protein",
        }
        for key, param in (("matrix", "matrix"), ("gap_open", "gapopen"),
                           ("gap_extend", "gapext")):
            if arguments.get(key) is not None:
                params[param] = arguments[key]

        outcome = _run_job(service, params, self.timeout)
        if outcome.get("status") == "error":
            return outcome

        text = outcome["text"]
        identity = re.search(r"# Identity:\s+\S+\s+\(\s*([\d.]+)%\)", text)
        similarity = re.search(r"# Similarity:\s+\S+\s+\(\s*([\d.]+)%\)", text)
        gaps = re.search(r"# Gaps:\s+\S+\s+\(\s*([\d.]+)%\)", text)
        score = re.search(r"# Score:\s+([\d.-]+)", text)

        return {
            "status": "success",
            "data": {
                "algorithm": algorithm,
                "alignment": text,
                "identity_percent": float(identity.group(1)) if identity else None,
                "similarity_percent": (
                    float(similarity.group(1)) if similarity else None
                ),
                "gaps_percent": float(gaps.group(1)) if gaps else None,
                "score": float(score.group(1)) if score else None,
            },
            "metadata": {
                "service": service,
                "description": description,
                "job_id": outcome["job_id"],
                "source": "EMBL-EBI Job Dispatcher",
            },
        }


@register_tool("EBITranslateSequenceTool")
class EBITranslateSequenceTool(BaseTool):
    """Translate or back-translate sequences via EMBL-EBI EMBOSS services."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("translation", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = _require_sequence(arguments)
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required, in FASTA or raw form.",
            }

        mode = (arguments.get("mode") or "dna_to_protein").lower()
        if mode not in _TRANSLATE_MODES:
            return {
                "status": "error",
                "error": f"Unknown mode '{mode}'. "
                f"Choose one of: {', '.join(sorted(_TRANSLATE_MODES))}.",
            }
        service, description = _TRANSLATE_MODES[mode]

        params: Dict[str, Any] = {"sequence": sequence}
        if arguments.get("codon_table") is not None:
            params["codontable"] = arguments["codon_table"]
        if mode == "dna_to_protein" and arguments.get("frame") is not None:
            params["frame"] = arguments["frame"]
        if mode == "six_frame" and arguments.get("min_orf_size") is not None:
            params["orfminsize"] = arguments["min_orf_size"]

        outcome = _run_job(service, params, self.timeout)
        if outcome.get("status") == "error":
            return outcome

        text = outcome["text"]
        return {
            "status": "success",
            "data": {
                "mode": mode,
                "result": text,
                "record_count": len(re.findall(r"^>", text, flags=re.MULTILINE)),
            },
            "metadata": {
                "service": service,
                "description": description,
                "job_id": outcome["job_id"],
                "source": "EMBL-EBI Job Dispatcher",
            },
        }


@register_tool("EBIPfamScanTool")
class EBIPfamScanTool(BaseTool):
    """Scan a protein sequence against Pfam HMMs via EMBL-EBI."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("PfamScan", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = _require_sequence(arguments)
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required: one protein sequence in FASTA "
                "or raw form.",
            }

        params: Dict[str, Any] = {
            "sequence": sequence,
            "database": arguments.get("database") or "pfam-a",
            "format": "json",
        }
        if arguments.get("evalue") is not None:
            params["evalue"] = arguments["evalue"]

        outcome = _run_job("pfamscan", params, self.timeout)
        if outcome.get("status") == "error":
            return outcome

        text = outcome["text"]
        # PfamScan returns a JSON array of hits, not a tabular report.
        try:
            hits = json.loads(text)
        except (TypeError, ValueError):
            hits = None

        if not isinstance(hits, list):
            return {
                "status": "error",
                "error": "PfamScan returned an unexpected result format. "
                f"First 200 characters: {text[:200]}",
            }

        domains: List[Dict[str, Any]] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            seq = hit.get("seq") or {}
            hmm = hit.get("hmm") or {}
            domains.append(
                {
                    "start": _int(seq.get("from")),
                    "end": _int(seq.get("to")),
                    "hmm_accession": hit.get("acc"),
                    "hmm_name": hit.get("name"),
                    "description": hit.get("desc"),
                    "type": hit.get("type"),
                    "clan": hit.get("clan"),
                    "bit_score": _float(hit.get("bits")),
                    "evalue": _float(hit.get("evalue")),
                    "significant": bool(hit.get("sig")),
                    "hmm_start": _int(hmm.get("from")),
                    "hmm_end": _int(hmm.get("to")),
                }
            )

        return {
            "status": "success",
            "data": domains,
            "metadata": {
                "service": "pfamscan",
                "database": params["database"],
                "domain_count": len(domains),
                "job_id": outcome["job_id"],
                "source": "EMBL-EBI Job Dispatcher",
            },
        }


@register_tool("EBIPhobiusTool")
class EBIPhobiusTool(BaseTool):
    """Predict transmembrane topology and signal peptides via Phobius."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("Phobius", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = _require_sequence(arguments)
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required: one protein sequence in FASTA "
                "or raw form.",
            }

        outcome = _run_job(
            "phobius",
            {"sequence": sequence, "stype": "protein", "format": "long"},
            self.timeout,
        )
        if outcome.get("status") == "error":
            return outcome

        text = outcome["text"]
        features: List[Dict[str, Any]] = []
        for line in text.splitlines():
            if not line.startswith("FT "):
                continue
            cols = line.split(None, 4)
            if len(cols) < 4:
                continue
            features.append(
                {
                    "feature": cols[1],
                    "start": _int(cols[2]),
                    "end": _int(cols[3]),
                    "note": cols[4].strip() if len(cols) > 4 else None,
                }
            )

        tm_count = sum(1 for f in features if f["feature"] == "TRANSMEM")
        has_signal = any(f["feature"] == "SIGNAL" for f in features)

        return {
            "status": "success",
            "data": {
                "transmembrane_helix_count": tm_count,
                "has_signal_peptide": has_signal,
                "features": features,
                "raw_output": text if not features else None,
            },
            "metadata": {
                "service": "phobius",
                "job_id": outcome["job_id"],
                "note": "Sequence-based prediction. For structure-derived "
                "topology see PDBTM and OPM resources.",
                "source": "EMBL-EBI Job Dispatcher",
            },
        }


@register_tool("EBIProfileSearchTool")
class EBIProfileSearchTool(BaseTool):
    """Iterative and profile-based sequence search via EMBL-EBI."""

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        return _guarded_run("profile search", self.timeout, self._run, arguments)

    def _run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = _require_sequence(arguments)
        if not sequence:
            return {
                "status": "error",
                "error": "sequence is required: one protein sequence in FASTA "
                "or raw form.",
            }

        method = (arguments.get("method") or "phmmer").lower()
        if method not in _PROFILE_METHODS:
            return {
                "status": "error",
                "error": f"Unknown method '{method}'. "
                f"Choose one of: {', '.join(sorted(_PROFILE_METHODS))}.",
            }
        service, description = _PROFILE_METHODS[method]

        allowed = _PHMMER_DATABASES if method == "phmmer" else _PSIBLAST_DATABASES
        database = arguments.get("database") or allowed[0]
        if database not in allowed:
            return {
                "status": "error",
                "error": f"Database '{database}' is not valid for {method}. "
                f"Choose one of: {', '.join(allowed)}.",
            }

        params: Dict[str, Any] = {"sequence": sequence, "database": database}
        if arguments.get("evalue") is not None:
            params["E" if method == "phmmer" else "expthr"] = arguments["evalue"]

        outcome = _run_job(service, params, self.timeout)
        if outcome.get("status") == "error":
            return outcome

        return {
            "status": "success",
            "data": {
                "method": method,
                "database": database,
                "result": outcome["text"],
            },
            "metadata": {
                "service": service,
                "description": description,
                "job_id": outcome["job_id"],
                "source": "EMBL-EBI Job Dispatcher",
            },
        }
