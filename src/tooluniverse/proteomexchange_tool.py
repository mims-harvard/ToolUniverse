# proteomexchange_tool.py
"""
ProteomeXchange REST API tool for ToolUniverse.

ProteomeXchange (PX) is a consortium providing a single point of
submission for proteomics data, coordinating PRIDE, MassIVE,
PeptideAtlas, jPOST, and iProX. It provides standardized metadata
for proteomics datasets using controlled vocabulary (CV) terms.

API: https://proteomecentral.proteomexchange.org/cgi/GetDataset
No authentication required. Free for all use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PX_BASE_URL = "https://proteomecentral.proteomexchange.org/cgi"
PROXI_BASE_URL = "https://proteomecentral.proteomexchange.org/api/proxi/v0.1"

# Maximum number of peaks (m/z + intensity pairs) returned per spectrum.
# Spectra can contain thousands of peaks; cap the payload to keep responses
# manageable for downstream agents.
MAX_PEAKS = 200


@register_tool("ProteomeXchangeTool")
class ProteomeXchangeTool(BaseTool):
    """
    Tool for querying ProteomeXchange, the proteomics data consortium.

    Provides access to metadata for proteomics datasets including
    species, instruments, publications, and data files from PRIDE,
    MassIVE, PeptideAtlas, jPOST, and iProX.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_dataset"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ProteomeXchange API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"ProteomeXchange API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to ProteomeXchange API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"ProteomeXchange API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying ProteomeXchange: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "get_dataset":
            return self._get_dataset(arguments)
        elif self.endpoint_type == "search_datasets":
            return self._search_datasets(arguments)
        elif self.endpoint_type == "get_spectrum_by_usi":
            return self._get_spectrum_by_usi(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type: {self.endpoint_type}",
            }

    def _extract_cv_value(self, terms, accession_prefix=None, name_match=None):
        """Extract a value from CV terms list."""
        if not isinstance(terms, list):
            return None
        for term in terms:
            if not isinstance(term, dict):
                continue
            if accession_prefix and term.get("accession", "").startswith(
                accession_prefix
            ):
                return term.get("value", "")
            if name_match and name_match.lower() in term.get("name", "").lower():
                return term.get("value", "")
        return None

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get a ProteomeXchange dataset by PX identifier."""
        px_id = arguments.get("px_id", "")
        if not px_id:
            return {
                "status": "error",
                "error": "px_id parameter is required (e.g., 'PXD000001')",
            }

        url = f"{PX_BASE_URL}/GetDataset"
        params = {"ID": px_id, "outputMode": "JSON"}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # Extract title (API returns plain string, not dict with terms)
        raw_title = raw.get("title", "")
        title = raw_title if isinstance(raw_title, str) else ""

        # Extract species
        species_groups = raw.get("species", [])
        species_list = []
        for group in species_groups:
            if isinstance(group, dict):
                terms = group.get("terms", [])
                sp = self._extract_cv_value(terms, name_match="taxonomy")
                if sp:
                    species_list.append(sp)

        # Extract identifiers (PX ID + partners)
        identifiers = []
        for ident in raw.get("identifiers", []):
            if isinstance(ident, dict):
                val = ident.get("value", "")
                name = ident.get("name", "")
                if val:
                    identifiers.append({"name": name, "value": val})

        # Extract instruments (API returns flat dicts with 'name'+'accession', not 'terms')
        instruments = []
        for inst in raw.get("instruments", []):
            if isinstance(inst, dict):
                inst_name = inst.get("name", "")
                if inst_name and inst_name != "null":
                    instruments.append(inst_name)

        # Extract publications
        publications = []
        for pub in raw.get("publications", []):
            if isinstance(pub, dict):
                terms = pub.get("terms", [])
                pmid = self._extract_cv_value(terms, name_match="PubMed identifier")
                doi = self._extract_cv_value(
                    terms, name_match="Digital Object Identifier"
                )
                publications.append(
                    {
                        "pubmed_id": pmid,
                        "doi": doi,
                    }
                )

        # Extract file count
        data_files = raw.get("datasetFiles", [])

        result = {
            "px_id": px_id,
            "title": title,
            "species": species_list,
            "identifiers": identifiers,
            "instruments": instruments,
            "publications": publications,
            "file_count": len(data_files),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ProteomeXchange",
                "query": px_id,
                "endpoint": "get_dataset",
            },
        }

    def _get_spectrum_by_usi(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a mass spectrum from the PROXI interface by USI.

        A Universal Spectrum Identifier (USI) uniquely references a single
        spectrum/PSM inside a ProteomeXchange dataset. This wraps the PROXI
        v0.1 /spectra endpoint, which returns spectrum-level data (peak lists
        plus CV-term attributes) rather than dataset-level metadata.
        """
        usi = arguments.get("usi", "")
        if not usi or not isinstance(usi, str) or not usi.strip():
            return {
                "status": "error",
                "error": (
                    "usi parameter is required (e.g., 'mzspec:PXD000561:"
                    "Adult_Frontalcortex_bRP_Elite_85_f09:scan:17555:"
                    "VLHPLEGAVVIIFK/2')"
                ),
            }
        usi = usi.strip()

        result_type = arguments.get("resultType") or "full"

        url = f"{PROXI_BASE_URL}/spectra"
        params = {"usi": usi, "resultType": result_type}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # PROXI returns a JSON list of spectrum objects (usually one).
        if isinstance(raw, dict):
            # Error-shaped payloads come back as dicts (e.g. 404/400 detail).
            detail = raw.get("detail") or raw.get("title")
            return {
                "status": "error",
                "error": (
                    f"PROXI returned no spectrum for USI '{usi}'"
                    + (f": {detail}" if detail else "")
                ),
            }
        if not isinstance(raw, list) or len(raw) == 0:
            return {
                "status": "error",
                "error": f"No spectrum found for USI '{usi}'",
            }

        spectrum = raw[0]
        attributes = (
            spectrum.get("attributes", []) if isinstance(spectrum, dict) else []
        )

        # Pull common spectrum attributes by CV accession / name.
        scan_number = self._extract_attribute(
            attributes, accession="MS:1008025", name="scan number"
        )
        charge = self._extract_attribute(
            attributes, accession="MS:1000041", name="charge state"
        )
        precursor_mz = self._extract_attribute(
            attributes, accession="MS:1000744", name="selected ion m/z"
        )
        peptide = self._extract_attribute(
            attributes,
            accession="MS:1000888",
            name="unmodified peptide sequence",
        )

        mzs = spectrum.get("mzs", []) if isinstance(spectrum, dict) else []
        intensities = (
            spectrum.get("intensities", []) if isinstance(spectrum, dict) else []
        )
        if not isinstance(mzs, list):
            mzs = []
        if not isinstance(intensities, list):
            intensities = []

        total_peaks = max(len(mzs), len(intensities))
        # Pair m/z with intensity, capping the payload size.
        peaks = [
            {"mz": mzs[i], "intensity": intensities[i]}
            for i in range(min(len(mzs), len(intensities), MAX_PEAKS))
        ]
        peaks_truncated = total_peaks > len(peaks)

        result = {
            "usi": usi,
            "scan_number": scan_number,
            "charge": charge,
            "precursor_mz": precursor_mz,
            "peptide_sequence": peptide,
            "attributes": [
                {
                    "accession": a.get("accession", ""),
                    "name": a.get("name", ""),
                    "value": a.get("value", ""),
                }
                for a in attributes
                if isinstance(a, dict)
            ],
            "total_peaks": total_peaks,
            "returned_peaks": len(peaks),
            "peaks_truncated": peaks_truncated,
            "peaks": peaks,
        }
        if peaks_truncated:
            result["note"] = (
                f"Peak list truncated to the first {len(peaks)} of {total_peaks} peaks."
            )

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "ProteomeXchange/PROXI",
                "query": usi,
                "result_type": result_type,
                "endpoint": "get_spectrum_by_usi",
            },
        }

    def _extract_attribute(self, attributes, accession=None, name=None):
        """Return the value of a PROXI attribute by CV accession or name."""
        if not isinstance(attributes, list):
            return None
        for attr in attributes:
            if not isinstance(attr, dict):
                continue
            if accession and attr.get("accession") == accession:
                return attr.get("value")
            if name and name.lower() == str(attr.get("name", "")).lower():
                return attr.get("value")
        return None

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search ProteomeXchange datasets via ProteomeCentral API."""
        query = arguments.get("query", "")
        limit = min(arguments.get("limit", 10), 50)

        # Use ProteomeCentral API (same host as _get_dataset, more reliable)
        url = f"{PX_BASE_URL}/GetDataset"
        params = {"outputMode": "JSON"}
        if query:
            params["keyword"] = query

        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        raw = response.json()

        # API returns list of dataset dicts when keyword is given
        if isinstance(raw, list):
            raw_list = raw
        elif isinstance(raw, dict):
            raw_list = raw.get("datasets", [raw])
        else:
            raw_list = []

        import re

        def _strip_html(val):
            """Strip HTML tags from API response values."""
            if isinstance(val, str):
                return re.sub(r"<[^>]+>", "", val).strip()
            return val

        # Client-side keyword filter (API ignores keyword param)
        query_lower = query.lower() if query else ""

        datasets = []
        for ds in raw_list:
            if not isinstance(ds, dict):
                continue
            # ProteomeCentral uses "Dataset Identifier", "Title", "Species" (HTML-wrapped)
            acc = _strip_html(ds.get("Dataset Identifier") or ds.get("identifier", ""))
            title = _strip_html(ds.get("Title") or ds.get("title", ""))
            species = _strip_html(ds.get("Species") or str(ds.get("species", "")))
            contact = _strip_html(ds.get("LabHead") or ds.get("contact", ""))

            # Client-side keyword filtering since API ignores keyword param
            if query_lower and query_lower not in (title + " " + species).lower():
                continue

            datasets.append(
                {
                    "accession": acc,
                    "title": title,
                    "species": species,
                    "contact": contact,
                }
            )
            if len(datasets) >= limit:
                break

        return {
            "status": "success",
            "data": datasets,
            "metadata": {
                "source": "ProteomeXchange/ProteomeCentral",
                "total_returned": len(datasets),
                "query": query or "(all)",
                "endpoint": "search_datasets",
            },
        }
