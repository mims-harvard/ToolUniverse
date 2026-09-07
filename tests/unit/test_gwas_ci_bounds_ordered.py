"""``ci_lower`` must never exceed ``ci_upper``.

Defect this covers
------------------
GWAS Catalog derives ``ci_lower`` / ``ci_upper`` by splitting its own ``range``
string, and sometimes writes that string high-bound-first, so the inverted pair
arrives under field names asserting the opposite ordering.
``gwas_get_variants_for_trait`` passed it straight through.

``gwas_tool._order_ci_bounds`` is the single record of the live sweep behind
this: the four inverted periodontitis rows with their measurements, and why
``range`` must not be re-parsed. It is not repeated here -- two dated copies of
one measurement drift apart. ``INVERTED`` below is those four rows verbatim, and
``test_negative_bounds_survive`` is the negative-bound half of that rationale.

All tests here mock the HTTP layer -- no network. See ``_no_network``.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.gwas_tool import GWASAssociationByID, GWASVariantsForTrait

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _no_network(disable_network):
    """Fail loudly if anything in this module reaches the network.

    ``disable_network`` (tests/conftest.py) closes ``requests.Session.request``,
    which is the door ``requests.get`` and ``http_utils.request_with_retry`` ->
    ``requests.request`` both go through. The two extra patches below are belt
    and braces for a caller that reaches past requests entirely. Autouse, so a
    test added later cannot opt out; each test re-opens only ``requests.get``,
    with a fake.
    """

    def boom(*args, **kwargs):
        raise AssertionError("network access attempted in a hermetic test")

    with (
        patch("requests.request", side_effect=boom),
        patch("socket.create_connection", side_effect=boom),
    ):
        yield


def _association(association_id, rng, ci_lower, ci_upper, gene="TCF7L2"):
    """Shape mirrors /v2/associations/105855749 exactly."""
    return {
        "association_id": association_id,
        "range": rng,
        "ci_lower": ci_lower,
        "ci_upper": ci_upper,
        "beta": "0.05 unit increase",
        "p_value": 6e-13,
        "mapped_genes": [gene],
    }


# The four live periodontitis offenders, verbatim.
INVERTED = [
    _association(105855749, "[0.07-0.03]", 0.07, 0.03, "TCF7L2"),
    _association(105855816, "[0.06-0.02]", 0.06, 0.02, "ZFP36L2"),
    _association(105855801, "[0.1-0.06]", 0.1, 0.06, "CCND2"),
    _association(105855764, "[0.05-0.01]", 0.05, 0.01, "ARAP1"),
]


def _serve(payload):
    """`_make_request` reads only `raise_for_status()` and `json()` on this path."""
    response = MagicMock()
    response.json.return_value = payload
    return patch("tooluniverse.gwas_tool.requests.get", return_value=response)


def _variants(associations):
    """Run gwas_get_variants_for_trait with the trait already resolved.

    ``efo_id`` is passed so the trait resolver never fires and the single mocked
    response is the association page, not an ontology lookup.
    """
    tool = GWASVariantsForTrait(
        {"name": "gwas_get_variants_for_trait", "type": "GWASVariantsForTrait"}
    )
    payload = {
        "_embedded": {"associations": associations},
        "page": {"totalElements": 1},
    }
    with _serve(payload):
        return tool.run({"efo_id": "MONDO_0005076"})


def test_inverted_bounds_are_ordered_and_the_raw_range_is_kept():
    rows = _variants(INVERTED)["data"]

    assert [(r["ci_lower"], r["ci_upper"]) for r in rows] == [
        (0.03, 0.07),
        (0.02, 0.06),
        (0.06, 0.1),
        (0.01, 0.05),
    ]
    # `range` is the record of what upstream actually sent, so it stays verbatim.
    assert [r["range"] for r in rows] == [
        "[0.07-0.03]",
        "[0.06-0.02]",
        "[0.1-0.06]",
        "[0.05-0.01]",
    ]
    # Order and identity: the repair rebuilds each row, so the rows must still be
    # the same four loci, in the same order, and not shuffled or merged.
    assert [r["mapped_genes"] for r in rows] == [
        ["TCF7L2"],
        ["ZFP36L2"],
        ["CCND2"],
        ["ARAP1"],
    ]


def test_already_ordered_bounds_are_untouched():
    ordered = _association(105855750, "[1.15939-1.18827]", 1.15939, 1.18827)
    row = _variants([ordered])["data"][0]

    assert (row["ci_lower"], row["ci_upper"]) == (1.15939, 1.18827)
    assert row["range"] == "[1.15939-1.18827]"


@pytest.mark.parametrize(
    "rng, lower, upper",
    [
        # Upstream's own ordering, correct: two negative bounds.
        ("[-0.05--0.01]", -0.05, -0.01),
        # ...and the same pair written high-first.
        ("[-0.01--0.05]", -0.01, -0.05),
        # A negative lower bound with a positive upper, the live shape.
        ("[-0.00131-0.00151]", -0.00131, 0.00151),
    ],
)
def test_negative_bounds_survive(rng, lower, upper):
    """A minus sign must never be mistaken for the separator inside `range`.

    Splitting "[-0.05--0.01]" on "-" yields ['', '0.05', '', '0.01'] -- which is
    why the ordering is done on the numeric fields and `range` is left alone.
    """
    row = _variants([_association(1, rng, lower, upper)])["data"][0]

    assert row["ci_lower"] == min(lower, upper)
    assert row["ci_upper"] == max(lower, upper)
    assert row["range"] == rng


def test_missing_bounds_are_left_alone():
    """15 of the 172 periodontitis rows carry `range` "-" or "[NR]" and no bounds."""
    row = _variants([_association(2, "[NR]", None, None)])["data"][0]

    assert row["ci_lower"] is None
    assert row["ci_upper"] is None
    assert row["range"] == "[NR]"


def test_single_association_endpoint_is_repaired_too():
    """`gwas_get_association_by_id` bypasses the list extractor entirely."""
    tool = GWASAssociationByID(
        {"name": "gwas_get_association_by_id", "type": "GWASAssociationByID"}
    )
    with _serve(INVERTED[0]):
        row = tool.run({"association_id": "105855749"})

    assert (row["ci_lower"], row["ci_upper"]) == (0.03, 0.07)
    assert row["range"] == "[0.07-0.03]"
