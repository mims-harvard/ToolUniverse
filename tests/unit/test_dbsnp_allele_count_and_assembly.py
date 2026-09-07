"""Regression guards for the dbSNP "mislabelled number" defects.

Two distinct problems, both of the shape "a number or coordinate whose label
does not match what the source actually provides":

1. dbSNP esummary encodes per-study frequencies as ``allele=frequency/N`` in
   ``global_mafs``. ``N`` is the count of observed ALLELES (chromosomes)
   carrying the allele, not a count of individuals -- but it was surfaced
   under the name ``sample_count``. The arithmetic is decisive: 1000 Genomes
   phase 3 is 2504 samples = 5008 alleles, and 0.1505591 x 5008 = 754 for
   rs429358 while 0.002396 x 5008 = 12 for rs80338939; multiplying by 2504
   instead yields 377 and 6, matching neither token. TOPMED freeze 8 (132,345
   samples = 264,690 alleles) confirms independently: 0.1553138 x 264690 =
   41110. The value is now also emitted as ``allele_count``; ``sample_count``
   is kept, byte-identical, as a legacy alias so no caller breaks.

2. ``position`` carried esummary's ``chrpos`` with no assembly label, while
   ``chrpos_prev_assm`` was discarded entirely. For rs80338939 the two differ
   by ~574 kb (13:20189547 on GRCh38 vs 13:20763686 on GRCh37), so a GRCh37
   pipeline had no way to tell which build it received. ``position`` is
   unchanged; ``assembly``, ``position_grch38`` and ``position_grch37`` are
   added alongside it.

All fixtures below are recorded from live esummary responses.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.dbsnp_tool import dbSNPGetVariantByRsID, dbSNPGetFrequencies

pytestmark = pytest.mark.unit


def _esummary(uid, record):
    return {
        "status": "success",
        "data": {"result": {"uids": [uid], uid: record}},
    }


# Recorded live from esummary.fcgi?db=snp&id=80338939 (GJB2 c.35delG).
RS80338939 = {
    "snp_id": 80338939,
    "chr": "13",
    "chrpos": "13:20189547",
    "chrpos_prev_assm": "13:20763686",
    "allele": "N",
    "snp_class": "delins",
    "clinical_significance": "pathogenic",
    "genes": [{"name": "GJB2"}],
    "global_mafs": [
        {"study": "1000Genomes", "freq": "-=0.002396/12"},
        {"study": "1000Genomes_30X", "freq": "-=0.002342/15"},
        {"study": "TWINSUK", "freq": "-=0.007012/26"},
    ],
    "docsum": "",
    "spdi": "",
    "fxn_class": "frameshift_variant",
    "validated": "by-frequency",
    "createdate": "2009/11/18 16:00",
    "updatedate": "2024/11/01 13:31",
}

# Recorded live from esummary.fcgi?db=snp&id=429358 (APOE).
RS429358 = {
    "snp_id": 429358,
    "chr": "19",
    "chrpos": "19:44908684",
    "chrpos_prev_assm": "19:45411941",
    "allele": "Y",
    "snp_class": "snv",
    "clinical_significance": "risk-factor",
    "genes": [{"name": "APOE"}],
    "global_mafs": [
        {"study": "1000Genomes", "freq": "C=0.1505591/754"},
        {"study": "TOPMED", "freq": "C=0.1553138/41110"},
    ],
    "docsum": "",
    "spdi": "",
    "fxn_class": "missense_variant",
    "validated": "by-cluster",
    "createdate": "2000/09/19 17:02",
    "updatedate": "2024/11/01 13:31",
}


def _frequencies(monkeypatch, uid, record):
    tool = dbSNPGetFrequencies({"name": "dbsnp_get_frequencies"})
    monkeypatch.setattr(
        tool, "_make_request", lambda *a, **k: _esummary(uid, dict(record))
    )
    return tool.run({"rsid": f"rs{uid}"})["data"]["frequencies"]


def _variant(monkeypatch, uid, record):
    tool = dbSNPGetVariantByRsID({"name": "dbsnp_get_variant_by_rsid"})
    monkeypatch.setattr(
        tool, "_make_request", lambda *a, **k: _esummary(uid, dict(record))
    )
    return tool.run({"rsid": f"rs{uid}"})["data"]


# --------------------------------------------------------------------------
# Defect 1: the /N token is an allele count
# --------------------------------------------------------------------------


def test_slash_token_maps_to_allele_count(monkeypatch):
    """The number after the slash lands in `allele_count`."""
    freqs = {f["study"]: f for f in _frequencies(monkeypatch, "80338939", RS80338939)}

    assert freqs["1000Genomes"]["allele_count"] == 12
    assert freqs["1000Genomes_30X"]["allele_count"] == 15
    assert freqs["TWINSUK"]["allele_count"] == 26


def test_sample_count_retained_with_identical_value(monkeypatch):
    """`sample_count` is a legacy alias: still present, still the same number.

    This is the backwards-compatibility guarantee -- renaming the key was not
    an option, so the old name must keep emitting exactly what it always did.
    """
    for uid, record in (("80338939", RS80338939), ("429358", RS429358)):
        for row in _frequencies(monkeypatch, uid, record):
            assert "sample_count" in row, f"{uid}/{row['study']} lost sample_count"
            assert row["sample_count"] == row["allele_count"], (
                f"{uid}/{row['study']}: sample_count diverged from allele_count"
            )


def test_allele_count_is_alleles_not_individuals(monkeypatch):
    """freq x (2 x samples) reproduces the token; freq x samples does not.

    Guards the semantic claim itself, not just the plumbing. If someone later
    "corrects" the parser to halve the token into individuals, this fails.
    """
    # (study, cohort size in individuals) for cohorts with published Ns.
    cohorts = {"1000Genomes": 2504, "1000Genomes_30X": 3202, "TOPMED": 132345}

    for uid, record in (("80338939", RS80338939), ("429358", RS429358)):
        for row in _frequencies(monkeypatch, uid, record):
            n_samples = cohorts.get(row["study"])
            if n_samples is None:
                continue
            as_alleles = row["frequency"] * 2 * n_samples
            as_individuals = row["frequency"] * n_samples
            assert abs(as_alleles - row["allele_count"]) < 1.0, (
                f"{uid}/{row['study']}: token {row['allele_count']} is not "
                f"freq x 2N ({as_alleles:.3f})"
            )
            assert abs(as_individuals - row["allele_count"]) >= 1.0, (
                f"{uid}/{row['study']}: token is also consistent with an "
                "individual count -- fixture no longer discriminates"
            )


def test_malformed_frequency_entries_still_skipped(monkeypatch):
    """Unparseable entries are dropped rather than raising."""
    record = {**RS429358, "global_mafs": [{"study": "Broken", "freq": "C=notanum/12"}]}
    assert _frequencies(monkeypatch, "429358", record) == []


# --------------------------------------------------------------------------
# Defect 2: assembly label and previous-assembly coordinate
# --------------------------------------------------------------------------


def test_assembly_label_present(monkeypatch):
    data = _variant(monkeypatch, "80338939", RS80338939)
    assert data["assembly"] == "GRCh38"


def test_position_unchanged_and_both_assemblies_exposed(monkeypatch):
    """`position` keeps its original value/type; both builds are named."""
    data = _variant(monkeypatch, "80338939", RS80338939)

    # Unchanged: still chrpos, still a "chrom:pos" string.
    assert data["position"] == "13:20189547"
    assert isinstance(data["position"], str)

    assert data["position_grch38"] == "13:20189547"
    assert data["position_grch37"] == "13:20763686"
    # The ~574 kb gap that made the missing label dangerous.
    assert data["position_grch38"] != data["position_grch37"]


def test_previous_assembly_coordinate_for_second_variant(monkeypatch):
    """rs429358's two builds are textbook APOE coordinates."""
    data = _variant(monkeypatch, "429358", RS429358)
    assert data["position_grch38"] == "19:44908684"
    assert data["position_grch37"] == "19:45411941"


def test_missing_previous_assembly_is_null_not_an_error(monkeypatch):
    record = {k: v for k, v in RS429358.items() if k != "chrpos_prev_assm"}
    data = _variant(monkeypatch, "429358", record)

    assert data["position_grch37"] is None
    assert data["position"] == "19:44908684"
    assert data["assembly"] == "GRCh38"
