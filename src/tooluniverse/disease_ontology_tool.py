# disease_ontology_tool.py
"""
Disease Ontology (DO) REST API tool for ToolUniverse.

The Disease Ontology provides a standardized ontology for human disease terms.
It is widely used in bioinformatics for disease annotation and cross-referencing
with ICD-10, OMIM, MeSH, NCI Thesaurus, and SNOMED-CT.

API: https://www.disease-ontology.org/api/
No authentication required.
"""

from typing import Dict, Any

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

DO_BASE_URL = "https://www.disease-ontology.org/api/metadata"


@register_tool("DiseaseOntologyTool")
class DiseaseOntologyTool(BaseTool):
    """
    Tool for querying the Disease Ontology (DO) REST API.

    The Disease Ontology semantically integrates disease and medical
    vocabularies through cross-mapping of DO terms to MeSH, ICD,
    NCI Thesaurus, SNOMED CT, and OMIM.

    Supports: term lookup, parent hierarchy navigation.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_term")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Disease Ontology API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Disease Ontology API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Disease Ontology API",
            }
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return {
                    "status": "error",
                    "error": f"DOID not found in Disease Ontology",
                }
            return {
                "status": "error",
                "error": f"Disease Ontology API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Disease Ontology: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate Disease Ontology endpoint."""
        if self.endpoint == "get_term":
            return self._get_term(arguments)
        elif self.endpoint == "get_parents":
            return self._get_parents(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    @staticmethod
    def _normalize_doid(value: Any) -> tuple[str | None, str | None]:
        if not isinstance(value, str) or not value.strip():
            return None, "doid must be a non-empty string"
        raw = value.strip()
        if ":" in raw:
            parts = raw.split(":")
            if len(parts) != 2 or parts[0].upper() != "DOID":
                return None, "doid must have format DOID:<numeric ID>"
            numeric_id = parts[1]
        else:
            numeric_id = raw
        if not numeric_id.isdigit():
            return None, "doid must have format DOID:<numeric ID>"
        return f"DOID:{numeric_id}", None

    def _fetch_term(self, doid: str) -> Dict[str, Any]:
        """Fetch a single DO term by DOID."""
        canonical_id, error = self._normalize_doid(doid)
        if error or canonical_id is None:
            raise ValueError(error)
        url = f"{DO_BASE_URL}/{canonical_id}/"
        response = requests.get(url, timeout=self.timeout, allow_redirects=True)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, dict) or data.get("id") != canonical_id:
            raise ValueError(
                f"Disease Ontology returned a different term for {canonical_id}"
            )
        return data

    @staticmethod
    def _validated_list(data: Dict[str, Any], field: str) -> list:
        value = data.get(field)
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError(f"Disease Ontology returned malformed {field}")
        return value

    def _parse_parents(self, data: Dict[str, Any]) -> list:
        parents = []
        for parent in self._validated_list(data, "parents"):
            if (
                not isinstance(parent, (list, tuple))
                or len(parent) < 3
                or any(not isinstance(value, str) for value in parent[:3])
            ):
                raise ValueError(
                    "Disease Ontology returned a malformed parent relation"
                )
            parents.append(
                {
                    "relationship": parent[0],
                    "name": parent[1],
                    "id": parent[2],
                    "source": parent[3] if len(parent) > 3 else None,
                }
            )
        return parents

    def _get_term(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a Disease Ontology term."""
        doid, error = self._normalize_doid(arguments.get("doid"))
        if error:
            return {"status": "error", "error": error}
        assert doid is not None

        data = self._fetch_term(doid)

        # Parse parents
        parents = self._parse_parents(data)

        # Parse synonyms (format: "name TYPE []")
        synonyms = self._validated_list(data, "synonyms")
        cross_references = self._validated_list(data, "xrefs")
        subsets = self._validated_list(data, "subsets")
        alternate_ids = self._validated_list(data, "alternateIds")
        skos_broad = self._validated_list(data, "skos_broadMatch")
        skos_exact = self._validated_list(data, "skos_exactMatch")
        skos_narrow = self._validated_list(data, "skos_narrowMatch")
        if any(
            any(not isinstance(item, str) for item in values)
            for values in (
                synonyms,
                cross_references,
                subsets,
                alternate_ids,
                skos_broad,
                skos_exact,
                skos_narrow,
            )
        ):
            return {
                "status": "error",
                "error": "Disease Ontology returned a malformed list-valued term field",
            }

        return {
            "status": "success",
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "definition": data.get("definition"),
                "synonyms": synonyms,
                "parents": parents,
                "cross_references": cross_references,
                "subsets": subsets,
                "alternate_ids": alternate_ids,
                "skos_broad_matches": skos_broad,
                "skos_exact_matches": skos_exact,
                "skos_narrow_matches": skos_narrow,
            },
            "metadata": {
                "source": "Disease Ontology (DO)",
                "requested_id": doid,
                "returned_id_verified": True,
                "source_record_complete": True,
                "omitted_internal_fields": ["neo4jid"],
            },
        }

    def _get_parents(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get parent terms for a Disease Ontology term with hierarchy navigation."""
        doid, error = self._normalize_doid(arguments.get("doid"))
        if error:
            return {"status": "error", "error": error}
        assert doid is not None

        data = self._fetch_term(doid)

        parents_detail = []
        direct_parents = self._parse_parents(data)
        failed_parent_fetches = []
        for parent in direct_parents:
            parent_id = parent["id"]
            try:
                parent_data = self._fetch_term(parent_id)
                grandparents = [
                    {
                        "id": grandparent["id"],
                        "name": grandparent["name"],
                        "relationship": grandparent["relationship"],
                        "source": grandparent["source"],
                    }
                    for grandparent in self._parse_parents(parent_data)
                ]
                parents_detail.append(
                    {
                        "id": parent_id,
                        "name": parent_data.get("name"),
                        "definition": parent_data.get("definition"),
                        "relationship": parent["relationship"],
                        "source": parent["source"],
                        "grandparents": grandparents,
                        "fetch_complete": True,
                    }
                )
            except Exception as exc:
                failed_parent_fetches.append(
                    {"id": parent_id, "error": f"{type(exc).__name__}: {exc}"}
                )
                parents_detail.append(
                    {
                        "id": parent_id,
                        "name": parent["name"],
                        "definition": None,
                        "relationship": parent["relationship"],
                        "source": parent["source"],
                        "grandparents": [],
                        "fetch_complete": False,
                    }
                )

        return {
            "status": "success",
            "data": {
                "id": data.get("id"),
                "name": data.get("name"),
                "parents": parents_detail,
            },
            "metadata": {
                "source": "Disease Ontology (DO)",
                "requested_id": doid,
                "returned_id_verified": True,
                "hierarchy_depth_returned": 2,
                "direct_parent_count": len(direct_parents),
                "resolved_parent_count": len(direct_parents)
                - len(failed_parent_fetches),
                "parent_expansion_complete": not failed_parent_fetches,
                "failed_parent_fetches": failed_parent_fetches,
                "full_ancestry_complete": not direct_parents,
            },
        }
