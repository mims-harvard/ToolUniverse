# hubmap_tool.py
"""
HuBMAP (Human BioMolecular Atlas Program) tool for ToolUniverse.

Provides access to HuBMAP APIs for searching spatial biology datasets,
listing available organs, and retrieving dataset metadata.

APIs:
- Search API: https://search.api.hubmapconsortium.org/v3/search
- Ontology API: https://ontology.api.hubmapconsortium.org
- Entity API: https://entity.api.hubmapconsortium.org

No authentication required for public datasets.
"""

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


HUBMAP_SEARCH_URL = "https://search.api.hubmapconsortium.org/v3/search"
HUBMAP_ONTOLOGY_URL = "https://ontology.api.hubmapconsortium.org"
HUBMAP_ENTITY_URL = "https://entity.api.hubmapconsortium.org"


@register_tool("HuBMAPTool")
class HuBMAPTool(BaseTool):
    """
    Tool for querying HuBMAP datasets, organs, and dataset details.

    Supports searching published human tissue datasets by organ, assay type,
    and free text; listing available organs; and getting dataset metadata.

    No authentication required.
    """

    def __init__(self, tool_config: dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.operation = fields.get("operation", "search_datasets")

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if self.operation == "search_datasets":
                return self._search_datasets(arguments)
            elif self.operation == "list_organs":
                return self._list_organs(arguments)
            elif self.operation == "get_dataset":
                return self._get_dataset(arguments)
            else:
                return {
                    "status": "error",
                    "error": f"Unknown operation: {self.operation}",
                }
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"HuBMAP API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to HuBMAP API",
            }
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _search_datasets(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Search HuBMAP datasets by organ, assay type, or free text."""
        organ = arguments.get("organ")
        dataset_type = arguments.get("dataset_type")
        query_text = arguments.get("query")
        limit = min(int(arguments.get("limit", 10)), 50)
        status_filter = arguments.get("status", "Published")

        must_clauses = [{"match": {"entity_type": "Dataset"}}]

        if status_filter:
            must_clauses.append({"match": {"status": status_filter}})

        if organ:
            must_clauses.append({"match": {"origin_samples.organ": organ.upper()}})

        if dataset_type:
            must_clauses.append({"match": {"dataset_type": dataset_type}})

        if query_text:
            must_clauses.append(
                {
                    "multi_match": {
                        "query": query_text,
                        "fields": [
                            "title",
                            "description",
                            "dataset_type",
                            "anatomy_0",
                            "anatomy_1",
                        ],
                    }
                }
            )

        body = {
            "size": limit,
            "query": {"bool": {"must": must_clauses}},
            "_source": [
                "hubmap_id",
                "dataset_type",
                "origin_samples.organ",
                "status",
                "title",
                "anatomy_0",
                "anatomy_1",
                "group_name",
                "created_timestamp",
                "doi_url",
                "data_types",
                "donor.mapped_metadata.sex",
                "donor.mapped_metadata.age_value",
            ],
        }

        resp = requests.post(
            HUBMAP_SEARCH_URL,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)

        results = []
        for h in hits:
            src = h.get("_source", {})
            organs = [
                s.get("organ", "")
                for s in src.get("origin_samples", [])
                if s.get("organ")
            ]
            donor = src.get("donor", {})
            mapped = donor.get("mapped_metadata", {}) if donor else {}

            results.append(
                {
                    "hubmap_id": src.get("hubmap_id"),
                    "title": src.get("title"),
                    "dataset_type": src.get("dataset_type"),
                    "organ": organs[0] if organs else None,
                    "status": src.get("status"),
                    "group_name": src.get("group_name"),
                    "anatomy": src.get("anatomy_0") or src.get("anatomy_1"),
                    "doi_url": src.get("doi_url"),
                    "data_types": src.get("data_types"),
                    "donor_sex": mapped.get("sex") if mapped else None,
                    "donor_age": mapped.get("age_value") if mapped else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(results),
                "datasets": results,
            },
        }

    def _list_organs(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """List all organs available in HuBMAP."""
        url = f"{HUBMAP_ONTOLOGY_URL}/organs?application_context=HUBMAP"
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        organs = resp.json()

        results = []
        for org in organs:
            results.append(
                {
                    "code": org.get("rui_code"),
                    "term": org.get("term"),
                    "organ_uberon": org.get("organ_uberon"),
                    "organ_cui": org.get("organ_cui"),
                    "rui_supported": org.get("rui_supported"),
                }
            )

        return {
            "status": "success",
            "data": {"total": len(results), "organs": results},
        }

    def _get_dataset(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Get detailed metadata for a specific HuBMAP dataset."""
        hubmap_id = arguments.get("hubmap_id")
        if not hubmap_id:
            return {"status": "error", "error": "hubmap_id is required"}

        url = f"{HUBMAP_ENTITY_URL}/entities/{hubmap_id}"
        resp = requests.get(url, timeout=self.timeout)

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Dataset not found: {hubmap_id}",
            }
        resp.raise_for_status()
        data = resp.json()

        organs = [
            s.get("organ", "")
            for s in data.get("origin_samples", [{}])
            if isinstance(s, dict) and s.get("organ")
        ]

        contacts = data.get("contacts", [])
        contributors = data.get("contributors", [])

        result = {
            "hubmap_id": data.get("hubmap_id"),
            "entity_type": data.get("entity_type"),
            "dataset_type": data.get("dataset_type"),
            "status": data.get("status"),
            "title": data.get("title"),
            "description": data.get("description"),
            "organ": organs[0] if organs else None,
            "group_name": data.get("group_name"),
            "data_types": data.get("data_types"),
            "doi_url": data.get("doi_url"),
            "dbgap_study_url": data.get("dbgap_study_url"),
            "contains_human_genetic_sequences": data.get(
                "contains_human_genetic_sequences"
            ),
            "data_access_level": data.get("data_access_level"),
            "created_timestamp": data.get("created_timestamp"),
            "contacts": [
                {"name": c.get("name"), "email": c.get("email")} for c in contacts[:5]
            ]
            if contacts
            else [],
            "contributors": [
                {"name": c.get("name"), "affiliation": c.get("affiliation")}
                for c in contributors[:10]
            ]
            if contributors
            else [],
        }

        return {"status": "success", "data": result}
