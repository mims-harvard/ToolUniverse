"""IUPred3 intrinsic protein disorder prediction tool.

Wraps the IUPred3 REST API, which runs the IUPred algorithm to predict
intrinsically disordered regions of a protein directly from its sequence
(via UniProt accession or ID). Unlike database lookups (MobiDB, DisProt),
this is an on-the-fly machine-learning style prediction.

API: https://iupred3.elte.hu/iupred3/{type}/{accession}.json
No authentication required. Fast (<5 s).

Prediction types:
  - long   : long disordered regions (default)
  - short  : short disordered regions (e.g. missing residues in PDB)
  - anchor : long disorder + ANCHOR2 protein-binding-region scores
  - glob   : globular-domain-aware disorder
  - redox  : redox-state-dependent disorder (oxidised/reduced scores)

Reference:
  Erdos G, Pajkos M, Dosztanyi Z. IUPred3. Nucleic Acids Research 2021.
"""

import json
import urllib.error
import urllib.request
from typing import Any, Dict, List

from .tool_registry import register_tool

IUPRED3_BASE = "https://iupred3.elte.hu/iupred3"
VALID_TYPES = ("long", "short", "anchor", "glob", "redox")
DISORDER_THRESHOLD = 0.5


def _regions_from_scores(scores: List[float], threshold: float) -> List[Dict[str, int]]:
    """Collapse a per-residue score list into contiguous regions above threshold.

    Positions are 1-based and inclusive.
    """
    regions: List[Dict[str, int]] = []
    start = None
    for idx, score in enumerate(scores):
        above = score is not None and score >= threshold
        if above and start is None:
            start = idx + 1
        elif not above and start is not None:
            regions.append({"start": start, "end": idx, "length": idx - start + 1})
            start = None
    if start is not None:
        end = len(scores)
        regions.append({"start": start, "end": end, "length": end - start + 1})
    return regions


def _per_residue(
    sequence: str, iupred: List[float], anchor: List[float] | None
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for i, aa in enumerate(sequence):
        row: Dict[str, Any] = {
            "position": i + 1,
            "residue": aa,
            "disorder_score": (
                round(iupred[i], 4)
                if i < len(iupred) and iupred[i] is not None
                else None
            ),
        }
        if anchor is not None and i < len(anchor) and anchor[i] is not None:
            row["anchor_score"] = round(anchor[i], 4)
        rows.append(row)
    return rows


@register_tool(
    "IUPred3Tool",
    config={
        "name": "IUPred3_predict_disorder",
        "type": "IUPred3Tool",
        "description": (
            "Predict intrinsically disordered protein regions from sequence using "
            "the IUPred3 algorithm. Input a UniProt accession or ID (e.g. P04637). "
            "Returns per-residue disorder scores (0-1, higher = more disordered), "
            "predicted disordered region segments (score >= 0.5), and summary "
            "statistics. The 'anchor' type also returns ANCHOR2 protein-binding "
            "region scores. No authentication required."
        ),
        "parameter": {
            "type": "object",
            "properties": {
                "accession": {
                    "type": "string",
                    "description": (
                        "UniProt accession or entry ID, e.g. 'P04637' (human p53) "
                        "or 'TP53_HUMAN'. The IUPred3 server links to the latest "
                        "UniProt release and fetches the sequence automatically."
                    ),
                },
                "iupred_type": {
                    "type": "string",
                    "enum": ["long", "short", "anchor", "glob", "redox"],
                    "description": (
                        "Prediction mode. 'long' (default) = long disordered "
                        "regions; 'short' = short disorder (e.g. missing PDB "
                        "residues); 'anchor' = long disorder plus ANCHOR2 "
                        "binding-region scores; 'glob' = globular-domain-aware "
                        "disorder; 'redox' = redox-state-dependent disorder."
                    ),
                },
            },
            "required": ["accession"],
        },
    },
)
class IUPred3Tool:
    def __init__(self, tool_config=None):
        self.tool_config = tool_config or {}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession = (arguments.get("accession") or "").strip()
        if not accession:
            return {"status": "error", "error": "accession is required"}

        iupred_type = (arguments.get("iupred_type") or "long").strip().lower()
        if iupred_type not in VALID_TYPES:
            return {
                "status": "error",
                "error": "Invalid iupred_type '{}'. Must be one of: {}".format(
                    iupred_type, ", ".join(VALID_TYPES)
                ),
            }

        # Guard against path-injection / malformed accessions.
        if "/" in accession or " " in accession or len(accession) > 40:
            return {
                "status": "error",
                "error": "Invalid accession format: '{}'".format(accession),
            }

        url = "{}/{}/{}.json".format(IUPRED3_BASE, iupred_type, accession)

        try:
            req = urllib.request.Request(url, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "error": "IUPred3 API returned HTTP {}: {}".format(e.code, e.reason),
            }
        except urllib.error.URLError as e:
            return {
                "status": "error",
                "error": "Failed to connect to IUPred3 API: {}".format(str(e.reason)),
            }
        except Exception as e:  # noqa: BLE001 - run() must never raise
            return {
                "status": "error",
                "error": "IUPred3 request failed: {}".format(str(e)),
            }

        # IUPred3 returns HTTP 200 with "<pre>ACC not found!</pre>" for
        # unknown accessions instead of a proper error code.
        if "not found" in body.lower() and not body.lstrip().startswith("{"):
            return {
                "status": "error",
                "error": "Accession '{}' not found by IUPred3.".format(accession),
            }

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": "IUPred3 returned a non-JSON response (accession may be invalid).",
            }

        sequence = payload.get("sequence") or ""
        if not sequence:
            return {
                "status": "error",
                "error": "IUPred3 returned no sequence for '{}'.".format(accession),
            }

        # The disorder score key differs for the redox mode.
        if iupred_type == "redox":
            iupred_scores = (
                payload.get("iupred2_redox_minus")
                or payload.get("iupred2_redox_plus")
                or []
            )
        else:
            iupred_scores = payload.get("iupred2") or []

        anchor_scores = payload.get("anchor2")

        regions = _regions_from_scores(iupred_scores, DISORDER_THRESHOLD)
        disordered_residues = sum(r["length"] for r in regions)
        length = len(sequence)
        valid_scores = [s for s in iupred_scores if s is not None]
        mean_score = (
            round(sum(valid_scores) / len(valid_scores), 4) if valid_scores else None
        )

        data: Dict[str, Any] = {
            "accession": accession,
            "iupred_type": iupred_type,
            "sequence_length": length,
            "mean_disorder_score": mean_score,
            "disordered_residues": disordered_residues,
            "disordered_fraction": (
                round(disordered_residues / length, 4) if length else 0.0
            ),
            "disordered_regions": regions,
            "per_residue": _per_residue(sequence, iupred_scores, anchor_scores),
            "sequence": sequence,
        }

        if anchor_scores is not None:
            anchor_regions = _regions_from_scores(anchor_scores, DISORDER_THRESHOLD)
            data["anchor_binding_regions"] = anchor_regions

        if iupred_type == "redox":
            data["redox_sensitive_regions"] = payload.get("redox_sensitive_regions", [])

        return {"status": "success", "data": data}
