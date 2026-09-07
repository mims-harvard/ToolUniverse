"""Regression guard for the GxA partial-sample disclosure fix.

`GxA_get_experiment_expression` calls the upstream EBI Expression Atlas
`/experiments/{accession}` endpoint. That endpoint (confirmed live against
E-MTAB-2836: searchResultTotal=9570, len(rows)=29) always returns only a
small, arbitrary default SAMPLE of the experiment's genes and silently
ignores every gene-filter parameter we can send it. A prior fix already
applied a client-side `gene_id` filter over that sample, but a filtered
miss still came back as a bare, confident-looking empty result -- easily
misread as "this gene is not expressed here" when it may simply have
fallen outside the tiny sample.

This test mocks the upstream JSON with `searchResultTotal` far larger than
`len(rows)` and asserts:
  * the filtered-miss path still returns status=success (strictly additive,
    not a re-meaning of success/error)
  * it discloses `profiles_returned_by_upstream` / `profiles_available_upstream`
  * it carries a `coverage_warning` explaining an empty result is not
    evidence of absence
  * the filtered-hit path returns real rows and does NOT carry that warning
  * the unfiltered path also carries the coverage numbers (so
    `total_gene_profiles` is never mistaken for the true experiment gene
    count), and does not carry the warning
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gxa_tool import GxATool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


def _tool():
    return GxATool(
        {
            "name": "GxA_get_experiment_expression",
            "fields": {"endpoint": "get_experiment_expression"},
        }
    )


# A small sample of 3 rows out of a much larger upstream total, mirroring
# the live E-MTAB-2836 shape (searchResultTotal is a numeric *string*
# upstream -- confirmed live -- so the fake mirrors that quirk too).
SAMPLE_RESPONSE = {
    "experiment": {"description": "RNA-seq of 122 human tissues"},
    "columnHeaders": [
        {
            "assayGroupId": "g1",
            "factorValue": "liver",
            "factorValueOntologyTermId": "UBERON_0002107",
            "assayGroupSummary": {"replicates": 3},
        },
        {
            "assayGroupId": "g2",
            "factorValue": "kidney",
            "factorValueOntologyTermId": "UBERON_0002113",
            "assayGroupSummary": {"replicates": 4},
        },
    ],
    "profiles": {
        "searchResultTotal": "9570",
        "rows": [
            {
                "id": "ENSG00000252920",
                "name": "ENSG00000252920",
                "expressions": [{"value": 6.0}, {"value": "N/A"}],
            },
            {
                "id": "ENSG00000111111",
                "name": "DEFA1B",
                "expressions": [{"value": 1.2}, {"value": 2.3}],
            },
            {
                "id": "ENSG00000222222",
                "name": "INSL5",
                "expressions": [{"value": None}, {"value": 0.5}],
            },
        ],
    },
}


def _fake_get(url, **kwargs):
    return _FakeResponse(200, SAMPLE_RESPONSE)


def test_filtered_miss_returns_success_with_coverage_warning(monkeypatch):
    tool = _tool()
    monkeypatch.setattr("tooluniverse.gxa_tool.requests.get", _fake_get)

    # TP53 is not in the fake sample -- mirrors the real-world bug report.
    result = tool.run(
        {
            "experiment_accession": "E-MTAB-2836",
            "gene_id": "ENSG00000141510",
        }
    )

    assert result["status"] == "success"
    data = result["data"]

    # Existing keys keep their existing meaning (strictly additive).
    assert data["total_gene_profiles"] == 0
    assert data["gene_profiles"] == []

    # New disclosure keys.
    assert data["profiles_returned_by_upstream"] == 3
    assert data["profiles_available_upstream"] == 9570
    assert isinstance(data["profiles_available_upstream"], int)

    warning = data["coverage_warning"]
    assert warning is not None
    assert "not evidence" in warning.lower()
    assert "3" in warning and "9570" in warning
    assert "ENSG00000141510" in warning


def test_filtered_hit_returns_rows_without_warning(monkeypatch):
    tool = _tool()
    monkeypatch.setattr("tooluniverse.gxa_tool.requests.get", _fake_get)

    # ENSG00000252920 IS in the fake sample.
    result = tool.run(
        {
            "experiment_accession": "E-MTAB-2836",
            "gene_id": "ENSG00000252920",
        }
    )

    assert result["status"] == "success"
    data = result["data"]

    assert data["total_gene_profiles"] == 1
    assert len(data["gene_profiles"]) == 1
    assert data["gene_profiles"][0]["gene_id"] == "ENSG00000252920"

    # Coverage numbers are still present...
    assert data["profiles_returned_by_upstream"] == 3
    assert data["profiles_available_upstream"] == 9570
    # ...but no warning, since the requested gene WAS found.
    assert data["coverage_warning"] is None


def test_unfiltered_path_carries_coverage_numbers_without_warning(monkeypatch):
    tool = _tool()
    monkeypatch.setattr("tooluniverse.gxa_tool.requests.get", _fake_get)

    result = tool.run({"experiment_accession": "E-MTAB-2836"})

    assert result["status"] == "success"
    data = result["data"]

    # total_gene_profiles reflects only the sample searched, never the
    # true experiment gene count -- the new keys make that explicit.
    assert data["total_gene_profiles"] == 3
    assert data["profiles_returned_by_upstream"] == 3
    assert data["profiles_available_upstream"] == 9570
    assert data["coverage_warning"] is None
