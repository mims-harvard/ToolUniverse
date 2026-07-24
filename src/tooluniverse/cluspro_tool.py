"""ClusPro peptide-protein docking tool (submit; requires a free academic key).

ClusPro (https://cluspro.bu.edu, Vajda/Kozakov lab) is the standard rigid-body
docking server and has a native **peptide docking mode**. It exposes a real HTTP
REST API (``/api.php`` submit) documented in the open-source ``cluspro-api``
package; this tool replicates that flow exactly (sorted ``key+value`` HMAC-MD5
signature). Docking is asynchronous (hours); this tool SUBMITS a job and returns
the ClusPro job id — retrieve results from the ClusPro account/results page.

Access: ClusPro is FREE for academic / government / non-profit use (PIPER is
licensed to Acpharis/Schrodinger for commercial use). Create a free account at
cluspro.bu.edu, then copy your username + API secret from the API tab and set
``CLUSPRO_USERNAME`` and ``CLUSPRO_API_SECRET`` in the environment.

NOTE: ClusPro peptide mode targets SHORT peptides (motif-based; typically up to
~30 residues). It docks the peptide against a receptor given as a 4-letter PDB
code (or an uploaded structure — not exposed here).
"""

import hashlib
import hmac
import os
from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_API_URL = "https://cluspro.bu.edu/api.php"
_TIMEOUT = 30


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _make_sig(form: Dict[str, Any], secret: str) -> str:
    """Replicate cluspro-api make_sig: sorted key+value concat, HMAC-MD5 hex."""
    msg = "".join(f"{k}{form[k]}" for k in sorted(form) if form[k] is not None)
    return hmac.new(
        secret.encode("utf-8"), msg.encode("utf-8"), hashlib.md5
    ).hexdigest()


@register_tool(
    "ClusProSubmitPeptideDockingTool",
    config={
        "name": "ClusPro_submit_peptide_docking",
        "type": "ClusProSubmitPeptideDockingTool",
        "description": (
            "Submit a peptide-protein docking job to ClusPro (peptide mode) and "
            "return the ClusPro job id. Docks a short peptide (motif + sequence) "
            "against a receptor given by 4-letter PDB code. Docking is "
            "asynchronous (hours); retrieve clustered poses + scores from your "
            "ClusPro results page. Requires a FREE academic ClusPro account: set "
            "CLUSPRO_USERNAME and CLUSPRO_API_SECRET. Peptide mode is for SHORT "
            "peptides (~<=30 residues)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "receptor_pdb_id": {
                    "type": "string",
                    "description": "4-letter PDB code of the receptor protein, e.g. '1A2K'.",
                },
                "peptide_sequence": {
                    "type": "string",
                    "description": "Peptide amino-acid sequence (1-letter), e.g. 'KGRRL'. Short peptides only.",
                },
                "peptide_motif": {
                    "type": ["string", "null"],
                    "description": (
                        "Peptide motif for PDB fragment search (X = wildcard), e.g. "
                        "'KXRRL'. Defaults to peptide_sequence if omitted."
                    ),
                },
                "jobname": {
                    "type": ["string", "null"],
                    "description": "Optional job name (defaults to a ClusPro job number).",
                },
            },
            "required": ["receptor_pdb_id", "peptide_sequence"],
        },
        "required_api_keys": ["CLUSPRO_USERNAME", "CLUSPRO_API_SECRET"],
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "object",
                            "properties": {"job_id": {"type": ["string", "integer"]}},
                        },
                        "metadata": {"type": "object"},
                    },
                    "required": ["status", "data"],
                },
                {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "error": {"type": "string"},
                    },
                    "required": ["status", "error"],
                },
            ]
        },
        "test_examples": [
            {
                "receptor_pdb_id": "1A2K",
                "peptide_sequence": "KGRRL",
                "peptide_motif": "KXRRL",
            }
        ],
    },
)
class ClusProSubmitPeptideDockingTool(BaseTool):
    """Submit a ClusPro peptide-docking job; returns the job id."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        username = os.environ.get("CLUSPRO_USERNAME")
        secret = os.environ.get("CLUSPRO_API_SECRET")
        if not username or not secret:
            return _err(
                "Requires a free academic ClusPro account: set CLUSPRO_USERNAME "
                "and CLUSPRO_API_SECRET (register at cluspro.bu.edu, copy from the API tab)."
            )

        recpdb = (arguments.get("receptor_pdb_id") or "").strip()
        pepseq = (arguments.get("peptide_sequence") or "").strip().upper()
        if not recpdb:
            return _err("receptor_pdb_id (4-letter PDB code) is required")
        if not pepseq:
            return _err("peptide_sequence is required")
        pepmot = (arguments.get("peptide_motif") or pepseq).strip().upper()

        # Form replicates cluspro-api peptide-mode submission with a PDB-code receptor.
        form: Dict[str, Any] = {
            "username": username,
            "recpdb": recpdb,
            "userecpdbid": "1",
            "rec-input-type": "pdb",
            "useligpdbid": "1",
            "pepmot": pepmot,
            "pepseq": pepseq,
            "peptidemode": "1",
            "usepeptide": "1",
            "userecrepfile": "0",
            "useligrepfile": "0",
            "userestraints": "0",
            "usesaxs": "0",
        }
        jobname = arguments.get("jobname")
        if jobname:
            form["jobname"] = str(jobname)
        form["sig"] = _make_sig(form, secret)

        try:
            resp = requests.post(_API_URL, data=form, timeout=_TIMEOUT)
            resp.raise_for_status()
            result = resp.json()
        except requests.RequestException as exc:
            return _err(f"ClusPro submission failed: {exc}", url=_API_URL)
        except ValueError as exc:
            return _err(f"ClusPro returned non-JSON: {exc}", url=_API_URL)

        if isinstance(result, dict) and result.get("status") == "success":
            return {
                "status": "success",
                "data": {"job_id": result.get("id")},
                "metadata": {
                    "source": "ClusPro peptide docking",
                    "url": _API_URL,
                    "receptor_pdb_id": recpdb,
                    "peptide_sequence": pepseq,
                    "note": "Asynchronous job; retrieve poses+scores from your ClusPro results page.",
                },
            }
        errors = result.get("errors") if isinstance(result, dict) else result
        return _err(f"ClusPro rejected the job: {errors}", url=_API_URL)
