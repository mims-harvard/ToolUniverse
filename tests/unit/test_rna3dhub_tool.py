"""RNA 3D Hub tools: representative sets, Motif Atlas groups and the loops of
one structure. HTTP is faked with responses recorded from
rna.bgsu.edu/rna3dhub on 2026-11-25 (tests/fixtures/rna3dhub/README.md)."""

import json
import random
from pathlib import Path

import pytest
import requests

from tooluniverse import rna3dhub_tool as R

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "rna3dhub"
CONFIGS = {
    c["name"]: c
    for c in json.loads(
        (ROOT / "src" / "tooluniverse" / "data" / "rna3dhub_tools.json").read_text()
    )
}

NR_15 = "nrlist/download/current/1.5A/csv"
NR_ALL = "nrlist/download/current/all/csv"
HL = "motifs/release/hl/current/json"


def _text(name):
    return (FIXTURES / name).read_text()


class _Response:
    def __init__(self, text, status=200):
        self.text, self.status_code = text, status

    def json(self):
        return json.loads(self.text)


@pytest.fixture
def http(monkeypatch):
    """Serve recorded bodies by URL path; record every call."""
    routes = {}
    calls = []

    def get(url, timeout=None):
        path = url.replace(R.RNA3DHUB_BASE_URL + "/", "")
        calls.append(path)
        if path not in routes:
            raise AssertionError(f"unexpected GET {path}")
        body, status = routes[path]
        if isinstance(body, Exception):
            raise body
        return _Response(body, status)

    monkeypatch.setattr(R.requests, "get", get)

    def route(path, body, status=200):
        routes[path] = (body, status)

    route.calls = calls
    return route


def _run(name, arguments):
    return R.RNA3DHubTool(CONFIGS[name]).run(arguments)


def test_every_tool_names_its_operation():
    assert set(CONFIGS) == {
        "RNA3DHub_get_representative_set",
        "RNA3DHub_list_motifs",
        "RNA3DHub_get_motif",
        "RNA3DHub_get_structure_loops",
    }
    for config in CONFIGS.values():
        assert config["type"] == "RNA3DHubTool"
        assert config["name"].endswith(config["fields"]["operation"])


# -- representative set ---------------------------------------------------


def test_representative_set_pages_through_the_classes(http):
    http(NR_15, _text("nrlist_current_1.5A.csv"))
    result = _run("RNA3DHub_get_representative_set", {"resolution": "1.5", "limit": 3})
    assert result["status"] == "success"
    meta = result["metadata"]
    assert meta["total_classes"] == meta["matched_classes"] == 164
    assert (meta["returned"], meta["has_more"], meta["next_offset"]) == (3, True, 3)
    row = result["data"][0]
    assert row["class_id"].startswith("NR_1.5_")
    assert row["representative_pdb_id"] == row["representative"].split("|")[0]
    assert "members" not in row and "matched_members" not in row

    last = _run(
        "RNA3DHub_get_representative_set",
        {"resolution": "1.5", "limit": 100, "offset": 100},
    )
    assert last["metadata"]["returned"] == 64
    assert last["metadata"]["has_more"] is False
    assert "next_offset" not in last["metadata"]


def test_representative_set_order_does_not_follow_the_server(http):
    """The server changes the row order between requests; pages must not move."""
    lines = _text("nrlist_current_1.5A.csv").splitlines(keepends=True)
    http(NR_15, "".join(lines))
    first = _run("RNA3DHub_get_representative_set", {"resolution": "1.5"})
    random.Random(7).shuffle(lines)
    http(NR_15, "".join(lines))
    second = _run("RNA3DHub_get_representative_set", {"resolution": "1.5"})
    assert first["data"] == second["data"]
    ids = [row["class_id"] for row in first["data"]]
    assert ids == sorted(ids)


def test_representative_set_finds_the_class_of_a_pdb_entry(http):
    http(NR_15, _text("nrlist_current_1.5A.csv"))
    result = _run(
        "RNA3DHub_get_representative_set",
        {"resolution": 1.5, "pdb_id": "5ebi", "include_members": True},
    )
    assert result["metadata"]["matched_classes"] == 1
    row = result["data"][0]
    assert row["class_id"] == "NR_1.5_06980.2"
    assert row["representative"] == "5EBI|1|E+5EBI|1|F"
    assert row["member_count"] == 4 == len(row["members"])
    assert sorted(row["matched_members"]) == sorted(row["members"])


