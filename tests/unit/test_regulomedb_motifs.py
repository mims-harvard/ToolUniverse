"""RegulomeDB motif summarisation.

`features` only reports booleans (`PWM: true`), so "how many motifs are
annotated here" was unanswerable from the tool's output. RegulomeDB records a
motif hit under two methods -- "PWMs" and "footprints" -- and its Motifs tab
lists the union, one row per target label.

These tests drive `_summarize_motifs` directly with a fixture shaped like the
live `@graph`, so they assert the counting rule without needing the network.
"""

from tooluniverse.regulomedb_tool import RegulomeDBRESTTool


def _row(method, target, start=100):
    return {
        "method": method,
        "target_label": target,
        "chrom": "chr10",
        "start": start,
        "end": start + 10,
        "strand": "+",
    }


# Shape of the real rs17583618 response: 7 PWM rows and 91 footprint rows whose
# target labels overlap, leaving 8 distinct motifs.
RS17583618 = (
    [
        _row("PWMs", t)
        for t in [
            "NFATC2",
            "STAT1",
            "STAT3",
            "STAT4",
            "STAT5A",
            "STAT5A, STAT5B",
            "STAT5B",
        ]
    ]
    + [
        _row("footprints", t)
        for t in [
            "BCL6B",
            "STAT1",
            "STAT3",
            "STAT4",
            "STAT5A",
            "STAT5A, STAT5B",
            "STAT5B",
        ]
    ]
    + [_row("chromatin state", "irrelevant") for _ in range(833)]
    + [_row("eQTLs", "irrelevant") for _ in range(4)]
)


def test_counts_union_of_pwm_and_footprint_targets():
    out = RegulomeDBRESTTool._summarize_motifs(RS17583618)
    # PWM rows alone give 7 -- the count that made this item wrong.
    assert out["motif_count"] == 8
    assert [m["target_label"] for m in out["motifs"]] == [
        "BCL6B",
        "NFATC2",
        "STAT1",
        "STAT3",
        "STAT4",
        "STAT5A",
        "STAT5A, STAT5B",
        "STAT5B",
    ]


def test_combined_label_counts_once():
    """RegulomeDB shows a matrix shared by two factors as a single row."""
    out = RegulomeDBRESTTool._summarize_motifs([_row("PWMs", "STAT5A, STAT5B")])
    assert out["motif_count"] == 1
    assert out["motifs"][0]["target_label"] == "STAT5A, STAT5B"


def test_reports_both_methods_and_record_counts():
    out = RegulomeDBRESTTool._summarize_motifs(
        [
            _row("PWMs", "STAT1"),
            _row("footprints", "STAT1", 200),
            _row("footprints", "BCL6B"),
        ]
    )
    by = {m["target_label"]: m for m in out["motifs"]}
    assert by["STAT1"]["methods"] == ["PWMs", "footprints"]
    assert by["STAT1"]["n_records"] == 2
    assert by["BCL6B"]["methods"] == ["footprints"]
    assert out["motif_records"] == 3


def test_non_motif_methods_are_excluded():
    out = RegulomeDBRESTTool._summarize_motifs(
        [
            _row("chromatin state", "X"),
            _row("ATAC-seq", "Y"),
            _row("Histone ChIP-seq", "Z"),
        ]
    )
    assert out["motif_count"] == 0
    assert out["motifs"] == []


def test_empty_and_missing_graph_are_safe():
    """A variant with no motif evidence (e.g. RegulomeDB rank 1f) is not an error."""
    for graph in ([], None):
        out = RegulomeDBRESTTool._summarize_motifs(graph)
        assert out["motif_count"] == 0
        assert out["motif_records"] == 0
