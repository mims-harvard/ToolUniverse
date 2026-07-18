"""Regression guard for Fix-R13E-1 and Fix-R13E-3.

Fix-R13E-1: Wikidata_search_entities's `language` param was documented as
"Default: 'en'" but had no actual `default` in its JSON schema, so omitting
it sent no `language` param at all. Confirmed live that MediaWiki's
wbsearchentities then returns HTTP 200 with a `{"error": {"code":
"missingparam", ...}}` body -- a failure disguised as a ToolUniverse
success. Adding the schema default (BaseRESTTool applies schema defaults
for any arg the caller omits) makes the documented behavior real.

Fix-R13E-3: Wikidata_SPARQL_query's `max_results` was listed in `required`
even though its own description says "Optional... If not specified, uses
the LIMIT clause" and the Python code already does `arguments.get(...)`
(gracefully handling absence) -- the schema contradicted both the docs and
the implementation.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ENTITY_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src/tooluniverse/data/wikidata_entity_tools.json"
)
SPARQL_CONFIG_PATH = (
    Path(__file__).parent.parent.parent
    / "src/tooluniverse/data/wikidata_sparql_tools.json"
)


def test_search_entities_language_has_en_default():
    configs = json.loads(ENTITY_CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "Wikidata_search_entities")
    assert config["parameter"]["properties"]["language"]["default"] == "en"


def test_search_entities_language_default_is_applied_to_request(monkeypatch):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from tooluniverse.base_rest_tool import BaseRESTTool

    configs = json.loads(ENTITY_CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "Wikidata_search_entities")
    tool = BaseRESTTool(config)

    params = tool._build_params({"search": "Zea mays"})
    assert params["language"] == "en"


def test_sparql_query_max_results_not_required():
    configs = json.loads(SPARQL_CONFIG_PATH.read_text())
    config = next(c for c in configs if c["name"] == "Wikidata_SPARQL_query")
    assert "max_results" not in config["parameter"]["required"]
    assert "sparql" in config["parameter"]["required"]


def test_sparql_query_runs_without_max_results(monkeypatch):
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))
    from tooluniverse.wikidata_sparql_tool import WikidataSPARQLTool

    class _FakeResponse:
        status_code = 200

        def raise_for_status(self):
            pass

        def json(self):
            return {
                "results": {
                    "bindings": [{"item": {"value": "Zea mays"}}]
                }
            }

    def fake_get(url, **kwargs):
        return _FakeResponse()

    monkeypatch.setattr("tooluniverse.wikidata_sparql_tool.requests.get", fake_get)

    tool = WikidataSPARQLTool({"name": "Wikidata_SPARQL_query"})
    result = tool.run({"sparql": "SELECT ?item WHERE { wd:Q11575 wdt:P225 ?item }"})
    assert result == [{"item": "Zea mays"}]