def test_representative_set_explains_a_pdb_entry_with_no_class(http):
    http(NR_15, _text("nrlist_current_1.5A.csv"))
    result = _run(
        "RNA3DHub_get_representative_set", {"resolution": "1.5A", "pdb_id": "1UBQ"}
    )
    assert result["status"] == "success"
    assert result["data"] == []
    note = result["metadata"]["note"]
    assert "No equivalence class" in note and "resolution='all'" in note


def test_no_class_at_any_resolution_is_an_error(http):
    """With no cutoff and the current release, the Hub does not hold the id."""
    http(NR_ALL, _text("nrlist_current_all.csv"))
    result = _run(
        "RNA3DHub_get_representative_set", {"resolution": "all", "pdb_id": "1UBQ"}
    )
    assert result["status"] == "error"
    assert "holds no RNA structure with the id 1UBQ" in result["error"]
    known = _run(
        "RNA3DHub_get_representative_set", {"resolution": "all", "pdb_id": "7DOL"}
    )
    assert [row["class_id"] for row in known["data"]] == ["NR_all_79034.1"]


def test_invalid_release_is_an_error_not_a_one_row_set(http):
    """HTTP 200 with the text 'Invalid release id' parses as one CSV row."""
    http("nrlist/download/9.99/1.5A/csv", _text("nrlist_invalid_release.txt"))
    result = _run(
        "RNA3DHub_get_representative_set", {"resolution": "1.5", "release": "9.99"}
    )
    assert result["status"] == "error"
    assert "no representative-set release '9.99'" in result["error"]


def test_representative_set_rejects_a_body_that_is_not_the_csv(http):
    http(NR_15, "<html><body>Service temporarily unavailable</body></html>")
    result = _run("RNA3DHub_get_representative_set", {"resolution": "1.5"})
    assert result["status"] == "error"
    assert "unexpected representative set" in result["error"]

    http(NR_15, "")
    assert (
        _run("RNA3DHub_get_representative_set", {"resolution": "1.5"})["status"]
        == "error"
    )


@pytest.mark.parametrize(
    "arguments, text",
    [
        ({"resolution": "7.7"}, "resolution must be one of"),
        ({"resolution": "high"}, "resolution must be one of"),
        ({"release": "latest"}, "release must be 'current'"),
        ({"release": "../4.66"}, "release must be 'current'"),
        ({"pdb_id": "TRNA1"}, "4-character PDB id"),
        ({"limit": 0}, "limit must be between 1 and 500"),
        ({"limit": 501}, "limit must be between 1 and 500"),
        ({"limit": "many"}, "limit must be an integer"),
        ({"offset": -1}, "offset must be 0 or more"),
    ],
)
def test_representative_set_bad_arguments_make_no_request(http, arguments, text):
    result = _run("RNA3DHub_get_representative_set", arguments)
    assert result["status"] == "error"
    assert text in result["error"]
    assert http.calls == []


def test_resolution_forms_reach_the_same_route(http):
    http(NR_15, _text("nrlist_current_1.5A.csv"))
    http(NR_ALL, _text("nrlist_current_all.csv"))
    http("nrlist/download/current/4.0A/csv", _text("nrlist_current_1.5A.csv"))
    for value in ("1.5", "1.5A", 1.5, " 1.5 a "):
        assert (
            _run("RNA3DHub_get_representative_set", {"resolution": value})["status"]
            == "success"
        )
    assert (
        _run("RNA3DHub_get_representative_set", {"resolution": "ALL"})["metadata"][
            "total_classes"
        ]
        == 3
    )
    default = _run("RNA3DHub_get_representative_set", {})
    assert default["metadata"]["resolution"] == "4.0"
    assert http.calls == [NR_15] * 4 + [NR_ALL, "nrlist/download/current/4.0A/csv"]


# -- motif atlas ----------------------------------------------------------


def test_list_motifs_counts_the_loop_annotations(http):
    http(HL, _text("motifs_hl_current.json"))
    result = _run("RNA3DHub_list_motifs", {"loop_type": "HL"})
    assert result["status"] == "success"
    assert result["metadata"]["total_motifs"] == 6
    assert result["metadata"]["loop_type_name"] == "hairpin loop"
    sizes = [row["num_instances"] for row in result["data"]]
    assert sizes == sorted(sizes, reverse=True)
    by_id = {row["motif_id"]: row for row in result["data"]}
    gnra = by_id["HL_27656.2"]
    assert gnra["instance_annotations"] == {
        "GNRA-like with tWH": 2,
        "GNRA-like with tWH (H)": 1,
    }
    assert gnra["common_name"] is None and gnra["num_instances"] == 6
    assert "alignment" not in gnra
    assert by_id["HL_00317.1"]["instance_annotations"] == {}


