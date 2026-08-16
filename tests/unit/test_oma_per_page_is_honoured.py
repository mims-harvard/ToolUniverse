"""Regression tests: OMA's declared paging parameters must do what they say.

``oma_tools.json`` declares every paging parameter as ``["integer", "null"]``,
and ``OMATool`` then compared the value against a bound with ``min(value, 100)``.
``null`` is therefore a legal argument that raised ``TypeError: '<' not supported
between instances of 'int' and 'NoneType'``, reaching the caller as an opaque
"Unexpected error querying OMA" that named neither the parameter nor the cause.
Confirmed live on all three nullable sites: ``OMA_get_orthologs``,
``OMA_resolve_xref`` and ``OMA_get_genome_pair_orthologs``.

Separately, ``OMA_get_orthologs`` forwarded ``per_page`` to
``/protein/{id}/orthologs/``, which accepts it, returns HTTP 200 and ignores it.
Measured against P04637: ``per_page`` of 3, 20 and 100 each returned all 157
orthologs, and no Link, X-Total-Count or content-range header came back to page
with. A caller asking for 3 received 157 while the schema promised 20.

The sibling endpoint ``/pairs/{g1}/{g2}/`` *does* honour ``per_page`` (measured:
3 -> 3 rows, 20 -> 20 rows, each with a Link header), so the defect is one
endpoint's, not the module's, and that tool must keep forwarding the parameter.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tooluniverse.oma_tool import OMATool, _page_size

pytestmark = pytest.mark.unit

CONFIG_PATH = (
    Path(__file__).parent.parent.parent / "src/tooluniverse/data/oma_tools.json"
)
CONFIGS = {c["name"]: c for c in json.loads(CONFIG_PATH.read_text())}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _tool(name):
    return OMATool(dict(CONFIGS[name]))


def _orthologs(n):
    return [
        {
            "omaid": f"OMA{i}",
            "canonicalid": f"C{i}",
            "species": {"species": f"Species {i}", "code": f"S{i}", "taxon_id": i},
            "rel_type": "1:1",
            "distance": 1.0,
            "score": 1.0,
            "sequence_length": 100,
            "chromosome": "1",
        }
        for i in range(n)
    ]


# ---------------------------------------------------------------------------
# null is a declared value for every paging parameter, so it must not raise
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "name,endpoint,args",
    [
        ("OMA_get_orthologs", "orthologs", {"protein_id": "P04637", "per_page": None}),
        ("OMA_resolve_xref", "xref", {"search": "TP53", "limit": None}),
        (
            "OMA_get_genome_pair_orthologs",
            "genome_pairs",
            {"genome1": "HUMAN", "genome2": "MOUSE", "per_page": None},
        ),
    ],
)
def test_null_paging_parameter_is_not_an_error(name, endpoint, args):
    assert (
        "null"
        in CONFIGS[name]["parameter"]["properties"][
            "per_page" if "per_page" in args else "limit"
        ]["type"]
    ), f"{name} declares the parameter nullable"

    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(5))
        result = _tool(name).run(args)

    assert result["status"] == "success", result.get("error")


def test_page_size_treats_absent_and_null_alike():
    assert _page_size(None, 20) == 20
    assert _page_size(None, 25) == 25


def test_page_size_clamps_and_survives_junk():
    assert _page_size(500, 20) == 100, "the declared cap still applies"
    assert _page_size(0, 20) == 1, "a page of zero rows is never what was meant"
    assert _page_size(-4, 20) == 1
    assert _page_size("7", 20) == 7, "CLI arguments arrive as strings"
    assert _page_size("abc", 20) == 20, "unparseable falls back to the default"


def test_page_size_can_be_uncapped():
    """Orthologs has no server-side paging, so a cap would strand the tail."""
    assert _page_size(500, 20, maximum=None) == 500


# ---------------------------------------------------------------------------
# OMA_get_orthologs: the limit is applied here, because upstream ignores it
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("per_page", [3, 20, 100])
def test_orthologs_returns_the_number_requested(per_page):
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        result = _tool("OMA_get_orthologs").run(
            {"protein_id": "P04637", "per_page": per_page}
        )

    assert len(result["data"]) == per_page
    assert result["metadata"]["count"] == per_page
    assert result["metadata"]["total_count"] == 157
    assert result["metadata"]["truncated"] is True


def test_orthologs_does_not_forward_per_page_upstream():
    """Sending it implied a limit that was never applied."""
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        _tool("OMA_get_orthologs").run({"protein_id": "P04637", "per_page": 3})

    assert "per_page" not in get.call_args.kwargs["params"]


def test_orthologs_still_forwards_rel_type():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(4))
        _tool("OMA_get_orthologs").run({"protein_id": "P04637", "rel_type": "1:1"})

    assert get.call_args.kwargs["params"]["rel_type"] == "1:1"


def test_orthologs_default_is_the_documented_twenty():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        result = _tool("OMA_get_orthologs").run({"protein_id": "P04637"})

    assert result["metadata"]["count"] == 20


def test_orthologs_note_names_the_total_and_a_reachable_request():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        result = _tool("OMA_get_orthologs").run({"protein_id": "P04637", "per_page": 3})

    note = result["metadata"]["truncation_note"]
    assert "157" in note
    assert "per_page=157" in note, "the advice must be a request that works"


def test_orthologs_can_return_everything():
    """No cap: asking for the full set must actually yield the full set."""
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        result = _tool("OMA_get_orthologs").run(
            {"protein_id": "P04637", "per_page": 157}
        )

    assert len(result["data"]) == 157
    assert result["metadata"]["truncated"] is False
    assert "truncation_note" not in result["metadata"]


def test_orthologs_no_note_when_nothing_was_withheld():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(4))
        result = _tool("OMA_get_orthologs").run({"protein_id": "P04637"})

    assert result["metadata"]["truncated"] is False
    assert "truncation_note" not in result["metadata"]
    assert result["metadata"]["count"] == 4
    assert result["metadata"]["total_count"] == 4


def test_orthologs_empty_result_reports_zero():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse([])
        result = _tool("OMA_get_orthologs").run({"protein_id": "P04637"})

    assert result["data"] == []
    assert result["metadata"]["count"] == 0
    assert result["metadata"]["total_count"] == 0
    assert result["metadata"]["truncated"] is False


def test_total_orthologs_is_gone_rather_than_redefined():
    """It meant "rows returned"; keeping it as the total would flip its meaning."""
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(_orthologs(157))
        result = _tool("OMA_get_orthologs").run({"protein_id": "P04637", "per_page": 3})

    assert "total_orthologs" not in result["metadata"]


# ---------------------------------------------------------------------------
# The endpoint that already paged correctly must not move
# ---------------------------------------------------------------------------


def test_genome_pairs_still_forwards_per_page_upstream():
    """/pairs/ honours per_page server-side; slicing here would be wrong."""
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse([])
        _tool("OMA_get_genome_pair_orthologs").run(
            {"genome1": "HUMAN", "genome2": "MOUSE", "per_page": 3}
        )

    assert get.call_args.kwargs["params"]["per_page"] == 3


def test_genome_pairs_still_forwards_page():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse([])
        _tool("OMA_get_genome_pair_orthologs").run(
            {"genome1": "HUMAN", "genome2": "MOUSE", "page": 2}
        )

    assert get.call_args.kwargs["params"]["page"] == 2


def test_xref_limit_still_slices():
    with patch("tooluniverse.oma_tool.requests.get") as get:
        get.return_value = _FakeResponse(
            [{"xref": f"X{i}", "genome": {}} for i in range(50)]
        )
        result = _tool("OMA_resolve_xref").run({"search": "TP53", "limit": 5})

    assert len(result["data"]) == 5
    assert result["metadata"]["total_matches"] == 50


# ---------------------------------------------------------------------------
# Config: what the tool promises must match what it now does
# ---------------------------------------------------------------------------


def test_orthologs_description_documents_the_total():
    description = CONFIGS["OMA_get_orthologs"]["description"]
    assert "total_count" in description
    assert "count" in description


def test_orthologs_per_page_no_longer_advertises_a_maximum():
    """The old "max: 100" was never enforced anywhere and is now untrue."""
    description = CONFIGS["OMA_get_orthologs"]["parameter"]["properties"]["per_page"][
        "description"
    ]
    assert "max: 100" not in description


def test_return_schema_still_describes_the_inner_payload():
    """Issue #246 convention: return_schema describes `data`, not the envelope."""
    schema = CONFIGS["OMA_get_orthologs"]["return_schema"]
    assert "total_count" not in json.dumps(schema)
    assert schema["oneOf"][0]["type"] == "array"


def test_test_examples_stay_within_what_the_tool_accepts():
    for example in CONFIGS["OMA_get_orthologs"]["test_examples"]:
        assert example["per_page"] >= 1
