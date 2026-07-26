"""EnsemblLD_get_ld_variants counted its LD partners after truncating them.

The handler sorted partners by r2, sliced to the top 200, then reported
``ld_count = len(<truncated list>)``. Two things were wrong at once: the count
read as the number of partners the variant has, and the returned set stopped
far above the requested r2 threshold. Confirmed live: rs1042779 in
1000GENOMES:phase_3:CEU at r2_threshold=0.05 returned ``ld_count: 200`` with a
weakest r2 of 0.792, while the Ensembl endpoint returned 735 partners reaching
down to 0.052. The tool description compounded it by promising "all variants in
LD", and there was no parameter to reach past the cap.

The handler now reports ``total_ld_count`` (pre-truncation), keeps ``ld_count``
as what was actually returned, sets ``truncated``, and accepts ``limit``.
"""

from unittest.mock import patch

from tooluniverse.ensembl_ld_tool import DEFAULT_LD_VARIANT_LIMIT, EnsemblLDTool


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _make():
    cfg = {
        "name": "EnsemblLD_get_ld_variants",
        "type": "EnsemblLDTool",
        "fields": {"endpoint_type": "ld_variants"},
        "parameter": {"type": "object", "properties": {}},
    }
    return EnsemblLDTool(cfg)


def _fake_partners(n):
    """n partners with descending r2 from just under 1.0 down toward 0.05."""
    return [
        {
            "variation1": "rs1042779",
            "variation2": f"rs{100000 + i}",
            "r2": str(round(0.99 - (i * 0.9 / n), 6)),
            "d_prime": "0.99",
            "population_name": "1000GENOMES:phase_3:CEU",
        }
        for i in range(n)
    ]


def _run(arguments, n_partners=735):
    tool = _make()
    with patch(
        "tooluniverse.ensembl_ld_tool.requests.get",
        return_value=_FakeResponse(_fake_partners(n_partners)),
    ):
        return tool.run(arguments)


_BASE = {
    "variant_id": "rs1042779",
    "population": "1000GENOMES:phase_3:CEU",
    "r2_threshold": 0.05,
}


def test_total_count_is_reported_before_truncation():
    data = _run(dict(_BASE))["data"]

    assert data["total_ld_count"] == 735
    assert data["ld_count"] == DEFAULT_LD_VARIANT_LIMIT
    assert len(data["ld_variants"]) == DEFAULT_LD_VARIANT_LIMIT
    assert data["truncated"] is True


def test_limit_reaches_the_partners_beyond_the_default_cap():
    data = _run(dict(_BASE, limit=5000))["data"]

    assert data["total_ld_count"] == 735
    assert data["ld_count"] == 735
    assert data["truncated"] is False
    # The weakest partner is now visible instead of being cut off at r2~0.79.
    assert min(v["r2"] for v in data["ld_variants"]) < 0.1


def test_not_flagged_truncated_when_everything_fits():
    data = _run(dict(_BASE), n_partners=12)["data"]

    assert data["total_ld_count"] == 12
    assert data["ld_count"] == 12
    assert data["truncated"] is False


def test_explicit_limit_smaller_than_default_is_honoured():
    data = _run(dict(_BASE, limit=5))["data"]

    assert data["ld_count"] == 5
    assert data["total_ld_count"] == 735
    assert data["truncated"] is True


def test_results_remain_sorted_by_descending_r2():
    data = _run(dict(_BASE, limit=50))["data"]

    r2_values = [v["r2"] for v in data["ld_variants"]]
    assert r2_values == sorted(r2_values, reverse=True)
