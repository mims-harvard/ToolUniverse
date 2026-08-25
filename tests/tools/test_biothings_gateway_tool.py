"""Unit tests for the BioThings API gateway tool.

The gateway reaches ~50 BioThings-hosted APIs through one uniform
interface, so the tests focus on routing, validation, and the fallback
path used when an API does not expose a typed annotation route.
"""

import pytest
from tooluniverse import ToolUniverse
from tooluniverse.biothings_gateway_tool import BIOTHINGS_APIS


EXPECTED_TOOLS = [
    "BioThings_list_apis",
    "BioThings_query",
    "BioThings_get_entity",
    "BioThings_get_metadata",
]

TRANSIENT = ("timed out", "Failed to connect", "returned HTTP 5")


@pytest.fixture(scope="module")
def tu():
    instance = ToolUniverse()
    instance.load_tools()
    return instance


def data_of(result):
    """Return result['data'], skipping on a transient upstream failure."""
    if result.get("status") == "error":
        error = str(result.get("error", ""))
        if any(t in error for t in TRANSIENT):
            pytest.skip(f"upstream temporarily unavailable: {error[:80]}")
        pytest.fail(f"unexpected error response: {error[:200]}")
    return result["data"]


class TestRegistration:
    def test_tools_load(self, tu):
        names = {t.get("name") for t in tu.all_tools if isinstance(t, dict)}
        assert not [n for n in EXPECTED_TOOLS if n not in names]

    def test_names_within_mcp_limit(self):
        assert not [n for n in EXPECTED_TOOLS if len(n) > 55]


class TestListApis:
    def test_lists_all_registered_apis(self, tu):
        rows = data_of(tu.tools.BioThings_list_apis(only_without_dedicated_tool=False))
        assert len(rows) == len(BIOTHINGS_APIS)

    def test_filters_to_apis_without_dedicated_tool(self, tu):
        rows = data_of(tu.tools.BioThings_list_apis(only_without_dedicated_tool=True))
        assert rows
        assert all(r["preferred_tooluniverse_tool"] is None for r in rows)
        # this filter is the point of the gateway; it must not be empty
        slugs = {r["api"] for r in rows}
        assert {"ddinter", "repodb", "idisk", "ttd"} <= slugs

    def test_keyword_filter(self, tu):
        rows = data_of(tu.tools.BioThings_list_apis(keyword="drug"))
        assert rows
        assert all(
            "drug" in r["api"].lower() or "drug" in r["description"].lower()
            for r in rows
        )

    def test_duplicates_are_flagged(self, tu):
        rows = data_of(tu.tools.BioThings_list_apis(keyword="ontology"))
        flagged = [r for r in rows if r["preferred_tooluniverse_tool"]]
        assert flagged, "ontology APIs duplicate dedicated tools and must be flagged"


class TestQuery:
    def test_fielded_query(self, tu):
        result = tu.tools.BioThings_query(
            api="ddinter", q="drug_a.name:warfarin", size=2
        )
        rows = data_of(result)
        assert 0 < len(rows) <= 2
        assert all("_id" in r for r in rows)
        assert result["metadata"]["total_matching"] > 0

    def test_match_all_and_size_cap(self, tu):
        rows = data_of(tu.tools.BioThings_query(api="repodb", q="*", size=3))
        assert len(rows) <= 3

    def test_fields_projection(self, tu):
        rows = data_of(
            tu.tools.BioThings_query(api="repodb", q="*", size=1, fields="drug")
        )
        assert rows
        returned = set(rows[0]) - {"_id", "_score", "_version"}
        assert returned <= {"drug"}, f"unexpected fields returned: {returned}"

    def test_unknown_api_suggests_alternatives(self, tu):
        result = tu.tools.BioThings_query(api="ddintr", q="*")
        assert result["status"] == "error"
        assert "ddinter" in result["error"]

    def test_missing_query_returns_error(self, tu):
        result = tu.tools.BioThings_query(api="ddinter", q="")
        assert result["status"] == "error"


class TestGetEntity:
    def test_typed_annotation_route(self, tu):
        result = tu.tools.BioThings_get_entity(
            api="mondo", entity_id="MONDO:0010329"
        )
        data = data_of(result)
        assert data["_id"] == "MONDO:0010329"
        assert result["metadata"]["biothing_type"] == "disease"

    def test_roundtrip_id_from_query(self, tu):
        rows = data_of(tu.tools.BioThings_query(api="repodb", q="*", size=1))
        entity_id = rows[0]["_id"]
        data = data_of(
            tu.tools.BioThings_get_entity(api="repodb", entity_id=entity_id)
        )
        assert data["_id"] == entity_id

    def test_unknown_id_returns_error(self, tu):
        result = tu.tools.BioThings_get_entity(api="ddinter", entity_id="NOTREAL")
        assert result["status"] == "error"


class TestGetMetadata:
    def test_metadata_reports_type_and_stats(self, tu):
        data = data_of(tu.tools.BioThings_get_metadata(api="ddinter"))
        assert data["biothing_type"]
        assert data["stats"]

    def test_include_fields_lists_queryable_fields(self, tu):
        data = data_of(
            tu.tools.BioThings_get_metadata(api="ddinter", include_fields=True)
        )
        assert data["queryable_fields"], "expected a non-empty field list"


class TestErrorHandling:
    @pytest.mark.parametrize(
        "tool_name,kwargs",
        [
            ("BioThings_query", {"api": "not_an_api", "q": "*"}),
            ("BioThings_get_entity", {"api": "not_an_api", "entity_id": "x"}),
            ("BioThings_get_metadata", {"api": "not_an_api"}),
        ],
    )
    def test_returns_error_dict_not_exception(self, tu, tool_name, kwargs):
        result = getattr(tu.tools, tool_name)(**kwargs)
        assert isinstance(result, dict)
        assert result["status"] == "error"
        assert isinstance(result.get("error"), str) and result["error"]
