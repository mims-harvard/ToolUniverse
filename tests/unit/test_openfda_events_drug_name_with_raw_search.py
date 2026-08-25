"""``OpenFDA_search_drug_events`` must not throw away the drug it was given.

The tool accepts a raw Lucene ``search`` and the convenience parameters
``drug_name``/``reaction``. ``drug_name`` and ``reaction`` used to be honoured
only when ``search`` was absent -- popped off the arguments unconditionally,
then read inside ``if not args.get("search")`` -- so supplying both silently
dropped the drug and counted the WHOLE of FAERS.

Measured live 2026-08-12,
``{"drug_name": D, "search": "serious:1",
   "count": "patient.reaction.reactionmeddrapt.exact", "limit": 3}``
returned a byte-identical payload (md5 330b19fa2dc4efa8760214640b29fbb1) topped
by ``{"term": "DEATH", "count": 846360}`` for D = "levetiracetam", for
D = "lacosamide" and for D = "ZZZ_NOT_A_DRUG_XYZ" -- each one
``"status": "success"``. The drug-name-only path answered SEIZURE 16,336 for
levetiracetam over the same period, so the data was always reachable; only the
combination was broken. Asking "which of these anti-seizure drugs has the worse
SERIOUS event profile" is exactly that combination, and it returned the same
846,360 deaths for every drug named.

After the fix the clauses are AND-ed, which can only narrow: levetiracetam +
serious:1 gives SEIZURE 14,934 and lacosamide + serious:1 gives SEIZURE 5,969,
while the nonexistent drug gives 0 reports.

No network: the HTTP layer is stubbed and the assertions are on the query sent.
"""

from unittest.mock import patch

import pytest

from tooluniverse.openfda_tool import OpenFDADrugEventsTool

pytestmark = pytest.mark.unit

CONFIG = {
    "name": "OpenFDA_search_drug_events",
    "type": "OpenFDADrugEventsTool",
    "fields": {"endpoint": "https://api.fda.gov/drug/event.json"},
    "parameter": {"type": "object", "properties": {}},
}

FACET = "patient.reaction.reactionmeddrapt.exact"


def _search_for(arguments):
    """Run the tool with the request stubbed; return the `search` it sent."""
    sent = {}

    def fake_run(_self, args):
        sent.update(args)
        return {"status": "success", "data": {"results": []}}

    with patch("tooluniverse.openfda_tool.BaseRESTTool.run", new=fake_run):
        result = OpenFDADrugEventsTool(CONFIG).run(arguments)
    return sent.get("search"), result


def test_a_drug_name_survives_a_raw_search_instead_of_being_dropped():
    search, _ = _search_for(
        {"drug_name": "levetiracetam", "search": "serious:1", "count": FACET}
    )

    assert 'patient.drug.medicinalproduct:"levetiracetam"' in search
    assert "(serious:1)" in search
    assert " AND " in search


def test_two_different_drugs_no_longer_produce_the_same_query():
    """The defect's signature: identical output for any drug, and for none."""
    leve, _ = _search_for({"drug_name": "levetiracetam", "search": "serious:1"})
    laco, _ = _search_for({"drug_name": "lacosamide", "search": "serious:1"})
    none, _ = _search_for({"drug_name": "ZZZ_NOT_A_DRUG_XYZ", "search": "serious:1"})

    assert len({leve, laco, none}) == 3


def test_a_reaction_also_survives_a_raw_search():
    search, _ = _search_for(
        {"drug_name": "warfarin", "reaction": "Haemorrhage", "search": "serious:1"}
    )

    assert 'patient.reaction.reactionmeddrapt:"Haemorrhage"' in search
    assert 'patient.drug.medicinalproduct:"warfarin"' in search
    assert "(serious:1)" in search


def test_the_raw_clause_is_parenthesized_so_a_top_level_or_cannot_escape():
    """Lucene binds AND tighter than OR, so an un-grouped user clause would
    re-associate and widen the query rather than narrow it."""
    search, _ = _search_for(
        {"drug_name": "warfarin", "search": "serious:1 OR seriousnessdeath:1"}
    )

    assert search.endswith("(serious:1 OR seriousnessdeath:1)")


def test_the_paths_that_already_worked_are_unchanged():
    drug_only, _ = _search_for({"drug_name": "levetiracetam"})
    raw_only, _ = _search_for({"search": "serious:1"})

    assert 'patient.drug.medicinalproduct:"levetiracetam"' in drug_only
    assert "serious:1" not in drug_only
    # A raw search alone is passed through byte-for-byte, unparenthesized:
    # there is nothing to AND it with, so nothing can re-associate.
    assert raw_only == "serious:1"


def test_neither_input_still_asks_for_one():
    _, result = _search_for({"count": FACET})

    assert result["status"] == "error"
    assert "drug_name" in result["error"]
