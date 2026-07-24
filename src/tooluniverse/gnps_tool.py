# gnps_tool.py
"""
GNPS Metabolomics USI REST API tool for ToolUniverse.

GNPS (Global Natural Products Social Molecular Networking) provides
mass spectrometry spectral library data through the Universal Spectrum
Identifier (USI) system. The Metabolomics USI resolver provides
programmatic access to reference MS/MS spectra for compound identification.

API: https://metabolomics-usi.gnps2.org
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GNPS_USI_BASE_URL = "https://metabolomics-usi.gnps2.org"
GNPS_SPECTRUM_URL = "https://external.gnps2.org/gnpsspectrum"
GNPS_NPCLASSIFIER_URL = "https://npclassifier.gnps2.org/classify"


@register_tool("GNPSTool")
class GNPSTool(BaseTool):
    """
    Tool for querying GNPS mass spectrometry spectral data.

    Provides access to reference MS/MS spectra through Universal Spectrum
    Identifiers (USIs) for metabolomics compound identification.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_spectrum"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GNPS API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GNPS API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GNPS API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"GNPS API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying GNPS: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "get_spectrum":
            return self._get_spectrum(arguments)
        elif self.endpoint_type == "compare_spectra":
            return self._compare_spectra(arguments)
        elif self.endpoint_type == "get_library_record":
            return self._get_library_record(arguments)
        elif self.endpoint_type == "npclassifier":
            return self._npclassifier(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _get_spectrum(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get MS/MS spectrum by Universal Spectrum Identifier (USI)."""
        usi = arguments.get("usi", "")
        if not usi:
            return {
                "status": "error",
                "error": "usi parameter is required (e.g., 'mzspec:GNPS:GNPS-LIBRARY:accession:CCMSLIB00005435737')",
            }

        params = {"usi1": usi}
        response = requests.get(
            f"{GNPS_USI_BASE_URL}/json/",
            params=params,
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        if "error" in raw:
            return {
                "status": "error",
                "error": f"GNPS USI error: {raw['error'].get('message', str(raw['error']))}",
            }

        # Process peaks - summarize to avoid huge responses
        peaks = raw.get("peaks", [])
        n_peaks = raw.get("n_peaks", len(peaks))

        # Get top peaks by intensity
        if peaks:
            sorted_peaks = sorted(
                peaks, key=lambda p: p[1] if len(p) > 1 else 0, reverse=True
            )
            top_peaks = [
                {"mz": round(p[0], 4), "intensity": round(p[1], 1)}
                for p in sorted_peaks[:20]
            ]
            mz_range = [
                round(min(p[0] for p in peaks), 2),
                round(max(p[0] for p in peaks), 2),
            ]
        else:
            top_peaks = []
            mz_range = []

        result = {
            "usi": usi,
            "precursor_mz": raw.get("precursor_mz"),
            "precursor_charge": raw.get("precursor_charge"),
            "n_peaks": n_peaks,
            "mz_range": mz_range,
            "top_20_peaks": top_peaks,
            "spectrum_id": raw.get("spectrum_id"),
            "splash": raw.get("splash"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GNPS Metabolomics USI",
                "query": usi,
                "endpoint": "get_spectrum",
            },
        }

    def _compare_spectra(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Compare two spectra using USI mirror plot endpoint."""
        usi1 = arguments.get("usi1", "")
        usi2 = arguments.get("usi2", "")
        if not usi1 or not usi2:
            return {
                "status": "error",
                "error": "Both usi1 and usi2 parameters are required",
            }

        # Fetch both spectra
        params1 = {"usi1": usi1}
        response1 = requests.get(
            f"{GNPS_USI_BASE_URL}/json/",
            params=params1,
            timeout=self.timeout,
        )
        response1.raise_for_status()
        spec1 = response1.json()

        params2 = {"usi1": usi2}
        response2 = requests.get(
            f"{GNPS_USI_BASE_URL}/json/",
            params=params2,
            timeout=self.timeout,
        )
        response2.raise_for_status()
        spec2 = response2.json()

        for s, name in [(spec1, "usi1"), (spec2, "usi2")]:
            if "error" in s:
                return {
                    "status": "error",
                    "error": f"GNPS USI error for {name}: {s['error'].get('message', str(s['error']))}",
                }

        result = {
            "spectrum_1": {
                "usi": usi1,
                "precursor_mz": spec1.get("precursor_mz"),
                "n_peaks": spec1.get("n_peaks"),
            },
            "spectrum_2": {
                "usi": usi2,
                "precursor_mz": spec2.get("precursor_mz"),
                "n_peaks": spec2.get("n_peaks"),
            },
            "mirror_plot_url": f"{GNPS_USI_BASE_URL}/mirror/?usi1={usi1}&usi2={usi2}",
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GNPS Metabolomics USI",
                "endpoint": "compare_spectra",
            },
        }

    def _get_library_record(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a full GNPS library reference record by SpectrumID/CCMSLIB accession."""
        spectrum_id = (
            arguments.get("spectrum_id")
            or arguments.get("SpectrumID")
            or arguments.get("accession")
            or ""
        )
        if not spectrum_id:
            return {
                "status": "error",
                "error": "spectrum_id parameter is required (e.g., 'CCMSLIB00005435737')",
            }

        response = requests.get(
            GNPS_SPECTRUM_URL,
            params={"SpectrumID": spectrum_id},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        annotations = raw.get("annotations") or []
        if not annotations:
            return {
                "status": "error",
                "error": f"No GNPS library record found for SpectrumID '{spectrum_id}'",
            }

        ann = annotations[0]
        spectrum_info = raw.get("spectruminfo") or {}
        record = {
            "spectrum_id": ann.get("SpectrumID") or spectrum_id,
            "compound_name": ann.get("Compound_Name"),
            "adduct": ann.get("Adduct"),
            "smiles": ann.get("Smiles"),
            "inchi": ann.get("INCHI"),
            "inchi_key": ann.get("INCHI_AUX"),
            "ion_source": ann.get("Ion_Source"),
            "instrument": ann.get("Instrument"),
            "ion_mode": ann.get("Ion_Mode"),
            "precursor_mz": ann.get("Precursor_MZ"),
            "charge": ann.get("Charge"),
            "compound_source": ann.get("Compound_Source"),
            "pi": ann.get("PI"),
            "data_collector": ann.get("Data_Collector"),
            "cas_number": ann.get("CAS_Number"),
            "pubmed_id": ann.get("Pubmed_ID"),
            "library_membership": spectrum_info.get("library_membership"),
            "ms_level": spectrum_info.get("ms_level"),
            "annotations": annotations,
        }

        return {
            "status": "success",
            "data": record,
            "metadata": {
                "source": "GNPS Library (gnps2)",
                "query": spectrum_id,
                "endpoint": "get_library_record",
            },
        }

    def _npclassifier(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """NP Classifier: de novo natural-product biosynthetic classification from SMILES."""
        smiles = arguments.get("smiles") or arguments.get("SMILES") or ""
        if not smiles:
            return {
                "status": "error",
                "error": "smiles parameter is required (e.g., 'CN1C=NC2=C1C(=O)N(C)C(=O)N2C' for caffeine)",
            }

        response = requests.get(
            GNPS_NPCLASSIFIER_URL,
            params={"smiles": smiles},
            timeout=self.timeout,
        )
        response.raise_for_status()
        raw = response.json()

        # NP Classifier returns empty result lists for SMILES it cannot classify.
        class_results = raw.get("class_results") or []
        superclass_results = raw.get("superclass_results") or []
        pathway_results = raw.get("pathway_results") or []
        if not (class_results or superclass_results or pathway_results):
            return {
                "status": "error",
                "error": f"NP Classifier returned no classification for SMILES '{smiles}'. The structure may be invalid or out of scope for natural-product classification.",
            }

        record = {
            "smiles": smiles,
            "class": class_results,
            "superclass": superclass_results,
            "pathway": pathway_results,
            "is_glycoside": raw.get("isglycoside"),
        }

        return {
            "status": "success",
            "data": record,
            "metadata": {
                "source": "NP Classifier (gnps2)",
                "query": smiles,
                "endpoint": "npclassifier",
            },
        }
