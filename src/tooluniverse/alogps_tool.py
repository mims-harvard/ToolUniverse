"""ALOGPS 2.1 lipophilicity and aqueous solubility prediction tool for ToolUniverse.

ALOGPS 2.1 (VCCLAB / Virtual Computational Chemistry Laboratory) is a free,
no-key public web service that predicts two key physicochemical properties of a
small molecule directly from its SMILES string using associative neural networks
(ASNN) trained on experimental data:

- logP : octanol/water partition coefficient (lipophilicity)
- logS : decimal logarithm of aqueous solubility in mol/L (water solubility)

The ALOGPS algorithm (Tetko et al.) is a widely cited reference method and
provides an independent, second-opinion estimate that complements RDKit
descriptors and SwissADME/ADMET-AI predictions.

API: https://vcclab.org/web/alogps/calc?SMILES=<smiles>
No authentication required. Free public access. One molecule per request.
"""

import re
import requests
from typing import Dict, Any, List

from .base_tool import BaseTool
from .tool_registry import register_tool

ALOGPS_URL = "https://vcclab.org/web/alogps/calc"

# A successful response looks like:
#   <HTML><body>mol_N logP logS SMILES<br>mol_1 1.43 -2.09 CC(=O)... <br></body></HTML>
# The data row begins with "mol_1 " followed by logP, logS, and the echoed SMILES.
_DATA_ROW_RE = re.compile(
    r"mol_1\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)\s+(\S.*?)\s*(?:<br>|$)"
)
# Error markers returned by the service for unparseable input.
_ERROR_MARKERS = (
    "could not be analysed",
    "<html>error</html>",
)

# Cap batch size to keep total runtime under the 30s tool budget.
_MAX_BATCH = 10


@register_tool("ALOGPSTool")
class ALOGPSTool(BaseTool):
    """
    Predict logP (lipophilicity) and logS (aqueous solubility) from SMILES
    using the ALOGPS 2.1 associative-neural-network model.

    Accepts a single SMILES string (``smiles``) or a list of SMILES strings
    (``smiles_list``, up to 10). Returns the predicted logP (octanol/water
    partition coefficient) and logS (log10 of aqueous solubility in mol/L) for
    each molecule.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        smiles = arguments.get("smiles")
        smiles_list = arguments.get("smiles_list")

        # Normalize inputs into a single list of cleaned SMILES strings.
        if smiles_list is not None:
            if not isinstance(smiles_list, list):
                return {
                    "status": "error",
                    "error": "smiles_list must be a list of SMILES strings",
                    "retryable": False,
                }
            queries = [str(s).strip() for s in smiles_list if str(s).strip()]
        elif smiles is not None and str(smiles).strip():
            queries = [str(smiles).strip()]
        else:
            return {
                "status": "error",
                "error": "Provide a SMILES string via 'smiles' or a list via 'smiles_list'",
                "retryable": False,
            }

        if not queries:
            return {
                "status": "error",
                "error": "No valid SMILES provided",
                "retryable": False,
            }

        if len(queries) > _MAX_BATCH:
            return {
                "status": "error",
                "error": f"Too many SMILES (max {_MAX_BATCH} per call); received {len(queries)}",
                "retryable": False,
            }

        results: List[Dict[str, Any]] = [self._predict_one(query) for query in queries]

        # If every molecule failed, surface an error so callers don't treat
        # an all-failed batch as a success.
        if all(r.get("error") is not None for r in results):
            first_error = results[0].get("error") if results else "prediction failed"
            return {
                "status": "error",
                "error": first_error,
                "retryable": False,
            }

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "source": "ALOGPS 2.1 (VCCLAB Virtual Computational Chemistry Laboratory)",
                "method": "Associative Neural Networks (ASNN)",
                "count": len(results),
                "logP_definition": "octanol/water partition coefficient (lipophilicity)",
                "logS_definition": "log10 of aqueous solubility in mol/L",
            },
        }

    def _predict_one(self, smiles: str) -> Dict[str, Any]:
        """Query ALOGPS for a single SMILES and parse the response."""
        try:
            resp = requests.get(
                ALOGPS_URL,
                params={"SMILES": smiles},
                timeout=self.timeout,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            return self._row(smiles, error="ALOGPS request timed out")
        except requests.exceptions.ConnectionError:
            return self._row(smiles, error="Failed to connect to ALOGPS service")
        except requests.exceptions.HTTPError as exc:
            code = exc.response.status_code if exc.response is not None else "unknown"
            return self._row(smiles, error=f"ALOGPS HTTP {code}")
        except Exception as exc:  # noqa: BLE001 - never raise out of run()
            return self._row(smiles, error=f"ALOGPS error: {exc}")

        text = resp.text or ""
        lowered = text.lower()
        if any(marker in lowered for marker in _ERROR_MARKERS):
            return self._row(
                smiles,
                error="ALOGPS could not parse this SMILES (invalid or unsupported structure)",
            )

        match = _DATA_ROW_RE.search(text)
        if not match:
            return self._row(
                smiles,
                error="ALOGPS returned an unexpected response format",
            )

        logp = float(match.group(1))
        logs = float(match.group(2))
        return self._row(smiles, logp=logp, logs=logs)

    @staticmethod
    def _row(smiles, logp=None, logs=None, error=None) -> Dict[str, Any]:
        return {
            "smiles": smiles,
            "logP": logp,
            "logS": logs,
            "error": error,
        }
