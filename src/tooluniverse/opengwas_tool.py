"""
OpenGWAS (IEU) tool for ToolUniverse.

Fetches the genetic instruments needed for a custom two-sample Mendelian
randomization analysis from the IEU OpenGWAS database: the genome-wide
significant, LD-clumped SNPs for an exposure GWAS (``/tophits``) and those
same SNPs' effects in an outcome GWAS (``/associations``), harmonized onto a
common effect allele so they are ready to feed into an MR estimator.

This complements EpiGraphDB's pre-computed MR-EvE results (which only cover
curated trait pairs) by letting callers assemble instruments for arbitrary
exposure/outcome GWAS pairs.

API: https://api.opengwas.io/api  (POST /tophits, POST /associations)
Auth: free JWT token in the OPENGWAS_JWT environment variable
      (register at https://api.opengwas.io).
"""

import os
import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

OPENGWAS_BASE = "https://api.opengwas.io/api"


@register_tool("OpenGWASTool")
class OpenGWASTool(BaseTool):
    """Assemble harmonized two-sample MR instruments from IEU OpenGWAS."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Clumping at the API can be slow, so allow a generous default.
        self.timeout = tool_config.get("fields", {}).get("timeout", 60)

    def _headers(self):
        """Bearer headers, or None when no token is configured."""
        token = os.environ.get("OPENGWAS_JWT", "").strip()
        if not token:
            return None
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Api-Source": "tooluniverse",
        }

    def run(self, arguments):
        try:
            return self._fetch_mr_instruments(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": (
                    f"OpenGWAS request timed out after {self.timeout}s. LD "
                    "clumping is expensive; retry, or set clump=0 / a preclumped "
                    "exposure."
                ),
            }
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            detail = e.response.text[:200] if e.response is not None else ""
            hint = (
                " The OPENGWAS_JWT token is missing/expired/invalid — get a free"
                " one at https://api.opengwas.io."
                if code in (401, 403)
                else ""
            )
            return {
                "status": "error",
                "error": f"OpenGWAS HTTP {code}: {detail}{hint}",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"OpenGWAS request failed: {e}"}
        except Exception as e:  # never raise out of run()
            return {"status": "error", "error": f"Unexpected OpenGWAS error: {e}"}

    def _post(self, path, payload):
        resp = requests.post(
            f"{OPENGWAS_BASE}/{path}",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        # The API returns a JSON array; some deployments wrap it in {"results": [...]}.
        if isinstance(data, dict):
            return data.get("results", [])
        return data if isinstance(data, list) else []

    @staticmethod
    def _norm(record):
        """Pick the standard OpenGWAS association fields off one record."""
        return {
            "rsid": record.get("rsid"),
            "chr": record.get("chr"),
            "position": record.get("position"),
            "ea": (record.get("ea") or "").upper() or None,
            "nea": (record.get("nea") or "").upper() or None,
            "eaf": record.get("eaf"),
            "beta": record.get("beta"),
            "se": record.get("se"),
            "p": record.get("p"),
            "n": record.get("n"),
        }

    @staticmethod
    def _harmonize(exposure, outcome):
        """Align an outcome record to the exposure's effect allele.

        Returns (outcome_beta, outcome_eaf, status) where status is one of
        'aligned' (alleles match), 'flipped' (strand/allele swap, beta negated),
        or 'incompatible' (alleles don't correspond — drop before MR).
        """
        ea, nea = exposure["ea"], exposure["nea"]
        o_ea, o_nea = outcome["ea"], outcome["nea"]
        beta, eaf = outcome["beta"], outcome["eaf"]
        if o_ea == ea and o_nea == nea:
            return beta, eaf, "aligned"
        if o_ea == nea and o_nea == ea:
            flipped_beta = -beta if isinstance(beta, (int, float)) else beta
            flipped_eaf = 1 - eaf if isinstance(eaf, (int, float)) else eaf
            return flipped_beta, flipped_eaf, "flipped"
        return beta, eaf, "incompatible"

    def _fetch_mr_instruments(self, arguments):
        exposure_id = (arguments.get("exposure_id") or "").strip()
        outcome_id = (arguments.get("outcome_id") or "").strip()
        if not exposure_id:
            return {
                "status": "error",
                "error": (
                    "exposure_id is required (an IEU OpenGWAS study ID, e.g. "
                    "'ieu-a-2' for BMI). Use EpiGraphDB_search_opengwas to find IDs."
                ),
            }
        if self._headers() is None:
            return {
                "status": "error",
                "error": (
                    "OpenGWAS requires a free JWT token. Register at "
                    "https://api.opengwas.io and set the OPENGWAS_JWT "
                    "environment variable."
                ),
            }

        pval = float(arguments.get("pval", 5e-8))
        clump = int(arguments.get("clump", 1))

        # Step 1: exposure instruments (genome-wide significant, LD-clumped).
        raw_instruments = self._post(
            "tophits",
            {
                "id": [exposure_id],
                "pval": pval,
                "clump": clump,
                "r2": float(arguments.get("r2", 0.001)),
                "kb": int(arguments.get("kb", 10000)),
                "pop": arguments.get("pop", "EUR"),
            },
        )
        instruments = [self._norm(r) for r in raw_instruments if r.get("rsid")]

        # Shared metadata base for every success envelope below.
        base_metadata = {
            "exposure_id": exposure_id,
            "pval": pval,
            "source": "IEU OpenGWAS",
        }

        if not instruments:
            return {
                "status": "success",
                "data": {"instruments": [], "mr_input": [], "n_instruments": 0},
                "metadata": {
                    **base_metadata,
                    "note": (
                        f"No genome-wide instruments for exposure '{exposure_id}' "
                        f"at p < {pval}. Verify the ID via EpiGraphDB_search_opengwas, "
                        "or relax pval — a weak-instrument MR is unreliable."
                    ),
                },
            }

        # Without an outcome, return the exposure instruments alone.
        if not outcome_id:
            return {
                "status": "success",
                "data": {
                    "instruments": instruments,
                    "mr_input": [],
                    "n_instruments": len(instruments),
                },
                "metadata": {
                    **base_metadata,
                    "note": (
                        "Exposure instruments only — pass outcome_id to get "
                        "harmonized two-sample MR input."
                    ),
                },
            }

        # Step 2: those SNPs' effects in the outcome GWAS, then harmonize.
        rsids = [i["rsid"] for i in instruments]
        raw_outcome = self._post(
            "associations",
            {
                "variant": rsids,
                "id": [outcome_id],
                "proxies": int(arguments.get("proxies", 0)),
            },
        )
        outcome_by_rsid = {
            o["rsid"]: o for o in (self._norm(r) for r in raw_outcome) if o["rsid"]
        }

        mr_input, missing, incompatible = [], 0, 0
        for inst in instruments:
            out = outcome_by_rsid.get(inst["rsid"])
            if out is None:
                missing += 1
                continue
            out_beta, out_eaf, harmon = self._harmonize(inst, out)
            if harmon == "incompatible":
                incompatible += 1
                continue
            mr_input.append(
                {
                    "rsid": inst["rsid"],
                    "ea": inst["ea"],
                    "nea": inst["nea"],
                    "eaf": inst["eaf"],
                    "exposure_beta": inst["beta"],
                    "exposure_se": inst["se"],
                    "exposure_p": inst["p"],
                    "outcome_beta": out_beta,
                    "outcome_se": out["se"],
                    "outcome_p": out["p"],
                    "outcome_eaf": out_eaf,
                    "harmonization": harmon,
                }
            )

        return {
            "status": "success",
            "data": {
                "instruments": instruments,
                "mr_input": mr_input,
                "n_instruments": len(instruments),
                "n_mr_input": len(mr_input),
            },
            "metadata": {
                **base_metadata,
                "outcome_id": outcome_id,
                "n_missing_in_outcome": missing,
                "n_incompatible_alleles": incompatible,
                "description": (
                    "Harmonized two-sample MR input: each row's exposure_beta and "
                    "outcome_beta are aligned to the same effect allele (ea). Feed "
                    "into an IVW/MR-Egger estimator. Palindromic SNPs are not "
                    "strand-resolved here — review before use."
                ),
            },
        }
