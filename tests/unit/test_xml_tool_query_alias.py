"""XMLTool-family tools (drugbank_*, mesh_*) all take a single search
parameter named 'query', regardless of what the tool's own NAME promises.

Regression for Fix Round 17: calling
drugbank_get_pharmacology_by_drug_name_or_drugbank_id with 'drug_name' (the
exact term used in the tool's own name) errored with "'query' is a required
property" -- schema validation runs before run(), so an alias resolved only
inside run() would never fire for a normal (validated) call. The fix
resolves the alias inside validate_parameters() itself, mutating the shared
arguments dict in place so the resolved 'query' is also visible to the
subsequent run() call.
"""

import pytest

pytestmark = pytest.mark.unit


def _make_tool(parameter_overrides=None):
    from tooluniverse.xml_tool import XMLDatasetTool

    config = {
        "name": "drugbank_get_pharmacology_by_drug_name_or_drugbank_id",
        "parameter": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "condition": {"type": "string"},
                "value": {"type": "string"},
            },
            "required": ["query"],
        },
        "settings": {
            # No real dataset path -- _load_dataset() catches the failure and
            # leaves self.records == [], which is fine for validation-layer tests.
            "record_xpath": ".//*",
        },
    }
    if parameter_overrides:
        config["parameter"].update(parameter_overrides)
    return XMLDatasetTool(config)


@pytest.mark.parametrize("alias", ["drug_name", "drugbank_id"])
def test_alias_resolved_before_schema_validation(alias):
    tool = _make_tool()
    arguments = {alias: "buprenorphine"}
    error = tool.validate_parameters(arguments)
    assert error is None, f"expected no validation error, got: {error}"
    # The alias resolution must mutate the same dict object run() will see.
    assert arguments["query"] == "buprenorphine"


def test_unrecognized_alias_still_errors_with_helpful_message():
    tool = _make_tool()
    error = tool.validate_parameters({"totally_unrelated_key": "x"})
    assert error is not None
    assert "query" in str(error.message if hasattr(error, "message") else error)


def test_explicit_query_takes_precedence_over_alias():
    tool = _make_tool()
    arguments = {"query": "aspirin", "drug_name": "ibuprofen"}
    error = tool.validate_parameters(arguments)
    assert error is None
    assert arguments["query"] == "aspirin"


def test_condition_based_filter_call_is_unaffected():
    # drugbank_filter_drugs_by_name's real schema requires condition+value,
    # not query -- matches that shape rather than the search-tool default.
    tool = _make_tool(
        parameter_overrides={"required": ["condition", "value"]}
    )
    arguments = {"condition": "type", "value": "small molecule"}
    error = tool.validate_parameters(arguments)
    assert error is None
    assert "query" not in arguments
