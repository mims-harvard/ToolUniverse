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

import json

import requests
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


HUBMAP_SEARCH_URL = "https://search.api.hubmapconsortium.org/v3/search"
HUBMAP_ONTOLOGY_URL = "https://ontology.api.hubmapconsortium.org"
HUBMAP_ENTITY_URL = "https://entity.api.hubmapconsortium.org"


DONOR_ATTRIBUTES_PER_ENTITY = 25


def _donor_attributes(entity: dict[str, Any]) -> list[dict[str, Any]]:
    """What a Donor was, from the UMLS-coded assertions HuBMAP records.

    `metadata.organ_donor_data` holds one row per attribute -- Age 66 years,
    Sex, Race -- each with the vocabulary and code that defines it.
    """
    metadata = entity.get("metadata")
    if not isinstance(metadata, dict):
        return []
    rows = metadata.get("organ_donor_data") or metadata.get("living_donor_data")
    if isinstance(rows, dict):
        rows = [rows]
    if not isinstance(rows, list):
        return []
    out = []
    for row in rows[:DONOR_ATTRIBUTES_PER_ENTITY]:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "attribute": row.get("grouping_concept_preferred_term")
                or row.get("preferred_term"),
                "value": row.get("data_value"),
                "units": row.get("units") or None,
                "data_type": row.get("data_type"),
                "code": row.get("code"),
                "concept_id": row.get("concept_id"),
                "vocabulary": row.get("sab"),
            }
        )
    return out


