"""
NEB Tm Calculator API Tool

Provides access to the New England Biolabs (NEB) Tm Calculator API
(https://tmapi.neb.com) for calculating primer melting temperatures (Tm)
and annealing temperatures (Ta) for PCR experiments.

Tm values are calculated using thermodynamic data from SantaLucia (1998)
with the salt correction of Owczarzy et al. (2004). For Phusion DNA
Polymerases, the Schildkraut & Lifson salt correction is used instead.

This tool complements the local DNA_primer_design tool by providing
polymerase-specific Tm calculations with NEB's validated algorithms.
"""

import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("NEBTmTool")
class NEBTmTool(BaseTool):
    """Tool for calculating primer Tm/Ta using the NEB Tm Calculator API."""

    BASE_URL = "https://tmapi.neb.com"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.timeout = 15

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NEB Tm Calculator API request."""
        endpoint = self.tool_config.get("fields", {}).get("endpoint", "")

        if endpoint == "calculate_tm":
            return self._calculate_tm(arguments)
        elif endpoint == "list_products":
            return self._list_products(arguments)
        else:
            return {"status": "error", "error": "Unknown endpoint: {}".format(endpoint)}

    def _calculate_tm(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate Tm for one or two primer sequences."""
        seq1 = arguments.get("primer_sequence", "")
        seq2 = arguments.get("primer_sequence_2")
        prodcode = arguments.get("polymerase", "q5-0")
        conc = arguments.get("primer_concentration", 250)
        monosalt = arguments.get("monovalent_salt_mm")
        fmt = "long"

        # Validate primer sequence
        if not seq1:
            return {"status": "error", "error": "primer_sequence is required"}

        seq1_clean = seq1.strip().upper()
        valid_bases = set("ATCG")
        if not all(c in valid_bases for c in seq1_clean):
            return {
                "status": "error",
                "error": "primer_sequence must contain only A, T, C, G bases",
            }

        if len(seq1_clean) < 10:
            return {
                "status": "error",
                "error": "primer_sequence must be at least 10 bases long",
            }

        # Build request parameters
        params = {
            "seq1": seq1_clean,
            "conc": conc,
            "prodcode": prodcode,
            "fmt": fmt,
        }

        if seq2:
            seq2_clean = seq2.strip().upper()
            if not all(c in valid_bases for c in seq2_clean):
                return {
                    "status": "error",
                    "error": "primer_sequence_2 must contain only A, T, C, G bases",
                }
            params["seq2"] = seq2_clean

        if monosalt is not None and prodcode == "custom":
            params["monosalt"] = monosalt

        url = "{}/tm".format(self.BASE_URL)

        try:
            response = self.session.get(url, params=params, timeout=self.timeout)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "NEB Tm API returned status {}".format(
                        response.status_code
                    ),
                    "detail": response.text[:500],
                }

            api_data = response.json()

            if not api_data.get("success", False):
                return {
                    "status": "error",
                    "error": api_data.get("error", "Unknown NEB API error"),
                }

            raw_data = api_data.get("data", {})

            # Build structured result
            result = {
                "primer_1": {
                    "sequence": seq1_clean,
                    "length": len(seq1_clean),
                    "gc_content": round(
                        (seq1_clean.count("G") + seq1_clean.count("C"))
                        / len(seq1_clean)
                        * 100,
                        1,
                    ),
                },
                "polymerase": prodcode,
                "primer_concentration_nM": conc,
            }

            # Extract primer 1 Tm
            if "p1" in raw_data and raw_data["p1"]:
                p1_info = raw_data["p1"][0]
                result["primer_1"]["tm_celsius"] = round(p1_info.get("tm", 0), 1)
            elif "tm1min" in raw_data:
                result["primer_1"]["tm_celsius"] = raw_data["tm1min"]

            result["primer_1"]["tm_range"] = [
                raw_data.get("tm1min"),
                raw_data.get("tm1max"),
            ]

            # Extract primer 2 Tm if present
            if seq2:
                result["primer_2"] = {
                    "sequence": seq2_clean,
                    "length": len(seq2_clean),
                    "gc_content": round(
                        (seq2_clean.count("G") + seq2_clean.count("C"))
                        / len(seq2_clean)
                        * 100,
                        1,
                    ),
                }
                if "p2" in raw_data and raw_data["p2"]:
                    p2_info = raw_data["p2"][0]
                    result["primer_2"]["tm_celsius"] = round(p2_info.get("tm", 0), 1)
                elif "tm2min" in raw_data:
                    result["primer_2"]["tm_celsius"] = raw_data["tm2min"]

                result["primer_2"]["tm_range"] = [
                    raw_data.get("tm2min"),
                    raw_data.get("tm2max"),
                ]

                # Annealing temperature
                if "ta" in raw_data:
                    result["annealing_temperature_celsius"] = raw_data["ta"]

            # Include NEB notes if available
            if "notes" in raw_data and raw_data["notes"]:
                result["notes"] = raw_data["notes"]

            return {"status": "success", "data": result}

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "NEB Tm API request timed out"}
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "NEB Tm API request failed: {}".format(str(e)),
            }
        except Exception as e:
            return {"status": "error", "error": "Unexpected error: {}".format(str(e))}

    def _list_products(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available NEB polymerase products and their product codes."""
        url = "{}/docs/productcodes".format(self.BASE_URL)

        try:
            response = self.session.get(url, timeout=self.timeout)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "NEB Tm API returned status {}".format(
                        response.status_code
                    ),
                }

            api_data = response.json()

            if not api_data.get("success", False):
                return {
                    "status": "error",
                    "error": api_data.get("error", "Unknown NEB API error"),
                }

            products = api_data.get("data", [])

            # Optional filtering
            filter_text = arguments.get("filter")
            if filter_text:
                filter_lower = filter_text.lower()
                products = [
                    p
                    for p in products
                    if filter_lower in p.get("name", "").lower()
                    or filter_lower in p.get("prodcode", "").lower()
                    or filter_lower in p.get("catalog", "").lower()
                ]

            # Format output
            formatted = []
            for p in products:
                formatted.append(
                    {
                        "prodcode": p.get("prodcode"),
                        "name": p.get("name"),
                        "catalog_number": p.get("catalog"),
                    }
                )

            return {
                "status": "success",
                "data": formatted,
                "count": len(formatted),
            }

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "NEB Tm API request timed out"}
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "NEB Tm API request failed: {}".format(str(e)),
            }
        except Exception as e:
            return {"status": "error", "error": "Unexpected error: {}".format(str(e))}
