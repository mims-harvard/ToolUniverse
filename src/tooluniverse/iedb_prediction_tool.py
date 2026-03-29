"""
IEDB Prediction Tool - MHC-I and MHC-II Binding Prediction

Provides access to the IEDB Analysis Resource tools API for predicting
peptide binding to MHC class I and class II molecules.

API: https://tools-cluster-interface.iedb.org/tools_api/
No authentication required.

Methods: NetMHCpan EL (recommended), NetMHCpan BA, SMM, ANN
"""

import requests
import csv
import io
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool


IEDB_TOOLS_BASE = "https://tools-cluster-interface.iedb.org/tools_api"


@register_tool("IEDBPredictionTool")
class IEDBPredictionTool(BaseTool):
    """
    Tool for predicting peptide-MHC binding using IEDB Analysis Resource.

    Supported operations:
    - predict_mhci: Predict MHC class I binding (CD8+ T cell epitopes)
    - predict_mhcii: Predict MHC class II binding (CD4+ T cell epitopes)
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 120  # predictions can be slow
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "predict_mhci"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if self.endpoint_type == "predict_mhci":
                return self._predict_mhci(arguments)
            elif self.endpoint_type == "predict_mhcii":
                return self._predict_mhcii(arguments)
            return {
                "status": "error",
                "error": f"Unknown endpoint: {self.endpoint_type}",
            }
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IEDB prediction timed out (max 120s)"}
        except Exception as e:
            return {"status": "error", "error": f"IEDB prediction error: {str(e)}"}

    def _parse_tsv(self, text: str) -> List[Dict[str, str]]:
        reader = csv.DictReader(io.StringIO(text.strip()), delimiter="\t")
        return [dict(row) for row in reader]

    def _predict_mhci(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        sequence = arguments.get("sequence", "")
        allele = arguments.get("allele", "HLA-A*02:01")
        method = arguments.get("method", "netmhcpan_el")
        length = arguments.get("length", 9)

        if not sequence:
            return {"status": "error", "error": "sequence is required"}

        data = {
            "method": method,
            "sequence_text": sequence,
            "allele": allele,
            "length": str(length),
        }

        resp = requests.post(
            f"{IEDB_TOOLS_BASE}/mhci/",
            data=data,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        results = self._parse_tsv(resp.text)

        # Sort by score (descending for EL, ascending for BA)
        for r in results:
            try:
                r["score"] = float(r.get("score", 0))
                r["percentile_rank"] = float(r.get("percentile_rank", 100))
            except (ValueError, TypeError):
                pass

        results.sort(key=lambda x: x.get("percentile_rank", 100))

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "method": method,
                "allele": allele,
                "length": length,
                "n_peptides": len(results),
                "source": "IEDB Analysis Resource",
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

        data = {
            "method": method,
            "sequence_text": sequence,
            "allele": allele,
        }

        resp = requests.post(
            f"{IEDB_TOOLS_BASE}/mhcii/",
            data=data,
            timeout=self.timeout,
        )
        resp.raise_for_status()

        results = self._parse_tsv(resp.text)
        for r in results:
            try:
                r["percentile_rank"] = float(r.get("percentile_rank", 100))
            except (ValueError, TypeError):
                pass

        results.sort(key=lambda x: x.get("percentile_rank", 100))

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "method": method,
                "allele": allele,
                "n_peptides": len(results),
                "source": "IEDB Analysis Resource",
            },
        }