def _ccf_annotations(entity: dict[str, Any]) -> list[str]:
    """The anatomical structures a sample's spatial registration overlaps."""
    location = entity.get("rui_location")
    if isinstance(location, str):
        try:
            location = json.loads(location)
        except (ValueError, TypeError):
            return []
    if not isinstance(location, dict):
        return []
    annotations = location.get("ccf_annotations")
    if not isinstance(annotations, list):
        return []
    return [item for item in annotations if isinstance(item, str)]


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
            elif self.operation == "get_provenance":
                return self._get_provenance(arguments)
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
        offset = max(0, int(arguments.get("offset", 0)))
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
            "from": offset,
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

        has_more = offset + len(results) < total
        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": has_more,
                "next_offset": offset + len(results) if has_more else None,
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
            category = org.get("category") or {}
            results.append(
                {
                    # `code` has always been the two-letter RUI code, not the
                    # ontology `code` field; both are reported now, under names
                    # that say which is which.
                    "code": org.get("rui_code"),
                    "rui_code": org.get("rui_code"),
                    "ontology_code": org.get("code"),
                    "term": org.get("term"),
                    "organ_uberon": org.get("organ_uberon"),
                    "organ_cui": org.get("organ_cui"),
                    "rui_supported": org.get("rui_supported"),
                    # "Eye (Left)" and "Eye (Right)" are separate entries whose
                    # side was legible only inside the term string, and whose
                    # shared parent organ (Eye, UBERON:0000970) was dropped.
                    "laterality": org.get("laterality"),
                    "category_term": category.get("term")
                    if isinstance(category, dict)
                    else None,
                    "category_organ_uberon": category.get("organ_uberon")
                    if isinstance(category, dict)
                    else None,
                    # Which vocabulary asserts the entry.
                    "sab": org.get("sab"),
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

        def format_person(person):
            return {
                "name": person.get("display_name") or person.get("name"),
                "first_name": person.get("first_name"),
                "middle_name_or_initial": person.get("middle_name_or_initial"),
                "last_name": person.get("last_name"),
                "email": person.get("email"),
                "affiliation": person.get("affiliation"),
                # HuBMAP sends `orcid_id`; reading `orcid` meant every
                # contributor's ORCID came back null (checked on
                # HBM626.FHJD.938, where all of them have one).
                "orcid": person.get("orcid") or person.get("orcid_id"),
                "is_contact": person.get("is_contact"),
                "is_operator": person.get("is_operator"),
                "is_principal_investigator": person.get("is_principal_investigator"),
            }

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
            "contacts": [format_person(contact) for contact in contacts],
            "contacts_count": len(contacts),
            "contributors": [
                format_person(contributor) for contributor in contributors
            ],
            "contributors_count": len(contributors),
            # The dataset record names the samples it was derived from, and
            # their spatial registration says where in the organ the tissue
            # came from. Only the organ name was read.
            "direct_ancestors": [
                {
                    "entity_type": ancestor.get("entity_type"),
                    "hubmap_id": ancestor.get("hubmap_id"),
                    "uuid": ancestor.get("uuid"),
                    "sample_category": ancestor.get("sample_category"),
                    "protocol_url": ancestor.get("protocol_url"),
                    "spatial_annotations": _ccf_annotations(ancestor),
                }
                for ancestor in (data.get("direct_ancestors") or [])
                if isinstance(ancestor, dict)
            ],
        }

        return {"status": "success", "data": result}

    def _get_provenance(self, arguments: dict[str, Any]) -> dict[str, Any]:
        """Retrieve a dataset's biological provenance lineage (ancestors chain).

        Returns the ordered chain of ancestor entities for a HuBMAP dataset:
        Dataset -> Sample (section / block / organ) -> Donor.
        """
        uuid = arguments.get("uuid") or arguments.get("hubmap_id")
        if not uuid:
            return {
                "status": "error",
                "error": "uuid (or hubmap_id) is required",
            }

        url = f"{HUBMAP_ENTITY_URL}/ancestors/{uuid}"
        resp = requests.get(url, timeout=self.timeout)

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Entity not found: {uuid}",
            }
        resp.raise_for_status()
        ancestors = resp.json()

        if not isinstance(ancestors, list):
            return {
                "status": "error",
                "error": f"Unexpected response for ancestors of {uuid}",
            }

        # Rank entities so the lineage reads Dataset -> Sample -> Donor, and
        # Samples are ordered by anatomical granularity (section -> organ).
        sample_rank = {"section": 1, "suspension": 1, "block": 2, "organ": 3}
        type_rank = {"Dataset": 0, "Sample": 1, "Donor": 2, "Publication": 3}

        def _sort_key(entity: dict[str, Any]) -> tuple:
            etype = entity.get("entity_type", "")
            cat = (entity.get("sample_category") or "").lower()
            return (type_rank.get(etype, 9), sample_rank.get(cat, 0))

        lineage = []
        for entity in sorted(ancestors, key=_sort_key):
            lineage.append(
                {
                    "entity_type": entity.get("entity_type"),
                    "hubmap_id": entity.get("hubmap_id"),
                    "uuid": entity.get("uuid"),
                    "sample_category": entity.get("sample_category"),
                    "organ": entity.get("organ"),
                    "dataset_type": entity.get("dataset_type"),
                    "group_name": entity.get("group_name"),
                    "description": entity.get("description"),
                    "protocol_url": entity.get("protocol_url"),
                    "created_timestamp": entity.get("created_timestamp"),
                    "data_access_level": entity.get("data_access_level"),
                    # The whole point of walking to the Donor is what the
                    # donor was: age 66, sex, race. It is in the same
                    # response, under metadata.organ_donor_data, and the
                    # lineage row carried seven keys that did not include it.
                    "donor_attributes": _donor_attributes(entity),
                    # The ancestor entities credit people too. Their records
                    # belong to HuBMAP_get_dataset for that hubmap_id, so the
                    # count says they exist rather than duplicating them here.
                    "contributor_count": len(entity.get("contributors") or []),
                    "contact_count": len(entity.get("contacts") or []),
                    # Where in the organ the sample was taken from.
                    "spatial_annotations": _ccf_annotations(entity),
                }
            )

        return {
            "status": "success",
            "data": {
                "uuid": uuid,
                "ancestor_count": len(lineage),
                "lineage": lineage,
            },
            "metadata": {"source": "HuBMAP Entity API (ancestors)"},
        }