def test_list_motifs_query_reads_ids_and_annotations_not_signatures(http):
    http(HL, _text("motifs_hl_current.json"))
    hits = _run("RNA3DHub_list_motifs", {"loop_type": "hl", "query": "uncg"})
    assert [row["motif_id"] for row in hits["data"]] == ["HL_89199.3"]
    by_id = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "query": "HL_00317"})
    assert by_id["metadata"]["matched_motifs"] == 1
    # every group has cWW in its base-pair signature
    none = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "query": "cWW"})
    assert none["data"] == []
    assert "matches the filters" in none["metadata"]["note"]


def test_list_motifs_min_instances_and_paging(http):
    http(HL, _text("motifs_hl_current.json"))
    big = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "min_instances": 5})
    assert big["metadata"]["matched_motifs"] == 4
    assert (
        _run("RNA3DHub_list_motifs", {"loop_type": "HL"})["metadata"]["matched_motifs"]
        == 6
    )
    page = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "limit": 2, "offset": 4})
    assert page["metadata"]["returned"] == 2
    assert page["metadata"]["has_more"] is False


def test_list_motifs_keeps_groups_without_loops_by_default(http):
    """Release 1.0 has 13 HL groups with no loop; none is dropped silently."""
    http("motifs/release/hl/1.0/json", _text("motifs_hl_1.0_with_empty_group.json"))
    every = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "release": "1.0"})
    assert every["status"] == "success"
    assert every["metadata"]["matched_motifs"] == 2
    empty = next(r for r in every["data"] if r["motif_id"] == "HL_00721.1")
    assert empty["num_instances"] == 0 and empty["instance_annotations"] == {}
    some = _run(
        "RNA3DHub_list_motifs",
        {"loop_type": "HL", "release": "1.0", "min_instances": 1},
    )
    assert [r["motif_id"] for r in some["data"]] == ["HL_00090.1"]


def test_list_motifs_unknown_release_passes_the_message_not_the_trace(http):
    http("motifs/release/hl/9.99/json", _text("motifs_release_404.json"), 404)
    result = _run("RNA3DHub_list_motifs", {"loop_type": "HL", "release": "9.99"})
    assert result == {
        "status": "error",
        "error": "RNA 3D Hub returned HTTP 404: Motif atlas release not found",
    }


@pytest.mark.parametrize(
    "arguments, text",
    [
        ({}, "loop_type is required"),
        ({"loop_type": "J8"}, "loop_type must be one of"),
        ({"loop_type": "hairpin"}, "loop_type must be one of"),
        ({"loop_type": "HL", "min_instances": -1}, "min_instances must be 0 or more"),
        ({"loop_type": "HL", "limit": 501}, "limit must be between 1 and 500"),
    ],
)
def test_list_motifs_bad_arguments(http, arguments, text):
    result = _run("RNA3DHub_list_motifs", arguments)
    assert result["status"] == "error" and text in result["error"]
    assert http.calls == []


def test_get_motif_returns_aligned_instances(http):
    http("motif/view/IL_03350.3/json", _text("motif_IL_03350.3.json"))
    result = _run("RNA3DHub_get_motif", {"motif_id": "il_03350.3"})
    assert result["status"] == "success"
    data = result["data"]
    assert data["motif_id"] == "IL_03350.3" and data["loop_type"] == "IL"
    assert data["num_instances"] == 3 and data["num_nucleotides"] == 13
    assert data["chainbreak"] == ["9"]
    assert data["instance_annotations"] == {"Reverse kink-turn related": 3}
    assert {i["pdb_id"] for i in data["instances"]} == {"4PHY", "5CNR", "4P97"}
    loop = next(i for i in data["instances"] if i["loop_id"] == "IL_4PHY_005")
    assert loop["unit_ids"][0] == "4PHY|1|A|C|5"
    assert loop["unit_ids"][9] == "4PHY|1|B|G|38"  # position 10: second strand
    assert loop["sequence"] == "CUCCCCACCGAGG"
    assert loop["chains"] == ["A", "B"]
    assert loop["annotation"] == "Reverse kink-turn related"
    assert all(len(i["unit_ids"]) == 13 for i in data["instances"])
    assert result["metadata"]["total_instances"] == 3


