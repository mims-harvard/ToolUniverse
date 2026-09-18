"""
NCI Image Data Commons (IDC) v3 API tool.

IDC (https://imaging.datacommons.cancer.gov/) is NCI's public, no-auth-required
repository of cancer imaging data spanning both radiology (CT/MRI/PET) and
digital pathology (whole-slide images), complementing TCIA (which this
repository already covers via tcia_tool.py) with a newer, cohort-oriented API
and pathology coverage TCIA's NBIA REST API does not provide.

API base: https://api.imaging.datacommons.cancer.gov/v3
Note: the v2 API is fully deprecated (confirmed live: returns HTTP 410 on every
endpoint, pointing callers at v3). No API key is required for any read
endpoint used here.

Full spec: https://api.imaging.datacommons.cancer.gov/v3/openapi.json
"""

import requests
from typing import Any, Dict
from .base_tool import BaseTool
from .tool_registry import register_tool

IDC_API_URL = "https://api.imaging.datacommons.cancer.gov/v3"


@register_tool("IDCTool")
class IDCTool(BaseTool):
    """
    Tool for querying NCI's Image Data Commons (IDC), a public, no-auth
    repository of cancer imaging collections spanning radiology and digital
    pathology, with a cohort-filter API for sizing a subset before use.
    """

    def __init__(self, tool_config: Dict[str, Any], timeout: int = 30):
        super().__init__(tool_config)
        self.timeout = timeout
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation")
        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        handlers = {
            "list_collections": self._list_collections,
            "get_collection": self._get_collection,
            "list_attributes": self._list_attributes,
            "list_attribute_values": self._list_attribute_values,
            "get_cohort_counts": self._get_cohort_counts,
        }

        handler = handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, ", ".join(handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IDC API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to IDC API"}
        except Exception as e:  # noqa: BLE001 - surfaced to the caller, not raised
            return {"status": "error", "error": "Operation failed: {}".format(str(e))}

    def _get(self, path: str, params=None) -> requests.Response:
        return requests.get(
            IDC_API_URL + path, params=params or {}, timeout=self.timeout
        )

    def _list_collections(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all IDC collections with cancer types, species, and subject counts."""
        response = self._get("/collections")
        response.raise_for_status()
        collections = response.json()
        return {
            "status": "success",
            "data": {"collections": collections, "total_count": len(collections)},
            "metadata": {"source": "NCI Image Data Commons (IDC) v3"},
        }

    def _get_collection(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed metadata for one collection: counts, modalities, license."""
        collection_id = arguments.get("collection_id")
        if not collection_id:
            return {
                "status": "error",
                "error": "Missing required parameter: collection_id",
            }

        response = self._get("/collections/{}".format(str(collection_id).strip()))
        if response.status_code == 422:
            return {
                "status": "error",
                "error": "Collection '{}' not found on IDC. Use "
                "IDC_list_collections to see valid collection_id values.".format(
                    collection_id
                ),
            }
        response.raise_for_status()
        return {
            "status": "success",
            "data": response.json(),
            "metadata": {
                "source": "NCI Image Data Commons (IDC) v3",
                "collection_id": collection_id,
            },
        }

    def _list_attributes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the attributes a cohort can be filtered on (name, type, kind)."""
        response = self._get("/attributes")
        response.raise_for_status()
        attributes = response.json()
        return {
            "status": "success",
            "data": {"attributes": attributes, "total_count": len(attributes)},
            "metadata": {"source": "NCI Image Data Commons (IDC) v3"},
        }

    def _list_attribute_values(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List the distinct real values of a categorical attribute (e.g. Modality)."""
        attribute = arguments.get("attribute")
        if not attribute:
            return {"status": "error", "error": "Missing required parameter: attribute"}

        limit = min(int(arguments.get("limit", 100) or 100), 10000)
        response = self._get(
            "/attributes/{}/values".format(str(attribute).strip()),
            params={"limit": limit},
        )
        if response.status_code == 422:
            return {
                "status": "error",
                "error": "Attribute '{}' not found. Use IDC_list_attributes to "
                "see valid attribute names.".format(attribute),
            }
        response.raise_for_status()
        return {
            "status": "success",
            "data": response.json(),
            "metadata": {
                "source": "NCI Image Data Commons (IDC) v3",
                "attribute": attribute,
            },
        }

    def _get_cohort_counts(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get patient/study/series/instance counts and total size for a filtered
        cohort, without downloading any sample rows. An empty filter is valid
        and describes all of IDC.
        """
        terms = arguments.get("terms")
        ranges = arguments.get("ranges")

        filters: Dict[str, Any] = {}
        if terms:
            filters["terms"] = terms
        if ranges:
            filters["ranges"] = ranges

        body = {"filters": filters} if filters else {"filters": {}}

        response = requests.post(
            IDC_API_URL + "/cohort/counts", json=body, timeout=self.timeout
        )
        if response.status_code == 400:
            return {
                "status": "error",
                "error": "IDC could not apply the given filter: {}".format(
                    response.text[:300]
                ),
            }
        response.raise_for_status()
        counts = response.json()
        return {
            "status": "success",
            "data": counts,
            "metadata": {
                "source": "NCI Image Data Commons (IDC) v3",
                "filters_sent": filters,
            },
        }
