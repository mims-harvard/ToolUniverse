"""
NHANES Tool

Provides information about NHANES (National Health and Nutrition Examination Survey) datasets.

Note: NHANES data is typically available as downloadable files (SAS, XPT formats)
rather than REST APIs. This tool provides information and links to access the data.
"""

from typing import Dict, Any, Optional
from .base_tool import BaseTool
from .tool_registry import register_tool


@register_tool("NHANESTool")
class NHANESTool(BaseTool):
    """NHANES data information tool."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = tool_config["fields"]["endpoint"]

    def _get_dataset_info(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get NHANES dataset information."""
        year = arguments.get("year")
        component = arguments.get("component")

        base_url = "https://wwwn.cdc.gov/Nchs/Nhanes"

        # Common NHANES cycles
        cycles = [
            "2017-2018",
            "2015-2016",
            "2013-2014",
            "2011-2012",
            "2009-2010",
            "2007-2008",
        ]

        datasets = []

        if year:
            cycles_to_show = [year] if year in cycles else cycles[:2]
        else:
            cycles_to_show = cycles[:2]  # Show most recent

        for cycle in cycles_to_show:
            if component:
                datasets.append(
                    {
                        "name": f"NHANES {component} - {cycle}",
                        "year": cycle,
                        "component": component,
                        "download_url": f"{base_url}/{cycle}/{component.lower()}_{cycle}.aspx",
                        "description": f"NHANES {component} data for {cycle}",
                    }
                )
            else:
                # Show all components
                for comp in [
                    "Demographics",
                    "Dietary",
                    "Examination",
                    "Laboratory",
                    "Questionnaire",
                ]:
                    datasets.append(
                        {
                            "name": f"NHANES {comp} - {cycle}",
                            "year": cycle,
                            "component": comp,
                            "download_url": f"{base_url}/{cycle}/{comp.lower()}_{cycle}.aspx",
                            "description": f"NHANES {comp} data for {cycle}",
                        }
                    )

        return {
            "status": "success",
            "data": {
                "datasets": datasets[:20],  # Limit results
                "note": "NHANES data is available as downloadable files (SAS, XPT formats) from the CDC website. Visit the download URLs to access datasets. Files may require SAS or conversion tools to read.",
            },
            "metadata": {
                "source": "CDC NHANES",
                "endpoint": self.endpoint,
                "query": arguments,
            },
        }

    def _search_datasets(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for NHANES datasets."""
        search_term = arguments.get("search_term", "").lower()
        year = arguments.get("year")
        limit = arguments.get("limit", 20)

        # Common NHANES dataset keywords
        common_datasets = [
            {
                "name": "Demographics",
                "keywords": ["demographics", "age", "gender", "race"],
            },
            {"name": "Glucose", "keywords": ["glucose", "blood sugar", "diabetes"]},
            {
                "name": "Blood Pressure",
                "keywords": ["blood pressure", "hypertension", "bp"],
            },
            {"name": "Body Measures", "keywords": ["body", "bmi", "weight", "height"]},
            {"name": "Dietary", "keywords": ["diet", "nutrition", "food", "calories"]},
            {"name": "Laboratory", "keywords": ["lab", "laboratory", "test", "blood"]},
        ]

        datasets = []
        for ds in common_datasets:
            if not search_term or any(kw in search_term for kw in ds["keywords"]):
                cycle = year or "2017-2018"
                datasets.append(
                    {
                        "name": f"NHANES {ds['name']} - {cycle}",
                        "year": cycle,
                        "download_url": f"https://wwwn.cdc.gov/Nchs/Nhanes/{cycle}/",
                    }
                )
                if len(datasets) >= limit:
                    break

        return {
            "status": "success",
            "data": {
                "datasets": datasets,
                "note": "NHANES datasets are available for download from the CDC website. Use the download URLs to access data files.",
            },
            "metadata": {
                "source": "CDC NHANES",
                "endpoint": self.endpoint,
                "query": arguments,
            },
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the NHANES tool."""
        if self.endpoint == "dataset_info":
            return self._get_dataset_info(arguments)
        elif self.endpoint == "search":
            return self._search_datasets(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}
