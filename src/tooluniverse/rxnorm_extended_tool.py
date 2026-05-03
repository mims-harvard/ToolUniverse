"""
RxNorm Extended Tool

Extends the basic RxNorm drug name tool with additional endpoints from the
U.S. National Library of Medicine (NLM) RxNorm API:

  - rxnorm_get_drug_info    : comprehensive properties for a drug by name or RXCUI
  - rxnorm_get_related_drugs: branded and generic products for an ingredient RXCUI
  - rxnorm_find_rxcui       : resolve a drug name to its RXCUI(s)

API base: https://rxnav.nlm.nih.gov/REST
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

RXNORM_BASE = "https://rxnav.nlm.nih.gov/REST"

# Term-type (tty) labels used in RxNorm
TTY_LABELS = {
    "IN": "Ingredient (generic)",
    "PIN": "Precise Ingredient",
    "BN": "Brand Name",
    "SCD": "Semantic Clinical Drug (generic product)",
    "SBD": "Semantic Branded Drug",
    "GPCK": "Generic Pack",
    "BPCK": "Branded Pack",
    "SCDF": "Semantic Clinical Drug Form",
    "SBDF": "Semantic Branded Drug Form",
    "SCDC": "Semantic Drug Component",
    "MIN": "Multiple Ingredients",
    "DF": "Dose Form",
}


@register_tool("RxNormExtendedTool")
class RxNormExtendedTool(BaseTool):
    """
    Extended RxNorm tools for drug information retrieval.

    Supports three operations:
      - find_rxcui:      Resolve a drug name to its RXCUI identifier(s)
      - get_drug_info:   Fetch full properties (name, TTY, synonym) by RXCUI or name
      - get_related_drugs: List all branded and generic clinical drug products
                          that share an active ingredient
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get("operation", "find_rxcui")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        op = self.operation
        if op == "find_rxcui":
            return self._find_rxcui(arguments)
        elif op == "get_drug_info":
            return self._get_drug_info(arguments)
        elif op == "get_related_drugs":
            return self._get_related_drugs(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _resolve_rxcui(self, arguments: Dict[str, Any]):
        """Return (rxcui_str, error_dict_or_None)."""
        rxcui = arguments.get("rxcui")
        drug_name = arguments.get("drug_name") or arguments.get("name")

        if rxcui:
            return str(rxcui).strip(), None

        if drug_name:
            url = f"{RXNORM_BASE}/rxcui.json"
            try:
                resp = requests.get(
                    url, params={"name": drug_name.strip()}, timeout=self.timeout
                )
                resp.raise_for_status()
                ids = resp.json().get("idGroup", {}).get("rxnormId", [])
                if not ids:
                    return None, {
                        "status": "error",
                        "error": f"No RXCUI found for drug name: {drug_name!r}",
                    }
                return str(ids[0]), None
            except requests.exceptions.RequestException as e:
                return None, {
                    "status": "error",
                    "error": f"RxNorm API request failed: {e}",
                }

        return None, {
            "status": "error",
            "error": "Provide either 'rxcui' or 'drug_name'.",
        }

    # ------------------------------------------------------------------
    # operations
    # ------------------------------------------------------------------

    def _find_rxcui(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a drug name to one or more RXCUIs."""
        drug_name = arguments.get("drug_name") or arguments.get("name")
        if not drug_name or not str(drug_name).strip():
            return {"status": "error", "error": "drug_name is required"}

        url = f"{RXNORM_BASE}/rxcui.json"
        try:
            resp = requests.get(
                url,
                params={"name": drug_name.strip(), "search": 2},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"RxNorm API request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse response: {e}"}

        rxcuis = data.get("idGroup", {}).get("rxnormId", [])
        if not rxcuis:
            return {
                "status": "success",
                "data": {"drug_name": drug_name, "rxcuis": [], "found": False},
                "metadata": {
                    "note": "No RXCUI found. Try a simpler drug name (generic, no dosage)."
                },
            }

        return {
            "status": "success",
            "data": {
                "drug_name": drug_name,
                "rxcuis": rxcuis,
                "primary_rxcui": rxcuis[0],
                "found": True,
            },
            "metadata": {"source": "NLM RxNorm API"},
        }

    def _get_drug_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch comprehensive drug properties by RXCUI or drug name."""
        rxcui, err = self._resolve_rxcui(arguments)
        if err:
            return err

        url = f"{RXNORM_BASE}/rxcui/{rxcui}/properties.json"
        try:
            resp = requests.get(url, timeout=self.timeout)
            resp.raise_for_status()
            props = resp.json().get("properties", {})
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"RxNorm API request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse response: {e}"}

        if not props:
            return {
                "status": "error",
                "error": f"No properties found for RXCUI {rxcui}",
            }

        tty = props.get("tty", "")
        tty_label = TTY_LABELS.get(tty, tty)

        return {
            "status": "success",
            "data": {
                "rxcui": props.get("rxcui", rxcui),
                "name": props.get("name"),
                "synonym": props.get("synonym") or None,
                "term_type": tty,
                "term_type_label": tty_label,
                "language": props.get("language"),
            },
            "metadata": {"source": "NLM RxNorm API"},
        }

    def _get_related_drugs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List branded and generic products for an ingredient RXCUI (or name)."""
        rxcui, err = self._resolve_rxcui(arguments)
        if err:
            return err

        # tty param: IN=ingredient, BN=brand name, SBD=branded drug, SCD=generic drug
        # RxNorm expects space-separated values; convert + to space so requests doesn't encode + as %2B
        tty_raw = arguments.get("tty", "IN+BN+SBD+SCD")
        tty_param = tty_raw.replace("+", " ")
        url = f"{RXNORM_BASE}/rxcui/{rxcui}/related.json"
        try:
            resp = requests.get(url, params={"tty": tty_param}, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"RxNorm API request failed: {e}"}
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse response: {e}"}

        concept_groups = data.get("relatedGroup", {}).get("conceptGroup", []) or []
        grouped: Dict[str, list] = {}
        for group in concept_groups:
            tty = group.get("tty", "unknown")
            label = TTY_LABELS.get(tty, tty)
            props = group.get("conceptProperties") or []
            if not isinstance(props, list):
                props = [props]
            entries = [
                {
                    "rxcui": p.get("rxcui"),
                    "name": p.get("name"),
                    "synonym": p.get("synonym") or None,
                }
                for p in props
                if isinstance(p, dict)
            ]
            if entries:
                grouped[label] = entries

        total = sum(len(v) for v in grouped.values())
        return {
            "status": "success",
            "data": {
                "rxcui": rxcui,
                "related_drugs": grouped,
                "total_related": total,
            },
            "metadata": {
                "source": "NLM RxNorm API",
                "tty_filter": tty_param,
                "tty_key": {v: k for k, v in TTY_LABELS.items()},
            },
        }
