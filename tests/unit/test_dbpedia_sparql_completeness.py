from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.dbpedia_tool import DBpediaSPARQLTool


pytestmark = pytest.mark.unit


def _tool():
    return DBpediaSPARQLTool({"name": "DBpedia_SPARQL_query"})


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    return response


def _select_payload(count):
    return {
        "head": {"vars": ["item", "label"]},
        "results": {
            "bindings": [
                {
                    "item": {
                        "type": "uri",
                        "value": f"http://dbpedia.org/resource/{i}",
                    },
                    "label": {
                        "type": "literal",
                        "xml:lang": "en",
                        "value": f"Item {i}",
                    },
                }
                for i in range(count)
            ]
        },
    }


def test_explicit_controls_override_terminal_query_clauses_and_probe_one_extra():
    response = _response(_select_payload(4))
    with patch("tooluniverse.dbpedia_tool.requests.get", return_value=response) as get:
        result = _tool().run(
            {
                "sparql": "SELECT ?item ?label WHERE { ?item ?p ?label } LIMIT 100 OFFSET 9",
                "max_results": 3,
                "offset": 6,
            }
        )
    sent = get.call_args.kwargs["params"]["query"]
    assert sent.endswith("LIMIT 4\nOFFSET 6")
    assert "LIMIT 100" not in sent
    data = result["data"]
    assert data["returned"] == 3
    assert data["has_more"] is True
    assert data["next_offset"] == 9
    assert data["result_set_complete"] is False


def test_word_limit_inside_literal_does_not_disable_page_controls():
    response = _response(_select_payload(0))
    query = 'SELECT ?item WHERE { ?item rdfs:label "unlimited" }'
    with patch("tooluniverse.dbpedia_tool.requests.get", return_value=response) as get:
        _tool().run({"sparql": query, "max_results": 2})
    assert get.call_args.kwargs["params"]["query"].endswith("LIMIT 3\nOFFSET 0")


def test_binding_qualifiers_are_preserved_alongside_normalized_values():
    response = _response(_select_payload(1))
    with patch("tooluniverse.dbpedia_tool.requests.get", return_value=response):
        result = _tool().run(
            {
                "sparql": "SELECT ?item ?label WHERE { ?item ?p ?label }",
                "max_results": 2,
            }
        )
    data = result["data"]
    assert data["results"][0]["label"] == "Item 0"
    assert data["bindings"][0]["item"]["type"] == "uri"
    assert data["bindings"][0]["label"]["xml:lang"] == "en"
    assert result["metadata"]["qualifiers_preserved"] is True
    assert result["metadata"]["pagination_stability_guaranteed"] is False
    assert data["total_count"] == 1


def test_ask_boolean_is_not_silently_returned_as_an_empty_list():
    response = _response({"head": {}, "boolean": True})
    with patch("tooluniverse.dbpedia_tool.requests.get", return_value=response):
        result = _tool().run({"sparql": "ASK WHERE { dbr:Berlin a dbo:Place }"})
    assert result == {
        "status": "success",
        "data": {"query_type": "ASK", "boolean": True},
        "metadata": {
            "source": "DBpedia SPARQL",
            "requested_scope_complete": True,
        },
    }


@pytest.mark.parametrize(
    "arguments,error",
    [
        ({"sparql": "SELECT * WHERE {?s ?p ?o}", "max_results": True}, "max_results"),
        ({"sparql": "SELECT * WHERE {?s ?p ?o}", "max_results": 0}, "max_results"),
        ({"sparql": "SELECT * WHERE {?s ?p ?o}", "offset": -1}, "offset"),
        ({"sparql": "ASK {?s ?p ?o}", "max_results": 2}, "only to SELECT"),
        ({"sparql": "CONSTRUCT {?s ?p ?o} WHERE {?s ?p ?o}"}, "Only SELECT and ASK"),
    ],
)
def test_invalid_or_unsupported_controls_are_rejected_before_network(arguments, error):
    with patch("tooluniverse.dbpedia_tool.requests.get") as get:
        result = _tool().run(arguments)
    assert result["status"] == "error"
    assert error.lower() in result["error"].lower()
    get.assert_not_called()


def test_malformed_select_envelope_is_explicit():
    response = _response({"results": {"bindings": []}})
    with patch("tooluniverse.dbpedia_tool.requests.get", return_value=response):
        result = _tool().run({"sparql": "SELECT ?s WHERE {?s ?p ?o}"})
    assert result["status"] == "error"
    assert "head.vars" in result["error"]
