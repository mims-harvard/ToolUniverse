"""
IDT OligoAnalyzer API Tool

Provides access to IDT (Integrated DNA Technologies) OligoAnalyzer web API
for calculating oligonucleotide thermodynamic properties including melting
temperature (Tm), GC content, molecular weight, extinction coefficient,
and self-dimer (homodimer) analysis with delta-G predictions.

API base URL: https://www.idtdna.com/calc/analyzer/home/

This tool complements:
- NEB_Tm_calculate: polymerase-specific Tm with salt corrections
- DNA_calculate_gc_content: local GC calculation without Tm
- DNA_reverse_complement: sequence manipulation before analysis

IDT OligoAnalyzer uses nearest-neighbor thermodynamic parameters and
provides comprehensive oligo characterization for primer/probe design QC.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("IDTTool")
class IDTTool(BaseTool):
    """Tool for oligo thermodynamic analysis using the IDT OligoAnalyzer API."""

    BASE_URL = "https://www.idtdna.com/calc/analyzer/home"

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Content-Type": "application/json",
            }
        )
        self.timeout = 15

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the IDT OligoAnalyzer API request."""
        endpoint = self.tool_config.get("fields", {}).get("endpoint", "")

        if endpoint == "analyze":
            return self._analyze_oligo(arguments)
        elif endpoint == "selfdimer":
            return self._check_self_dimer(arguments)
        else:
            return {"status": "error", "error": "Unknown endpoint: {}".format(endpoint)}

    def _validate_sequence(self, seq, param_name="sequence"):
        """Validate an oligonucleotide sequence. Returns (cleaned_seq, error_dict_or_None)."""
        if not seq or not seq.strip():
            return None, {
                "status": "error",
                "error": "{} is required".format(param_name),
            }

        cleaned = seq.strip().upper()

        # Allow DNA and RNA bases, plus common modifications
        valid_bases = set("ATCGU")
        invalid = set(cleaned) - valid_bases
        if invalid:
            return None, {
                "status": "error",
                "error": "{} contains invalid characters: {}. Only A, T, C, G, U are allowed.".format(
                    param_name, ", ".join(sorted(invalid))
                ),
            }

        if len(cleaned) < 5:
            return None, {
                "status": "error",
                "error": "{} must be at least 5 bases long".format(param_name),
            }

        if len(cleaned) > 200:
            return None, {
                "status": "error",
                "error": "{} must be at most 200 bases long".format(param_name),
            }

        return cleaned, None

    def _analyze_oligo(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze an oligonucleotide: Tm, GC%, MW, extinction coefficient."""
        seq = arguments.get("sequence", "")
        na_conc = arguments.get("na_concentration_mm", 50)
        mg_conc = arguments.get("mg_concentration_mm", 0)
        dntps_conc = arguments.get("dntps_concentration_mm", 0)
        oligo_conc = arguments.get("oligo_concentration_um", 0.25)
        oligo_type = arguments.get("oligo_type", "DNA")

        cleaned, err = self._validate_sequence(seq)
        if err:
            return err

        payload = {
            "Sequence": cleaned,
            "NaConc": na_conc,
            "MgConc": mg_conc,
            "dNTPsConc": dntps_conc,
            "OligoConc": oligo_conc,
            "OligoType": oligo_type,
        }

        url = "{}/analyze".format(self.BASE_URL)

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "IDT API returned status {}".format(response.status_code),
                    "detail": response.text[:500],
                }

            api_data = response.json()

            if api_data.get("HasErrors"):
                errors = api_data.get("Errors", [])
                return {
                    "status": "error",
                    "error": "IDT analysis error: {}".format(
                        "; ".join(str(e) for e in errors) if errors else "Unknown error"
                    ),
                }

            result = {
                "sequence": api_data.get("Sequence", "").replace(" ", ""),
                "complement": api_data.get("Complement", "").replace(" ", ""),
                "length": api_data.get("Length"),
                "base_count": api_data.get("BaseCount"),
                "gc_content_percent": api_data.get("GCContent"),
                "melting_temperature_celsius": api_data.get("MeltTemp"),
                "molecular_weight_daltons": api_data.get("MolecularWeight"),
                "extinction_coefficient": api_data.get("ExtCoefficient"),
                "nmole_per_od260": api_data.get("NmoleOD"),
                "ug_per_od260": api_data.get("UgOD"),
                "oligo_type": oligo_type,
                "conditions": {
                    "na_concentration_mm": na_conc,
                    "mg_concentration_mm": mg_conc,
                    "dntps_concentration_mm": dntps_conc,
                    "oligo_concentration_um": oligo_conc,
                },
            }

            return {"status": "success", "data": result}

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IDT API request timed out"}
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "IDT API request failed: {}".format(str(e)),
            }
        except Exception as e:
            return {"status": "error", "error": "Unexpected error: {}".format(str(e))}

    def _check_self_dimer(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check for self-complementarity and homodimer formation."""
        seq = arguments.get("sequence", "")
        na_conc = arguments.get("na_concentration_mm", 50)
        mg_conc = arguments.get("mg_concentration_mm", 0)
        temp = arguments.get("temperature_celsius", 25)

        cleaned, err = self._validate_sequence(seq)
        if err:
            return err

        payload = {
            "Sequence": cleaned,
            "NaConc": na_conc,
            "MgConc": mg_conc,
            "Temp": temp,
        }

        url = "{}/selfdimer".format(self.BASE_URL)

        try:
            response = self.session.post(url, json=payload, timeout=self.timeout)

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "IDT API returned status {}".format(response.status_code),
                    "detail": response.text[:500],
                }

            api_data = response.json()

            # Extract and format dimer results
            raw_results = api_data.get("Results", [])
            dimers = []
            for r in raw_results:
                dimers.append(
                    {
                        "delta_g_kcal_per_mol": r.get("DeltaG"),
                        "base_pairs": r.get("BasePairs"),
                        "alignment": r.get("Dimer"),
                    }
                )

            # The most stable (most negative delta G) dimer is the worst case
            worst_delta_g = api_data.get("MaxDeltaG")

            result = {
                "sequence": api_data.get("PrimarySequence", cleaned),
                "num_dimers_found": len(dimers),
                "worst_delta_g_kcal_per_mol": worst_delta_g,
                "self_dimer_risk": _assess_dimer_risk(worst_delta_g),
                "dimers": dimers[:5],  # Return top 5 most stable dimers
                "conditions": {
                    "na_concentration_mm": na_conc,
                    "mg_concentration_mm": mg_conc,
                    "temperature_celsius": temp,
                },
            }

            return {"status": "success", "data": result}

        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IDT API request timed out"}
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": "IDT API request failed: {}".format(str(e)),
            }
        except Exception as e:
            return {"status": "error", "error": "Unexpected error: {}".format(str(e))}


def _assess_dimer_risk(delta_g):
    """Assess self-dimer risk based on delta G value.

    Guidelines from IDT:
    - deltaG > -3.0: Low risk (acceptable)
    - -3.0 >= deltaG > -6.0: Moderate risk (may affect some applications)
    - deltaG <= -6.0: High risk (likely to form stable dimers)
    """
    if delta_g is None:
        return "unknown"
    if delta_g > -3.0:
        return "low"
    elif delta_g > -6.0:
        return "moderate"
    else:
        return "high"
