"""
IGSR Tool - International Genome Sample Resource (1000 Genomes Project)

IGSR hosts the 1000 Genomes Project data and related datasets that provide
a comprehensive catalog of human genetic variation across global populations.
The resource includes 4,989 samples from 212 populations grouped into
superpopulations (AFR, AMR, EAS, EUR, SAS).

API base: https://www.internationalgenome.org/api/beta
No authentication required. Elasticsearch-based API.

Reference: Byrska-Bishop et al., Cell 2022, 185(18):3426-3440
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


IGSR_BASE_URL = "https://www.internationalgenome.org/api/beta"


def _pagination_arguments(
    arguments: Dict[str, Any], *, default_limit: int
) -> tuple[int | None, int | None, str | None]:
    """Validate IGSR's real 500-record page boundary without clamping."""
    raw_limit = arguments.get("limit", default_limit)
    raw_offset = arguments.get("offset", 0)
    try:
        if isinstance(raw_limit, bool) or isinstance(raw_offset, bool):
            raise ValueError
        limit = int(raw_limit)
        offset = int(raw_offset)
        if isinstance(raw_limit, float) and not raw_limit.is_integer():
            raise ValueError
        if isinstance(raw_offset, float) and not raw_offset.is_integer():
            raise ValueError
        if not 1 <= limit <= 500 or offset < 0:
            raise ValueError
    except (TypeError, ValueError):
        return None, None, "limit must be 1-500 and offset must be non-negative"
    return limit, offset, None


