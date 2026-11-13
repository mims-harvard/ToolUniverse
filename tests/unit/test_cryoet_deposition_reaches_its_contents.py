"""A deposition must be reachable from, and must name, what it bundles.

arXiv 2609.26836 reports CryoET_list_depositions not exposing a deposition's
datasets. Measured live 2026-11-12, the GraphQL `Deposition` type has 28
fields; the query asked for nine scalars and none of the eight connections
(`datasets`, `annotations`, `tomograms`, `tiltseries`, `frames`,
`alignments`, `authors`, `depositionTypes`). The tool's own description calls
a deposition "the top-level submission unit that bundles a set of datasets,
runs, tomograms, and annotations" and "the natural entry point for browsing
what has been submitted", and nothing in the catalogue could reach that
bundle: CryoET_list_datasets filtered on organism and tissue only, and its
rows did not carry `depositionId` either, so the hierarchy was severed in
both directions.

Deposition 10000 ("DeePiCt Training and Evaluation Datasets") holds 3
datasets, 175 annotations, 23 tomograms, 23 tiltseries, 1,199 frames and 23
alignments, by 13 authors.
"""

import json
from pathlib import Path

import pytest

from tooluniverse.cryoet_tool import CryoETTool

pytestmark = pytest.mark.unit

CONFIG = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "cryoet_tools.json"
)
SOURCE = (
    Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "cryoet_tool.py"
).read_text()


def _config(name):
    for tool in json.loads(CONFIG.read_text()):
        if tool.get("name") == name:
            return tool
    raise AssertionError(f"{name} is not in {CONFIG}")


RAW = {
    "id": 10000,
    "title": "DeePiCt Training and Evaluation Datasets",
    "tag": None,
    "depositionTypes": {
        "edges": [{"node": {"type": "dataset"}}, {"node": {"type": "annotation"}}]
    },
    "authors": {
        "edges": [
            {"node": {"name": "Irene de Teresa Trueba", "primaryAuthorStatus": True}},
            {"node": {"name": "Sara Goetz", "primaryAuthorStatus": None}},
        ]
    },
    "datasetsAggregate": {"aggregate": [{"count": 3}]},
    "annotationsAggregate": {"aggregate": [{"count": 175}]},
    "tomogramsAggregate": {"aggregate": [{"count": 23}]},
    "tiltseriesAggregate": {"aggregate": [{"count": 23}]},
    "framesAggregate": {"aggregate": [{"count": 1199}]},
    # An aggregate with nothing to count is an empty list upstream, not a row
    # holding zero. Deposition 10014 answers this for annotations.
    "alignmentsAggregate": {"aggregate": []},
    "datasets": {"edges": [{"node": {"id": 10002, "title": "RPE1 cytosol"}}]},
}


def test_the_bundle_is_counted_and_the_connections_are_flattened():
    row = CryoETTool._shape_deposition(RAW)
    assert row["contents"] == {
        "datasets": 3,
        "annotations": 175,
        "tomograms": 23,
        "tiltseries": 23,
        "frames": 1199,
        "alignments": 0,
    }
    assert row["depositionTypes"] == ["dataset", "annotation"]
    assert [a["name"] for a in row["authors"]] == [
        "Irene de Teresa Trueba",
        "Sara Goetz",
    ]
    assert row["datasets"] == [{"id": 10002, "title": "RPE1 cytosol"}]
    # No connection envelope survives into the row.
    for value in row.values():
        assert not (isinstance(value, dict) and "edges" in value)


def test_a_truncated_dataset_list_says_so_and_says_where_the_rest_are():
    row = CryoETTool._shape_deposition(RAW)
    assert row["datasets_returned"] == 1
    assert row["datasets_total"] == 3
    assert "1 of 3" in row["datasets_note"]
    assert "deposition_id=10000" in row["datasets_note"]


def test_a_complete_dataset_list_carries_no_truncation_note():
    raw = dict(RAW, datasetsAggregate={"aggregate": [{"count": 1}]})
    row = CryoETTool._shape_deposition(raw)
    assert row["datasets_total"] == 1
    assert "datasets_note" not in row


def test_an_empty_aggregate_is_zero_not_unknown():
    assert (
        CryoETTool._aggregate_count({"xAggregate": {"aggregate": []}}, "xAggregate")
        == 0
    )
    assert CryoETTool._aggregate_count({}, "xAggregate") == 0


def test_the_deposition_query_asks_for_every_connection():
    block = SOURCE.split("def _list_depositions", 1)[1]
    for connection in (
        "datasetsAggregate",
        "annotationsAggregate",
        "tomogramsAggregate",
        "tiltseriesAggregate",
        "framesAggregate",
        "alignmentsAggregate",
        "depositionTypes",
        "authors(",
        "datasets(first:",
    ):
        assert connection in block, connection


def test_datasets_can_be_listed_by_deposition_and_carry_the_join_key():
    config = _config("CryoET_list_datasets")
    assert "deposition_id" in config["parameter"]["properties"]
    row = config["return_schema"]["oneOf"][0]["properties"]["datasets"]["items"]
    assert "depositionId" in row["properties"]
    block = SOURCE.split("def _list_datasets", 1)[1].split("def _get_dataset", 1)[0]
    assert "depositionId: {{_eq: {int(deposition_id)}}}" in block
    assert "depositionId" in block


def test_the_deposition_schema_declares_what_the_row_now_holds():
    config = _config("CryoET_list_depositions")
    props = config["return_schema"]["oneOf"][0]["properties"]["depositions"]["items"][
        "properties"
    ]
    for field in (
        "contents",
        "authors",
        "depositionTypes",
        "datasets",
        "datasets_total",
    ):
        assert field in props, field
