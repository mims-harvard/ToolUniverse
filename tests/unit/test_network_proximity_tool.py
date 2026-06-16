"""Unit tests for the network-proximity tool (networkx, pure local compute).

The tool implements the Guney/Barabasi (2016) and Menche (2015) set-distance
measures with a degree-matched random Z-score over a user-supplied graph. Tests
pin the distance math on a hand-checkable graph, the three measures, determinism
under a fixed seed, domain-neutral set_a/set_b vs the targets/disease_genes
aliases, missing-node handling, and error paths. networkx + numpy are core deps,
so no skip guard is needed.
"""

import csv

import pytest

from tooluniverse.network_proximity_tool import NetworkProximityTool

pytestmark = pytest.mark.unit

# A-B-C-D-E chain plus shortcuts; F-G hang off the side.
EDGES = [
    ["A", "B"], ["B", "C"], ["C", "D"], ["D", "E"],
    ["A", "C"], ["B", "D"], ["E", "F"], ["F", "G"], ["A", "F"], ["C", "G"],
]


def _tool():
    return NetworkProximityTool(
        {"name": "np", "type": "NetworkProximityTool",
         "parameter": {"type": "object", "properties": {}}}
    )


def test_closest_measure_matches_hand_calc():
    """closest = mean over set_a of min shortest-path to any set_b node."""
    # A->{D,E}: min path length 2; B->{D,E}: B-D = 1. mean(2,1) = 1.5.
    out = _tool().run(
        {"edges": EDGES, "set_a": ["A", "B"], "set_b": ["D", "E"],
         "measure": "closest", "n_rand": 100, "seed": 1}
    )
    assert out["status"] == "success"
    assert out["data"]["measure"] == "closest"
    assert out["data"]["value"] == 1.5
    assert out["data"]["n_set_a_in_network"] == 2
    assert out["data"]["n_set_b_in_network"] == 2


def test_pharmacology_aliases_work():
    """targets/disease_genes are accepted as aliases for set_a/set_b."""
    out = _tool().run(
        {"edges": EDGES, "targets": ["A", "B"], "disease_genes": ["D", "E"],
         "n_rand": 50, "seed": 1}
    )
    assert out["status"] == "success"
    assert out["data"]["value"] == 1.5


def test_separation_measure_runs_and_is_signed():
    """separation returns a finite (possibly negative) s_AB value."""
    out = _tool().run(
        {"edges": EDGES, "set_a": ["A", "B"], "set_b": ["D", "E"],
         "measure": "separation", "n_rand": 100, "seed": 1}
    )
    assert out["status"] == "success"
    assert out["data"]["measure"] == "separation"
    assert isinstance(out["data"]["value"], float)


def test_shortest_measure_at_least_closest():
    """shortest (all-pairs mean) >= closest (min) for the same sets."""
    c = _tool().run({"edges": EDGES, "set_a": ["A", "B"], "set_b": ["D", "E"],
                     "measure": "closest", "n_rand": 10, "seed": 1})["data"]["value"]
    s = _tool().run({"edges": EDGES, "set_a": ["A", "B"], "set_b": ["D", "E"],
                     "measure": "shortest", "n_rand": 10, "seed": 1})["data"]["value"]
    assert s >= c


def test_deterministic_under_fixed_seed():
    """Same seed -> identical Z-score and p-value."""
    args = {"edges": EDGES, "set_a": ["A", "B"], "set_b": ["D", "E"],
            "n_rand": 200, "seed": 7}
    a = _tool().run(args)["data"]
    b = _tool().run(args)["data"]
    assert a["z_score"] == b["z_score"]
    assert a["p_value"] == b["p_value"]


def test_adjacent_sets_have_distance_one():
    """Directly-connected nodes -> closest distance 1.0."""
    out = _tool().run(
        {"edges": EDGES, "set_a": ["B"], "set_b": ["D"], "n_rand": 50, "seed": 1}
    )
    assert out["data"]["value"] == 1.0


def test_missing_nodes_reported_not_fatal():
    """Nodes absent from the network are dropped and listed, not errored."""
    out = _tool().run(
        {"edges": EDGES, "set_a": ["A", "ZZZ"], "set_b": ["E"], "n_rand": 50, "seed": 1}
    )
    assert out["status"] == "success"
    assert out["data"]["missing_set_a"] == ["ZZZ"]
    assert out["data"]["n_set_a_in_network"] == 1


def test_edgelist_file_input(tmp_path):
    """Network can be loaded from a 2-column edgelist file."""
    p = tmp_path / "net.tsv"
    with open(p, "w", newline="") as fh:
        w = csv.writer(fh, delimiter="\t")
        for u, v in EDGES:
            w.writerow([u, v])
    out = _tool().run(
        {"edgelist_path": str(p), "set_a": ["A", "B"], "set_b": ["D", "E"],
         "n_rand": 50, "seed": 1}
    )
    assert out["status"] == "success"
    assert out["data"]["value"] == 1.5


# --- error paths ----------------------------------------------------------- #
def test_no_network_is_error():
    """Without edges or an edgelist_path the call errors cleanly."""
    out = _tool().run({"set_a": ["A"], "set_b": ["B"]})
    assert out["status"] == "error" and "network" in out["error"].lower()


def test_unknown_measure_is_error():
    """An unrecognized measure is rejected."""
    out = _tool().run(
        {"edges": EDGES, "set_a": ["A"], "set_b": ["E"], "measure": "bogus"}
    )
    assert out["status"] == "error" and "measure" in out["error"]


def test_nodes_absent_from_network_is_error():
    """If no set_a/set_b node exists in the graph, that's an error."""
    out = _tool().run(
        {"edges": EDGES, "set_a": ["XX"], "set_b": ["E"], "n_rand": 10}
    )
    assert out["status"] == "error"


def test_missing_node_sets_is_error():
    """Empty/absent set is rejected."""
    out = _tool().run({"edges": EDGES, "set_a": ["A"]})
    assert out["status"] == "error"