@register_tool("IGSRTool")
class IGSRTool(BaseTool):
    """
    Tool for querying the International Genome Sample Resource (1000 Genomes).

    Provides access to population, sample, and data collection metadata
    from the 1000 Genomes Project and related studies.

    Supported operations:
    - search_populations: Search/list populations with superpopulation filtering
    - search_samples: Search samples by population, data collection
    - list_data_collections: List available data collections/studies
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.timeout = 30

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the IGSR API tool with given arguments."""
        operation = arguments.get("operation")
        if not operation:
            # Fall back to schema default (set per tool in JSON config)
            props = self.tool_config.get("parameter", {}).get("properties", {})
            operation = props.get("operation", {}).get("default")

        operation_handlers = {
            "search_populations": self._search_populations,
            "search_samples": self._search_samples,
            "list_data_collections": self._list_data_collections,
        }

        handler = operation_handlers.get(operation)
        if not handler:
            return {
                "status": "error",
                "error": "Unknown operation: {}. Available: {}".format(
                    operation, list(operation_handlers.keys())
                ),
            }

        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "IGSR API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to IGSR API"}
        except Exception as e:
            return {"status": "error", "error": f"IGSR API error: {str(e)}"}

    def _es_search(self, index: str, body: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an Elasticsearch search against IGSR API."""
        url = f"{IGSR_BASE_URL}/{index}/_search"
        response = self.session.post(
            url,
            json=body,
            headers={"Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _total_hits(raw: Dict[str, Any]) -> int:
        """Number of documents matching the query, independent of page size.

        Elasticsearch reports this either as a bare integer or as
        ``{"value": N, "relation": ...}`` depending on server version.
        """
        total = raw.get("hits", {}).get("total", 0)
        if isinstance(total, dict):
            total = total.get("value", 0)
        return total or 0

    def _search_populations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search 1000 Genomes populations by superpopulation or name."""
        superpopulation = arguments.get("superpopulation")
        query_text = arguments.get("query")
        limit, offset, pagination_error = _pagination_arguments(
            arguments, default_limit=25
        )
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert limit is not None and offset is not None

        # Fetch all populations (212 total) when superpopulation filter is needed,
        # since the superpopulation.code field is not keyword-indexed in Elasticsearch.
        fetch_limit = 500 if superpopulation else limit
        body: Dict[str, Any] = {"size": fetch_limit}
        if not superpopulation:
            body["from"] = offset

        filters = []
        if query_text:
            filters.append(
                {
                    "bool": {
                        "should": [
                            {"match": {"name": query_text}},
                            {"match": {"description": query_text}},
                            {"match": {"code": query_text.upper()}},
                        ],
                        "minimum_should_match": 1,
                    }
                }
            )

        if filters:
            body["query"] = {"bool": {"filter": filters}}

        raw = self._es_search("population", body)

        populations = []
        for hit in raw.get("hits", {}).get("hits", []):
            src = hit["_source"]
            superpop = src.get("superpopulation", {})
            # Client-side superpopulation filter (field not keyword-indexed in ES)
            if (
                superpopulation
                and (superpop.get("code") or "").upper() != superpopulation.upper()
            ):
                continue
            populations.append(
                {
                    "code": src.get("code", ""),
                    "name": src.get("name", ""),
                    "description": src.get("description", ""),
                    "sample_count": src.get("samples", {}).get("count", 0),
                    "superpopulation_code": superpop.get("code", ""),
                    "superpopulation_name": superpop.get("name", ""),
                    "latitude": src.get("latitude"),
                    "longitude": src.get("longitude"),
                }
            )
        # `total` is the size of the matching result set, not of the page. When the
        # superpopulation filter is applied client-side the Elasticsearch hit count
        # ignores it, so the post-filter length is the authoritative total there.
        total = len(populations) if superpopulation else self._total_hits(raw)
        if superpopulation:
            populations = populations[offset : offset + limit]
        next_offset = offset + len(populations)
        has_more = next_offset < total

        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(populations),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "populations": populations,
            },
            "metadata": {
                "source": "IGSR / 1000 Genomes Project (internationalgenome.org)",
                "filter_superpopulation": superpopulation,
                "filter_query": query_text,
            },
        }

    def _search_samples(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search 1000 Genomes samples by population or data collection."""
        population = arguments.get("population")
        data_collection = arguments.get("data_collection")
        sample_name = arguments.get("sample_name")
        limit, offset, pagination_error = _pagination_arguments(
            arguments, default_limit=25
        )
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert limit is not None and offset is not None

        body: Dict[str, Any] = {"size": limit, "from": offset}

        filters = []
        if population:
            filters.append({"term": {"populations.code": population.upper()}})
        if data_collection:
            filters.append({"match": {"dataCollections.title": data_collection}})
        if sample_name:
            filters.append({"match": {"name": sample_name}})

        if filters:
            body["query"] = {"bool": {"filter": filters}}

        raw = self._es_search("sample", body)

        samples = []
        for hit in raw.get("hits", {}).get("hits", []):
            src = hit["_source"]
            pops = src.get("populations", [])
            pop_info = [
                {
                    "code": p.get("code", ""),
                    "name": p.get("name", ""),
                    "superpopulation": p.get("superpopulationCode", ""),
                }
                for p in pops
            ]
            dc_titles = [dc.get("title", "") for dc in src.get("dataCollections", [])]
            samples.append(
                {
                    "name": src.get("name", ""),
                    "sex": src.get("sex", ""),
                    "biosample_id": src.get("biosampleId", ""),
                    "populations": pop_info,
                    "data_collections": dc_titles,
                }
            )

        total = self._total_hits(raw)
        next_offset = offset + len(samples)
        has_more = next_offset < total
        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(samples),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "samples": samples,
            },
            "metadata": {
                "source": "IGSR / 1000 Genomes Project (internationalgenome.org)",
                "filter_population": population,
                "filter_data_collection": data_collection,
            },
        }

    def _list_data_collections(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List available 1000 Genomes data collections and studies."""
        limit, offset, pagination_error = _pagination_arguments(
            arguments, default_limit=50
        )
        if pagination_error:
            return {"status": "error", "error": pagination_error}
        assert limit is not None and offset is not None

        body: Dict[str, Any] = {"size": limit, "from": offset}
        raw = self._es_search("data-collection", body)

        collections = []
        for hit in raw.get("hits", {}).get("hits", []):
            src = hit["_source"]
            collections.append(
                {
                    "code": src.get("code", hit.get("_id", "")),
                    "title": src.get("title", ""),
                    "short_title": src.get("shortTitle", ""),
                    "sample_count": src.get("samples", {}).get("count", 0),
                    "population_count": src.get("populations", {}).get("count", 0),
                    "data_types": src.get("dataTypes", []),
                    "website": src.get("website"),
                }
            )

        total = self._total_hits(raw)
        next_offset = offset + len(collections)
        has_more = next_offset < total
        return {
            "status": "success",
            "data": {
                "total": total,
                "returned": len(collections),
                "offset": offset,
                "has_more": has_more,
                "next_offset": next_offset if has_more else None,
                "collections": collections,
            },
            "metadata": {
                "source": "IGSR / 1000 Genomes Project (internationalgenome.org)",
            },
        }
