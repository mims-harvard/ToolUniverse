"""
IEDB Prediction Tool - MHC-I, MHC-II, processing and B-cell epitope prediction

T-cell predictions (MHC-I binding, MHC-II binding and antigen processing) run
against IEDB's next-generation tools API:

    https://api-nextgen-tools.iedb.org/api/v1

That API is asynchronous: a prediction is submitted as a *pipeline* stage
(``POST /pipeline``) and the caller then polls ``GET /results/{result_id}``
until the job reports ``status: "done"``. Results arrive as typed tables
(``table_columns`` + ``table_data``) rather than TSV text.

Fix-R29A-1: these three predictions previously used the legacy synchronous
endpoint ``https://tools-cluster-interface.iedb.org/tools_api/{mhci,mhcii,
processing}/``. That host still completes a TCP/TLS handshake and answers
GET with 405, but it never sends a response body for a POST -- confirmed
live, e.g.::

    curl -X POST --max-time 90 \\
      https://tools-cluster-interface.iedb.org/tools_api/mhci/ \\
      -d "method=netmhcpan_el&sequence_text=GILGFVFTL&allele=HLA-A*02:01&length=9"
    -> curl exit 28, http_code 000, time 90.00   (no bytes, ever)

so every call -- including each tool's own documented example -- stalled for
the full client timeout and then reported a misleading "timed out" error.
The ``bcell/`` route on that same legacy host does still answer (verified
live, HTTP 200 with real TSV in ~67 s) and is therefore left in place.

No authentication required for either API.
"""

import re
import time
import requests
import csv
import io
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool


IEDB_TOOLS_BASE = "https://tools-cluster-interface.iedb.org/tools_api"
IEDB_NEXTGEN_BASE = "https://api-nextgen-tools.iedb.org/api/v1"

# Methods accepted by the next-gen pipeline, per predictor type. Verified
# live against POST /pipeline (a name outside these sets is rejected with an
# opaque HTML 500, so it is worth catching client-side).
NEXTGEN_MHCI_METHODS = (
    "netmhcpan_el",
    "netmhcpan_ba",
    "netmhcpan",
    "ann",
    "smm",
    "smmpmbec",
    "comblib_sidney2008",
    "consensus",
    "mhcflurry",
    "mhcnp",
    "pickpocket",
)
NEXTGEN_MHCII_METHODS = (
    "netmhciipan_el",
    "netmhciipan_ba",
    "netmhciipan",
    "nn_align",
    "smm_align",
    "comblib",
    "tepitope",
    "consensus",
)

# Legacy tools_api spellings that the next-gen API renamed.
LEGACY_METHOD_ALIASES = {
    "netmhciipan": "netmhciipan_el",
    "nn_align_2.3": "nn_align",
    "smm_align_1.1": "smm_align",
    "sturniolo": "tepitope",
}


