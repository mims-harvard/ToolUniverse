"""NCATSTranslator_query_associations posts to Aragorn on Translator's Shepherd.

The tool posted to https://aragorn.transltr.io/aragorn/query, which now answers
every path, GET or POST, with an nginx 404, so every call returned
"Translator returned HTTP 404". The SmartAPI registry lists Aragorn's production
server as https://shepherd.transltr.io/aragorn (x-maturity: production), which
speaks TRAPI 1.6. Measured 2026-11-24 with the tool's first example (MONDO:0004975,
treats, ChemicalEntity): old host 404, Shepherd 200 with 85 results.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ncats_translator_tool import NCATSTranslatorTool

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"
SHEPHERD_ARAGORN = "https://shepherd.transltr.io/aragorn/query"


def _tool():
    configs = json.loads((DATA / "ncats_translator_tools.json").read_text("utf-8"))
    config = next(
        c for c in configs if c["name"] == "NCATSTranslator_query_associations"
    )
    return NCATSTranslatorTool(config), config["test_examples"][0]


# One result as Shepherd's Aragorn returned it, trimmed to the fields the tool reads.
SHEPHERD_RESPONSE = {
    "message": {
        "results": [
            {
                "node_bindings": {
                    "n0": [{"id": "MONDO:0004975", "attributes": []}],
                    "n1": [{"id": "CHEBI:145499", "attributes": []}],
                },
                "analyses": [
                    {
                        "resource_id": "infores:shepherd-aragorn",
                        "edge_bindings": {"e0": [{"id": "e1", "attributes": []}]},
                        "support_graphs": ["OMNICORP_support_graph_22"],
                        "score": 0.999999996260506,
                    }
                ],
            }
        ],
        "knowledge_graph": {
            "nodes": {
                "CHEBI:145499": {
                    "name": "Donepezil",
                    "categories": ["biolink:ChemicalEntity", "biolink:Drug"],
                }
            },
            "edges": {
                "e1": {
                    "subject": "CHEBI:145499",
                    "object": "MONDO:0004975",
                    "predicate": "biolink:treats",
                    "sources": [
                        {
                            "resource_id": "infores:multiomics-clinicaltrials",
                            "resource_role": "primary_knowledge_source",
                        },
                        {
                            "resource_id": "infores:shepherd-aragorn",
                            "resource_role": "aggregator_knowledge_source",
                        },
                    ],
                    "attributes": [],
                }
            },
        },
    },
    "logs": [],
}


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_query_associations_posts_to_shepherd():
    tool, example = _tool()
    with patch(
        "tooluniverse.ncats_translator_tool.requests.post",
        return_value=_response(SHEPHERD_RESPONSE),
    ) as post:
        tool.run(example)

    assert post.call_args.args[0] == SHEPHERD_ARAGORN


def test_a_shepherd_response_parses_into_rows():
    tool, example = _tool()
    with patch(
        "tooluniverse.ncats_translator_tool.requests.post",
        return_value=_response(SHEPHERD_RESPONSE),
    ):
        result = tool.run(example)

    assert result["status"] == "success"
    assert result["data"] == [
        {
            "id": "CHEBI:145499",
            "name": "Donepezil",
            "categories": ["biolink:ChemicalEntity", "biolink:Drug"],
            "score": 0.999999996260506,
            "knowledge_sources": ["infores:multiomics-clinicaltrials"],
            "publication_count": 0,
        }
    ]


@pytest.mark.network
def test_live_query_returns_rows():
    tool, example = _tool()
    result = tool.run(example)

    assert result["status"] == "success", result
    assert result["data"]
