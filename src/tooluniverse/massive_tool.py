# massive_tool.py
"""
MassIVE (Mass spectrometry Interactive Virtual Environment) ProXI API tool.

MassIVE is one of the largest proteomics data repositories, hosting thousands
of mass spectrometry datasets. Uses the ProteomeXchange ProXI standard API.

API: https://massive.ucsd.edu/ProteoSAFe/proxi/v0.1/datasets
"""

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

MASSIVE_BASE_URL = "https://massive.ucsd.edu/ProteoSAFe/proxi/v0.1"


@register_tool("MassIVETool")
class MassIVETool(BaseTool):
    """
    Tool for querying MassIVE proteomics repository via ProXI API.

    Supports searching datasets and retrieving dataset details.
    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.operation = tool_config.get("fields", {}).get(
            "operation", "search_datasets"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the MassIVE API call."""
        op = self.operation
        if op == "search_datasets":
            return self._search_datasets(arguments)
        if op == "get_dataset":
            return self._get_dataset(arguments)
        return {"status": "error", "error": f"Unknown operation: {op}"}

    def _extract_all_cv_values(self, cv_list):
        """Extract all name-value pairs from a CV-param list."""
        results = []
        if not cv_list:
            return results
        items = cv_list
        if items and isinstance(items[0], list):
            items = items[0]
        for item in items:
            if isinstance(item, dict):
                name = item.get("name", "")
                value = item.get("value", "")
                if name:
                    results.append({"name": name, "value": value})
        return results

    def _parse_cv_groups(self, groups: List) -> List[Dict[str, str]]:
        """Parse a list of CV-param groups into a list of name->value dicts."""
        result = []
        for group in groups:
            entries = self._extract_all_cv_values(
                group if isinstance(group, list) else [group]
            )
            d = {e["name"]: e["value"] for e in entries}
            if d:
                result.append(d)
        return result

    def _parse_dataset(self, raw):
        """Parse a raw ProXI dataset into a cleaner format."""
        accessions = []
        for a in raw.get("accession", []):
            if isinstance(a, dict) and a.get("value"):
                accessions.append(a["value"])

        species_list = []
        for sp in raw.get("species", []):
            vals = self._extract_all_cv_values(sp if isinstance(sp, list) else [sp])
            for v in vals:
                if v.get("value") and v["value"] != "null":
                    species_list.append(v["value"])

        instruments = []
        for inst in raw.get("instruments", []):
            if isinstance(inst, dict):
                name = inst.get("name", inst.get("value", ""))
                if name and name != "null":
                    instruments.append(name)

        keywords = []
        for kw in raw.get("keywords", []):
            if isinstance(kw, dict) and kw.get("value"):
                keywords.append(kw["value"])

        return {
            "accessions": accessions,
            "title": raw.get("title", ""),
            "summary": raw.get("summary", ""),
            "species": species_list,
            "instruments": instruments,
            "keywords": keywords,
        }

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search MassIVE datasets."""
        page_size = arguments.get("page_size", 10)
        species = arguments.get("species")

        params = {
            "resultType": "compact",
            "pageSize": min(int(page_size), 100),
        }
        if species:
            params["species"] = species

        try:
            resp = requests.get(
                f"{MASSIVE_BASE_URL}/datasets",
                params=params,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MassIVE API error: {e}"}
        except ValueError:
            return {"status": "error", "error": "Invalid JSON response from MassIVE"}

        if not isinstance(data, list):
            return {
                "status": "error",
                "error": f"Unexpected response type: {type(data).__name__}",
            }

        datasets = [self._parse_dataset(item) for item in data]
        return {"status": "success", "data": datasets}

    def _get_dataset(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details for a specific MassIVE dataset."""
        accession = arguments.get("accession", "")
        if not accession:
            return {"status": "error", "error": "accession parameter is required"}

        try:
            resp = requests.get(
                f"{MASSIVE_BASE_URL}/datasets/{accession}",
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MassIVE API error: {e}"}
        except ValueError:
            return {"status": "error", "error": "Invalid JSON response from MassIVE"}

        result = self._parse_dataset(data)

        # Add extra fields available in detail view
        result["contacts"] = self._parse_cv_groups(data.get("contacts", []))
        result["publications"] = self._parse_cv_groups(data.get("publications", []))

        modifications = []
        for mod in data.get("modifications", []):
            if isinstance(mod, dict) and mod.get("name"):
                modifications.append(mod["name"])
        result["modifications"] = modifications

        return {"status": "success", "data": result}
