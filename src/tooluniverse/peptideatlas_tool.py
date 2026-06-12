"""PeptideAtlas observed-peptide tool (live REST, keyless).

PeptideAtlas (SBEAMS PeptideAtlas, Institute for Systems Biology) is the
canonical repository of peptides that have actually been observed by tandem
mass spectrometry across many proteomics experiments. Unlike sequence-derived
peptide-coverage resources (e.g. the EBI Proteins coverage endpoint, which
only lists where tryptic peptides map and whether they are unique), PeptideAtlas
reports *empirical* observation data: how many spectra (n_observations) and
how many samples (n_samples) each peptide was seen in, the best PeptideProphet
probability, an empirical proteotypic score, and SSRCalc hydrophobicity.

``PeptideAtlasGetObservedPeptidesTool`` (PeptideAtlas_get_observed_peptides)
queries the GetPeptides endpoint for one protein/gene (or the whole build) and
returns the observed-peptide table.

The public ``GetPeptides`` CGI is keyless. JSON is requested with
``output_mode=json`` and ``apply_action=QUERY``; a build is selected with
``atlas_build_id`` (Human 2024-01 = 572) and a protein with
``biosequence_name_constraint`` (a UniProt accession or biosequence name).
"""

from typing import Any, Dict

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://db.systemsbiology.net/sbeams/cgi/PeptideAtlas/GetPeptides"
_TIMEOUT = 30
_HEADERS = {"Accept": "application/json"}
_DEFAULT_BUILD_ID = 572  # Human 2024-01


