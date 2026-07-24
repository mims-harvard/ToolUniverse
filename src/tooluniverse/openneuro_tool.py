"""
OpenNeuro GraphQL API tool for ToolUniverse.

OpenNeuro is an open platform for validating and sharing brain imaging data
(BIDS format). It hosts 1000+ neuroimaging datasets (fMRI, EEG, MRI, etc.).

GraphQL API: https://openneuro.org/crn/graphql
No authentication required for public datasets. Public access.
"""

import copy
import requests

from .graphql_tool import GraphQLTool, remove_none_and_empty_values
from .tool_registry import register_tool

# Facet keys accepted by the OpenNeuro DatasetSearchInput type. Flat tool
# arguments matching these names are collected into the GraphQL `query` object
# variable ($q) for advancedSearch. Keys absent from this set (e.g. `first`)
# are treated as top-level query arguments instead.
_ADVANCED_SEARCH_FACETS = frozenset(
    {
        "ageRange",
        "authors",
        "bidsDatasetType",
        "bodyParts",
        "diagnosis",
        "keywords",
        "modality",
        "scannerManufacturers",
        "sex",
        "species",
        "studyDomains",
        "subjectCountRange",
        "tasks",
        "tracerNames",
        "tracerRadionuclides",
    }
)


@register_tool("OpenNeuroTool")
class OpenNeuroTool(GraphQLTool):
    """
    Tool for querying the OpenNeuro neuroimaging data repository.

    OpenNeuro stores brain imaging datasets in BIDS format including:
    - MRI, fMRI, EEG, MEG, PET datasets
    - Dataset metadata, subjects, tasks, modalities
    - Download information and analytics

    No authentication required for public datasets.
    """

    def __init__(self, tool_config: dict):
        endpoint_url = "https://openneuro.org/crn/graphql"
        super().__init__(tool_config, endpoint_url)

    def run(self, arguments):
        # advancedSearch needs flat facet args (species, sex, ...) assembled
        # into a single DatasetSearchInput object bound to the `query` variable
        # ($q). It can also return partial data alongside per-dataset permission
        # errors for private results, which the base GraphQLTool would discard;
        # tolerate that so the participantCount and pageInfo.count still return.
        if self.tool_config.get("name") == "OpenNeuro_advanced_search":
            return self._run_advanced_search(arguments)
        return super().run(arguments)

    def _run_advanced_search(self, arguments):
        try:
            arguments = copy.deepcopy(arguments or {})

            query_obj = {
                key: value
                for key, value in arguments.items()
                if key in _ADVANCED_SEARCH_FACETS and value is not None
            }
            top_level = {
                key: value
                for key, value in arguments.items()
                if key not in _ADVANCED_SEARCH_FACETS and value is not None
            }
            variables = dict(top_level)
            # Always send a (possibly empty) query object; DatasetSearchInput! is
            # non-null and an empty {} matches all datasets.
            variables["query"] = query_obj

            response = requests.post(
                self.endpoint_url,
                json={"query": self.query_schema, "variables": variables},
                timeout=30,
            )
            if not response.ok:
                return {
                    "status": "error",
                    "error": (
                        f"OpenNeuro advancedSearch API error: HTTP "
                        f"{response.status_code}: {response.text[:300]}"
                    ),
                }

            payload = response.json()
            data = payload.get("data")
            # OpenNeuro returns partial data with `errors` when some matched
            # datasets are not anonymously readable (those edges become null).
            # Keep the usable data (counts + readable nodes) and surface the
            # permission errors as a non-fatal note rather than failing.
            if not data:
                errors = payload.get("errors")
                return {
                    "status": "error",
                    "error": (
                        "OpenNeuro advancedSearch returned no data"
                        + (f": {errors}" if errors else "")
                    ),
                }

            data = remove_none_and_empty_values({"data": data}).get("data", data)
            result = {"status": "success", "data": data}
            if payload.get("errors"):
                result["metadata"] = {
                    "note": (
                        "Some matched datasets are not anonymously readable; "
                        "their edges were omitted. pageInfo.count and "
                        "participantCount remain accurate."
                    )
                }
            return result
        except Exception as exc:  # never raise out of run()
            return {
                "status": "error",
                "error": f"OpenNeuro advancedSearch API error: {exc}",
            }