def test_get_motif_pages_the_instances(http):
    http("motif/view/IL_03350.3/json", _text("motif_IL_03350.3.json"))
    result = _run("RNA3DHub_get_motif", {"motif_id": "IL_03350.3", "limit": 2})
    assert len(result["data"]["instances"]) == 2
    assert result["data"]["num_instances"] == 3
    assert result["metadata"]["has_more"] is True
    assert result["metadata"]["next_offset"] == 2


def test_get_motif_unknown_id_is_the_hub_message(http):
    http("motif/view/HL_99999.9/json", _text("motif_404.json"), 404)
    result = _run("RNA3DHub_get_motif", {"motif_id": "HL_99999.9"})
    assert result == {
        "status": "error",
        "error": "RNA 3D Hub returned HTTP 404: This motif id is invalid.",
    }


@pytest.mark.parametrize("motif_id", ["", "GNRA", "HL_4TNA_001", "HL_27656", "../x"])
def test_get_motif_rejects_a_malformed_id_without_a_request(http, motif_id):
    result = _run("RNA3DHub_get_motif", {"motif_id": motif_id})
    assert result["status"] == "error"
    assert "motif_id" in result["error"]
    assert http.calls == []


# -- loops of one structure -----------------------------------------------


def test_structure_loops_of_trna_phe(http):
    http("loops/download/4TNA", _text("loops_4TNA.csv"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "4tna"})
    assert result["status"] == "success"
    assert result["metadata"]["loop_type_counts"] == {"HL": 4, "J4": 1}
    assert result["metadata"]["total_loops"] == 5
    assert [row["loop_id"] for row in result["data"]] == [
        "HL_4TNA_001",
        "HL_4TNA_002",
        "HL_4TNA_003",
        "HL_4TNA_004",
        "J4_4TNA_001",
    ]
    d_loop = result["data"][0]
    assert d_loop["sequence"] == "CAG(H2U)(H2U)GGGAG"
    assert d_loop["nucleotide_count"] == 10 == len(d_loop["unit_ids"])
    assert d_loop["chains"] == ["A"] and d_loop["model"] == 1
    assert result["metadata"]["model_count"] == 1
    assert "models" not in result["metadata"]["note"]
    assert http.calls == ["loops/download/4TNA"]


def test_structure_loops_filter_keeps_the_counts_of_all_types(http):
    http("loops/download/4TNA", _text("loops_4TNA.csv"))
    junctions = _run(
        "RNA3DHub_get_structure_loops", {"pdb_id": "4TNA", "loop_type": "J4"}
    )
    assert [row["loop_id"] for row in junctions["data"]] == ["J4_4TNA_001"]
    assert junctions["metadata"]["matched_loops"] == 1
    assert junctions["metadata"]["total_loops"] == 5

    internal = _run(
        "RNA3DHub_get_structure_loops", {"pdb_id": "4TNA", "loop_type": "IL"}
    )
    assert internal["status"] == "success" and internal["data"] == []
    assert "4TNA has no internal loop" in internal["metadata"]["note"]
    assert internal["metadata"]["loop_type_counts"] == {"HL": 4, "J4": 1}


def test_an_nmr_entry_says_that_its_loops_repeat_per_model(http):
    """2KZL has 8 models: 40 rows for 1 hairpin loop and 4 internal loops."""
    http("loops/download/2KZL", _text("loops_2KZL.csv"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "2KZL"})
    meta = result["metadata"]
    assert meta["model_count"] == 8
    assert (meta["total_loops"], meta["loop_type_counts"]) == (40, {"HL": 8, "IL": 32})
    assert "2KZL has 8 models" in meta["note"] and "model=1" in meta["note"]
    assert [row["model"] for row in result["data"][:8]] == list(range(1, 9))


