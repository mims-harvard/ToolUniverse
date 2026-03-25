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