@register_tool("IEDBPredictionTool")
class IEDBPredictionTool(BaseTool):
    """
    Tool for predicting peptide-MHC binding using IEDB Analysis Resource.

    Supported operations:
    - predict_mhci: Predict MHC class I binding (CD8+ T cell epitopes)
    - predict_mhcii: Predict MHC class II binding (CD4+ T cell epitopes)
    - predict_processing: MHC-I binding chained with proteasomal cleavage
      and TAP transport (NetCTLpan)
    - predict_bcell: Linear B-cell epitope prediction (legacy tools_api)
    """

    #: Bound on how long the async next-gen pipeline is polled before the
    #: call is abandoned with an explicit message. Short peptides finish in
    #: roughly 10-20 s; nothing here should ever stall indefinitely.
    max_wait = 90
    #: Seconds between polls of GET /results/{id}.
    poll_interval = 3
    #: (connect, read) timeout for every individual HTTP request. A read
    #: timeout this short is safe because no next-gen request blocks on the
    #: prediction itself -- the work happens between polls.
    request_timeout: Tuple[int, int] = (10, 30)

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 120  # legacy bcell/ route only; predictions are slow
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "predict_mhci"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.endpoint_type == "predict_mhci":
                return self._predict_mhci(arguments)
            elif self.endpoint_type == "predict_mhcii":
                return self._predict_mhcii(arguments)
            elif self.endpoint_type == "predict_bcell":
                return self._predict_bcell(arguments)
            elif self.endpoint_type == "predict_processing":
                return self._predict_processing(arguments)
            return {
                "status": "error",
                "error": f"Unknown endpoint: {self.endpoint_type}",
            }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (
                    "IEDB did not respond within the request timeout "
                    f"{self.request_timeout}s (connect, read)."
                ),
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"IEDB request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"IEDB prediction error: {str(e)}"}

    # ------------------------------------------------------------------
    # Next-generation tools API (async pipeline) helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_allele(allele: str) -> str:
        """Translate legacy tools_api allele spellings to next-gen/MRO names.

        The next-gen API validates alleles against the MHC Restriction
        Ontology and rejects the legacy hyphenated mouse form: confirmed
        live, ``H-2-Kd`` returns ``{"errors": ["The following are not valid
        alleles: H-2-Kd"]}`` while ``H2-Kd`` predicts normally. This tool's
        own registered example used ``H-2-Kd``.
        """
        parts = [p.strip() for p in str(allele).split(",") if p.strip()]
        return ",".join(re.sub(r"^H-2-", "H2-", p) for p in parts)

    @staticmethod
    def _as_fasta(sequence: str) -> str:
        sequence = sequence.strip()
        if sequence.startswith(">"):
            return sequence
        return f">sequence_1\n{sequence}"

    @staticmethod
    def _table_rows(table: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Zip a next-gen result table's column names onto its row values."""
        names = [c.get("name") for c in table.get("table_columns", [])]
        return [dict(zip(names, row)) for row in table.get("table_data", [])]

    @staticmethod
    def _find_table(results: List[Dict[str, Any]], table_type: str):
        for table in results or []:
            if table.get("type") == table_type:
                return table
        return None

    def _submit_pipeline(
        self,
        tool_group: str,
        sequence: str,
        allele: str,
        length_range: List[int],
        predictors: List[Dict[str, str]],
    ):
        """POST a single-stage pipeline. Returns (result_id, warnings) or an
        error dict when the API rejects the request outright."""
        body = {
            "pipeline_id": "",
            "run_stage_range": [1, 1],
            "stages": [
                {
                    "stage_number": 1,
                    "tool_group": tool_group,
                    "input_sequence_text": self._as_fasta(sequence),
                    "input_parameters": {
                        "alleles": allele,
                        "peptide_length_range": length_range,
                        "predictors": predictors,
                    },
                }
            ],
        }
        resp = requests.post(
            f"{IEDB_NEXTGEN_BASE}/pipeline",
            json=body,
            timeout=self.request_timeout,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": (
                    f"IEDB next-generation tools API rejected the submission "
                    f"(HTTP {resp.status_code}): {resp.text[:300]!r}"
                ),
            }
        payload = resp.json()
        # A validation failure (bad allele, incompatible length) still comes
        # back as HTTP 200 -- but with `errors` and no `result_id`.
        if "result_id" not in payload:
            errors = payload.get("errors") or ["unspecified validation failure"]
            return {
                "status": "error",
                "error": f"IEDB rejected the prediction request: {'; '.join(errors)}",
            }
        return payload["result_id"], payload.get("warnings") or []

    def _poll_results(self, result_id: str):
        """Poll GET /results/{id} until the job is terminal.

        Returns the ``data`` block on success, or an error dict. Note that a
        failed stage surfaces as a populated ``data.errors`` list which may
        keep reporting ``status: "pending"`` indefinitely (confirmed live),
        so errors -- not just the status field -- must terminate the loop.
        """
        deadline = time.monotonic() + self.max_wait
        last_status = "unknown"
        while True:
            resp = requests.get(
                f"{IEDB_NEXTGEN_BASE}/results/{result_id}",
                timeout=self.request_timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data") or {}
            errors = data.get("errors") or []
            last_status = payload.get("status", "unknown")
            if errors:
                return {
                    "status": "error",
                    "error": (
                        f"IEDB prediction failed (result_id={result_id}): "
                        f"{'; '.join(str(e) for e in errors)[:600]}"
                    ),
                }
            if last_status == "done":
                return data
            if last_status == "error":
                return {
                    "status": "error",
                    "error": (
                        f"IEDB reported an unspecified failure for "
                        f"result_id={result_id}"
                    ),
                }
            if time.monotonic() + self.poll_interval >= deadline:
                return {
                    "status": "error",
                    "error": (
                        f"IEDB prediction did not finish within {self.max_wait}s "
                        f"(last status: {last_status!r}, result_id={result_id}). "
                        f"Results may still appear at "
                        f"{IEDB_NEXTGEN_BASE}/results/{result_id}"
                    ),
                }
            time.sleep(self.poll_interval)

    def _resolve_method(
        self, method: str, allowed: Tuple[str, ...], label: str
    ) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        method = LEGACY_METHOD_ALIASES.get(method, method)
        if method not in allowed:
            return None, {
                "status": "error",
                "error": (
                    f"Unsupported {label} method {method!r}. The IEDB "
                    f"next-generation tools API accepts: {', '.join(allowed)}"
                ),
            }
        return method, None

    @staticmethod
    def _first_present(row: Dict[str, Any], keys):
        for key in keys:
            if row.get(key) is not None:
                return row[key]
        return None

    def _peptide_rows(self, data: Dict[str, Any], method: str) -> List[Dict[str, Any]]:
        """Extract the peptide table and attach a uniform percentile_rank.

        Every next-gen peptide table carries ``median_percentile`` plus
        method-specific score columns. Single-algorithm methods name those
        ``<method>_percentile`` / ``<method>_score`` / ``<method>_ic50``
        (verified live for netmhcpan_el, netmhcpan_ba, ann, smm,
        netmhciipan_el, netmhciipan_ba, nn_align); the aggregate
        ``netmhcpan`` method instead uses the dotted
        ``binding.<method>.percentile`` form (also verified live), so both
        spellings are consulted before falling back to the median.
        """
        table = self._find_table(data.get("results", []), "peptide_table")
        rows = self._table_rows(table) if table else []
        for row in rows:
            rank = self._first_present(
                row,
                (
                    f"{method}_percentile",
                    f"binding.{method}.percentile",
                    "median_percentile",
                ),
            )
            if rank is not None:
                row["percentile_rank"] = rank
            score = self._first_present(
                row,
                (
                    f"{method}_score",
                    f"{method}_ic50",
                    f"binding.{method}.score",
                    f"binding.{method}.ic50",
                ),
            )
            if score is not None:
                row["score"] = score
        rows.sort(
            key=lambda r: (
                r["percentile_rank"]
                if isinstance(r.get("percentile_rank"), (int, float))
                else float("inf")
            )
        )
        return rows

    @staticmethod
    def _merge_warnings(*groups) -> List[str]:
        """Union of submit-time and result-time warnings, order preserved.

        The pipeline echoes its submission warnings back on the result, so
        concatenating the two lists otherwise reports each one twice.
        """
        merged: List[str] = []
        for group in groups:
            for warning in group or []:
                if warning not in merged:
                    merged.append(warning)
        return merged

    def _parse_tsv(self, text: str) -> List[Dict[str, str]]:
        text = text.strip()
        # Fix-R18D-1: IEDB's prediction endpoints return HTTP 200 with a
        # plain-text validation error (e.g. "The length of input sequence
        # is less than the input/default length 15.") instead of TSV data
        # for invalid input like a too-short sequence -- confirmed live.
        # csv.DictReader silently treated the error's first line as a
        # single-column header and the second as one data row, and the
        # caller's `.get("percentile_rank", 100)` fallback then made this
        # look like a real (if suspicious) successful prediction. Detect
        # the non-tabular response before parsing and raise instead, so
        # `run()`'s exception handler reports it as the error it is.
        if not text or "\t" not in text.splitlines()[0]:
            raise ValueError(
                f"IEDB tool returned a non-tabular response, likely an "
                f"input validation error rather than prediction data: "
                f"{text[:300]!r}"
            )
        reader = csv.DictReader(io.StringIO(text), delimiter="\t")
        return [dict(row) for row in reader]

    @staticmethod
    def _iedb_error_response(text: str) -> Dict[str, Any] | None:
        """Detect IEDB's plain-text error responses (e.g. an invalid allele
        name), which return HTTP 200 with prose instead of a TSV table --
        parsing that as TSV silently produces bogus rows keyed on the error
        message itself. Returns an error dict if `text` isn't real TSV data,
        else None.
        """
        first_line = text.strip().split("\n", 1)[0]
        if "\t" in first_line:
            return None
        return {
            "status": "error",
            "error": f"IEDB API error: {first_line}",
        }

    def _predict_bcell(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Predict linear B-cell epitopes along a protein sequence.

        Uses the IEDB B-cell tool (default BepiPred), which scores every residue;
        contiguous runs above the threshold are candidate antibody epitopes.
        """
        sequence = arguments.get("sequence", "")
        method = arguments.get("method", "Bepipred")
        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        resp = requests.post(
            f"{IEDB_TOOLS_BASE}/bcell/",
            data={"method": method, "sequence_text": sequence},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        err = self._iedb_error_response(resp.text)
        if err:
            return err
        rows = self._parse_tsv(resp.text)

        residues = []
        for r in rows:
            try:
                score = float(r.get("Score", 0))
            except (ValueError, TypeError):
                score = None
            residues.append(
                {
                    "position": r.get("Position"),
                    "residue": r.get("Residue"),
                    "score": score,
                    "epitope": r.get("Assignment") == "E",
                }
            )

        # Collapse the per-residue "E" assignments into contiguous epitope regions.
        regions = []
        start = None
        for i, res in enumerate(residues):
            if res["epitope"] and start is None:
                start = i
            elif not res["epitope"] and start is not None:
                seg = residues[start:i]
                regions.append(
                    {
                        "start": seg[0]["position"],
                        "end": seg[-1]["position"],
                        "peptide": "".join(s["residue"] or "" for s in seg),
                        "mean_score": round(
                            sum(s["score"] or 0 for s in seg) / len(seg), 4
                        ),
                    }
                )
                start = None
        if start is not None:
            seg = residues[start:]
            regions.append(
                {
                    "start": seg[0]["position"],
                    "end": seg[-1]["position"],
                    "peptide": "".join(s["residue"] or "" for s in seg),
                    "mean_score": round(
                        sum(s["score"] or 0 for s in seg) / len(seg), 4
                    ),
                }
            )

        return {
            "status": "success",
            "data": {"epitope_regions": regions, "per_residue": residues},
            "metadata": {
                "method": method,
                "n_epitope_regions": len(regions),
                "sequence_length": len(residues),
                "source": "IEDB Analysis Resource (B-cell)",
                "interpretation": (
                    "Residues assigned 'E' (score above the method threshold) are "
                    "predicted to be in a linear B-cell (antibody) epitope; "
                    "epitope_regions are the contiguous stretches."
                ),
            },
        }

    def _predict_processing(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Predict MHC class I antigen processing (cleavage + TAP + MHC-I).

        Runs the next-gen T-cell class I pipeline with both a binding
        predictor and the NetCTLpan processing predictor, so each peptide is
        scored for natural processing and presentation rather than raw
        binding alone. Verified live: the peptide table gains the columns
        ``cleavage_prediction_score``, ``tap_prediction_score``,
        ``mhc_prediction`` and ``combined_prediction_score`` alongside the
        binding columns.
        """
        sequence = arguments.get("sequence") or arguments.get("sequence_text", "")
        allele = arguments.get("allele", "HLA-A*02:01")
        method = arguments.get("method", "netmhcpan")
        length = arguments.get("length") or 9

        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        method, err = self._resolve_method(method, NEXTGEN_MHCI_METHODS, "MHC-I")
        if err:
            return err
        allele = self._normalize_allele(allele)
        length = int(length)

        submitted = self._submit_pipeline(
            "mhci",
            sequence,
            allele,
            [length, length],
            [
                {"type": "binding", "method": method},
                {"type": "processing", "method": "netctlpan"},
            ],
        )
        if isinstance(submitted, dict):
            return submitted
        result_id, warnings = submitted

        data = self._poll_results(result_id)
        if data.get("status") == "error":
            return data

        table = self._find_table(data.get("results", []), "peptide_table")
        results = self._table_rows(table) if table else []

        # Higher combined_prediction_score = more likely to be cleaved,
        # transported and presented.
        results.sort(
            key=lambda x: (
                x.get("combined_prediction_score")
                if isinstance(x.get("combined_prediction_score"), (int, float))
                else float("-inf")
            ),
            reverse=True,
        )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "method": method,
                "processing_method": "netctlpan",
                "allele": allele,
                "length": length,
                "n_peptides": len(results),
                "source": "IEDB next-generation tools API (T cell class I)",
                "result_id": result_id,
                "warnings": self._merge_warnings(warnings, data.get("warnings")),
                "interpretation": (
                    "cleavage_prediction_score = proteasomal C-terminal "
                    "cleavage; tap_prediction_score = TAP transport "
                    "efficiency; mhc_prediction = MHC-I binding component; "
                    "combined_prediction_score merges all three (higher = "
                    "more likely naturally processed and presented to CD8+ "
                    "T cells). The binding columns "
                    "(<method>_ic50 / <method>_score, <method>_percentile) "
                    "carry the raw affinity prediction."
                ),
            },
        }

    def _predict_mhci(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence", "")
        allele = arguments.get("allele", "HLA-A*02:01")
        method = arguments.get("method", "netmhcpan_el")
        length = arguments.get("length") or 9

        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        method, err = self._resolve_method(method, NEXTGEN_MHCI_METHODS, "MHC-I")
        if err:
            return err
        allele = self._normalize_allele(allele)
        length = int(length)

        submitted = self._submit_pipeline(
            "mhci",
            sequence,
            allele,
            [length, length],
            [{"type": "binding", "method": method}],
        )
        if isinstance(submitted, dict):
            return submitted
        result_id, warnings = submitted

        data = self._poll_results(result_id)
        if data.get("status") == "error":
            return data

        results = self._peptide_rows(data, method)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "method": method,
                "allele": allele,
                "length": length,
                "n_peptides": len(results),
                "source": "IEDB next-generation tools API (T cell class I)",
                "result_id": result_id,
                "warnings": self._merge_warnings(warnings, data.get("warnings")),
                "interpretation": (
                    "percentile_rank < 0.5% = strong binder, "
                    "0.5-2% = moderate binder, >2% = weak/non-binder"
                ),
            },
        }

    def _predict_mhcii(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence", "")
        allele = arguments.get("allele", "HLA-DRB1*01:01")
        method = arguments.get("method", "netmhciipan_el")

        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        method, err = self._resolve_method(method, NEXTGEN_MHCII_METHODS, "MHC-II")
        if err:
            return err
        allele = self._normalize_allele(allele)

        # The class II sliding window defaults to 15 residues and cannot
        # exceed the input sequence, so shrink it for short peptides (this
        # tool's own registered example is a 13-mer).
        length = arguments.get("length")
        if length is None:
            length = min(15, len(sequence.strip()))
        length = int(length)

        submitted = self._submit_pipeline(
            "mhcii",
            sequence,
            allele,
            [length, length],
            [{"type": "binding", "method": method}],
        )
        if isinstance(submitted, dict):
            return submitted
        result_id, warnings = submitted

        data = self._poll_results(result_id)
        if data.get("status") == "error":
            return data

        results = self._peptide_rows(data, method)

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "method": method,
                "allele": allele,
                "length": length,
                "n_peptides": len(results),
                "source": "IEDB next-generation tools API (T cell class II)",
                "result_id": result_id,
                "warnings": self._merge_warnings(warnings, data.get("warnings")),
                "interpretation": (
                    "percentile_rank < 2% = strong binder, "
                    "2-10% = weak binder, >10% = non-binder (NetMHCIIpan convention)"
                ),
            },
        }