def test_model_keeps_the_loops_of_one_model(http):
    http("loops/download/2KZL", _text("loops_2KZL.csv"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "2KZL", "model": 1})
    meta = result["metadata"]
    assert (meta["total_loops"], meta["loop_type_counts"]) == (5, {"HL": 1, "IL": 4})
    assert meta["model"] == 1 and meta["model_count"] == 8
    assert "8 models" not in meta["note"]
    assert {row["model"] for row in result["data"]} == {1}
    assert all(
        u.startswith("2KZL|1|") for row in result["data"] for u in row["unit_ids"]
    )

    http("loops/download/4TNA", _text("loops_4TNA.csv"))
    one_model = _run("RNA3DHub_get_structure_loops", {"pdb_id": "4TNA", "model": 2})
    assert one_model["error"].endswith("Its loops are in model 1 only.")

    missing = _run("RNA3DHub_get_structure_loops", {"pdb_id": "2KZL", "model": 9})
    assert missing["status"] == "error"
    assert "2KZL has no model 9" in missing["error"]
    assert "models 1 to 8" in missing["error"]

    bad = _run("RNA3DHub_get_structure_loops", {"pdb_id": "2KZL", "model": 0})
    assert bad["status"] == "error" and "model must be 1 or more" in bad["error"]


def test_no_loops_for_a_known_rna_is_an_explained_empty_list(http):
    """7DOL is in the representative set, so 'No loops found' is a real answer."""
    http("loops/download/7DOL", _text("loops_none.txt"))
    http(NR_ALL, _text("nrlist_current_all.csv"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "7DOL"})
    assert result["status"] == "success"
    assert result["data"] == []
    assert result["metadata"]["total_loops"] == 0
    assert "is an RNA structure in RNA 3D Hub" in result["metadata"]["note"]
    assert http.calls == ["loops/download/7DOL", NR_ALL]


def test_no_loops_for_an_id_the_hub_does_not_hold_is_an_error(http):
    """The same HTTP 200 body comes back for a protein entry and a wrong id."""
    http("loops/download/1UBQ", _text("loops_none.txt"))
    http(NR_ALL, _text("nrlist_current_all.csv"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "1UBQ"})
    assert result["status"] == "error"
    assert "holds no RNA structure with the id 1UBQ" in result["error"]


def test_no_loops_says_so_when_the_second_check_fails(http):
    http("loops/download/7DOL", _text("loops_none.txt"))
    http(NR_ALL, requests.exceptions.ConnectionError("down"))
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "7DOL"})
    assert result["status"] == "error"
    assert "No loops found" in result["error"]
    assert "the check that tells them apart failed" in result["error"]


def test_structure_loops_rejects_a_body_that_is_not_the_csv(http):
    http("loops/download/4TNA", "<html>Service temporarily unavailable</html>")
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "4TNA"})
    assert result["status"] == "error"
    assert "unexpected loop list for 4TNA" in result["error"]


@pytest.mark.parametrize("pdb_id", [None, "", "tRNA", "4TNA/../x", "12345"])
def test_structure_loops_rejects_a_malformed_pdb_id(http, pdb_id):
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": pdb_id})
    assert result["status"] == "error" and "pdb_id" in result["error"]
    assert http.calls == []


# -- transport ------------------------------------------------------------


@pytest.mark.parametrize(
    "failure, text",
    [
        (requests.exceptions.Timeout("slow"), "timed out after 60s"),
        (requests.exceptions.ConnectionError("down"), "Failed to connect"),
        (RuntimeError("boom"), "Error querying RNA 3D Hub: boom"),
    ],
)
def test_transport_failures_are_errors(http, failure, text):
    http("loops/download/4TNA", failure)
    result = _run("RNA3DHub_get_structure_loops", {"pdb_id": "4TNA"})
    assert result["status"] == "error" and text in result["error"]


def test_http_500_without_json_is_an_error(http):
    http(HL, "<html>R3DMCS error page</html>", 500)
    result = _run("RNA3DHub_list_motifs", {"loop_type": "HL"})
    assert result == {"status": "error", "error": "RNA 3D Hub returned HTTP 500"}


def test_http_200_with_html_instead_of_json_is_an_error(http):
    http(HL, "<html>maintenance</html>")
    result = _run("RNA3DHub_list_motifs", {"loop_type": "HL"})
    assert result["status"] == "error"
    assert "not valid JSON" in result["error"]


def test_run_accepts_none_and_reports_an_unknown_operation():
    assert R.RNA3DHubTool(CONFIGS["RNA3DHub_get_motif"]).run(None)["status"] == "error"
    config = dict(CONFIGS["RNA3DHub_get_motif"], fields={"operation": "nope"})
    assert R.RNA3DHubTool(config).run({}) == {
        "status": "error",
        "error": "Unknown operation: nope",
    }