def _err(message: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": message}
    out.update(extra)
    return out


def _as_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@register_tool(
    "PeptideAtlasGetObservedPeptidesTool",
    config={
        "name": "PeptideAtlas_get_observed_peptides",
        "type": "PeptideAtlasGetObservedPeptidesTool",
        "description": (
            "Query PeptideAtlas (SBEAMS PeptideAtlas, ISB) for the "
            "mass-spectrometry-OBSERVED peptides of a protein/gene, the "
            "canonical record of which tryptic peptides have actually been "
            "seen in MS proteomics experiments and how often. Constrain by a "
            "UniProt accession or biosequence name (biosequence_name), or omit "
            "it to sample the whole build. Each record returns: "
            "peptide_accession (PAp...), peptide_sequence, n_observations "
            "(spectral count across the atlas), n_samples (number of samples), "
            "best_probability (PeptideProphet), empirical_proteotypic_score, "
            "SSRCalc_relative_hydrophobicity, n_protein_mappings, "
            "n_genome_locations, is_exon_spanning, protease_ids, and "
            "is_subpeptide_of. Distinct from sequence-derived peptide-coverage "
            "tools: PeptideAtlas adds empirical observation frequency and "
            "proteotypic scoring. Keyless public CGI; default build is "
            "Human 2024-01 (atlas_build_id=572)."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "biosequence_name": {
                    "type": "string",
                    "description": (
                        "Protein/gene constraint: a UniProt accession or "
                        "PeptideAtlas biosequence name. Example: 'P02768' "
                        "(human serum albumin) -> several thousand observed "
                        "peptides. Maps to biosequence_name_constraint. Omit "
                        "to query the whole build (use a small row_limit)."
                    ),
                },
                "atlas_build_id": {
                    "type": ["integer", "string"],
                    "description": (
                        "PeptideAtlas build to query. Default 572 (Human 2024-01)."
                    ),
                },
                "row_limit": {
                    "type": ["integer", "string"],
                    "description": (
                        "Maximum number of peptide rows to return "
                        "(default 500). Use a small value (e.g. 2-5) for "
                        "whole-build sampling, since a build holds millions of "
                        "peptides."
                    ),
                },
            },
            "required": [],
        },
        "return_schema": {
            "oneOf": [
                {
                    "type": "object",
                    "description": "Successful observed-peptide query.",
                    "properties": {
                        "status": {"type": "string", "enum": ["success"]},
                        "data": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "peptide_accession": {"type": "string"},
                                    "peptide_sequence": {"type": "string"},
                                    "n_observations": {"type": ["integer", "string"]},
                                    "n_samples": {"type": ["integer", "string"]},
                                    "best_probability": {"type": ["string", "number"]},
                                    "n_protein_mappings": {
                                        "type": ["integer", "string"]
                                    },
                                    "n_genome_locations": {
                                        "type": ["integer", "string"]
                                    },
                                    "is_exon_spanning": {"type": "string"},
                                    "empirical_proteotypic_score": {
                                        "type": ["string", "number", "null"]
                                    },
                                    "SSRCalc_relative_hydrophobicity": {
                                        "type": ["string", "number", "null"]
                                    },
                                    "protease_ids": {"type": ["string", "null"]},
                                    "is_subpeptide_of": {"type": ["string", "null"]},
                                    "organism_full_name": {"type": "string"},
                                    "atlas build name": {"type": "string"},
                                },
                            },
                            "description": (
                                "Observed MS peptides for the protein/build."
                            ),
                        },
                        "metadata": {
                            "type": "object",
                            "properties": {
                                "source": {"type": "string"},
                                "url": {"type": "string"},
                                "atlas_build_id": {"type": "integer"},
                                "biosequence_name": {"type": ["string", "null"]},
                                "row_limit": {"type": "integer"},
                                "returned_count": {"type": "integer"},
                            },
                        },
                    },
                    "required": ["status", "data", "metadata"],
                },
                {
                    "type": "object",
                    "description": "Error result.",
                    "properties": {
                        "status": {"type": "string", "enum": ["error"]},
                        "error": {"type": "string"},
                        "url": {"type": "string"},
                        "response_snippet": {"type": "string"},
                    },
                    "required": ["status", "error"],
                },
            ]
        },
        "test_examples": [
            {"biosequence_name": "P02768", "row_limit": 5},
            {"row_limit": 2},
        ],
        "label": [
            "PeptideAtlas",
            "Proteomics",
            "Mass Spectrometry",
            "Observed Peptide",
            "Proteotypic",
        ],
        "metadata": {
            "tags": [
                "PeptideAtlas",
                "proteomics",
                "mass spectrometry",
                "observed peptide",
                "proteotypic",
                "SSRCalc",
                "peptide",
            ],
            "estimated_execution_time": "2-10 seconds",
        },
    },
)
class PeptideAtlasGetObservedPeptidesTool(BaseTool):
    """Query PeptideAtlas for MS-observed peptides of a protein/build."""

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}

        build_id = _as_int(arguments.get("atlas_build_id"), _DEFAULT_BUILD_ID)
        row_limit = _as_int(arguments.get("row_limit"), 500)
        if row_limit <= 0:
            row_limit = 500

        biosequence = arguments.get("biosequence_name")
        if biosequence is not None:
            biosequence = str(biosequence).strip() or None

        params: Dict[str, Any] = {
            "atlas_build_id": build_id,
            "output_mode": "json",
            "apply_action": "QUERY",
            "row_limit": row_limit,
        }
        if biosequence:
            params["biosequence_name_constraint"] = biosequence

        try:
            resp = requests.get(
                _BASE_URL, params=params, headers=_HEADERS, timeout=_TIMEOUT
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Request to PeptideAtlas failed: {exc}")

        if resp.status_code != 200:
            return _err(
                f"PeptideAtlas returned HTTP {resp.status_code}",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        try:
            payload = resp.json()
        except ValueError:
            return _err(
                "PeptideAtlas returned a non-JSON response (the protein may "
                "be unknown to this build, or the query was rejected).",
                url=resp.url,
                response_snippet=(resp.text or "")[:200],
            )

        # GetPeptides returns a bare JSON array of peptide objects; some error
        # conditions return an object with the array under "data"/"peptides".
        if isinstance(payload, list):
            records = payload
        elif isinstance(payload, dict):
            records = payload.get("data") or payload.get("peptides") or []
        else:
            return _err("Unexpected PeptideAtlas response shape", url=resp.url)

        if not isinstance(records, list):
            return _err("Unexpected PeptideAtlas data shape", url=resp.url)

        if not records:
            target = f" for biosequence {biosequence!r}" if biosequence else ""
            return _err(
                f"No observed peptides found{target} in atlas build {build_id}.",
                url=resp.url,
            )

        return {
            "status": "success",
            "data": records,
            "metadata": {
                "source": "PeptideAtlas (SBEAMS PeptideAtlas, ISB)",
                "url": resp.url,
                "atlas_build_id": build_id,
                "biosequence_name": biosequence,
                "row_limit": row_limit,
                "returned_count": len(records),
            },
        }
