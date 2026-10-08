"""BOLDSystems_search_by_taxon returned nothing for a species name with no rank.

``taxon_name="Apis mellifera"`` was searched as ``tax:genus:Apis mellifera``, which
matches no genus, and the call succeeded with an empty list. A name with a space
cannot be a genus, so an omitted rank now means species; an explicit rank is kept.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.bold_systems_tool import BOLDSystemsTool

pytestmark = pytest.mark.unit

ROWS = [
    {"processid": "A1", "genus": "Apis", "species": "Apis mellifera"},
    {"processid": "A2", "genus": "Apis", "species": "Apis cerana"},
]


def _search(arguments):
    tool = BOLDSystemsTool(
        {
            "name": "BOLDSystems_search_by_taxon",
            "fields": {"operation": "search_by_taxon"},
        }
    )
    with patch(
        "tooluniverse.bold_systems_tool._run_query",
        return_value=({"data": ROWS, "recordsTotal": 2}, None),
    ) as run_query:
        return tool._search_by_taxon(arguments), run_query


def test_two_word_name_without_rank_is_searched_as_a_species():
    result, run_query = _search({"taxon_name": "Apis mellifera"})
    assert result["metadata"]["rank"] == "species"
    assert run_query.call_args.args[0] == "tax:genus:Apis"  # genus-level query
    assert [r["processid"] for r in result["data"]] == ["A1"]  # filtered to the species


def test_one_word_name_without_rank_is_still_a_genus():
    result, _ = _search({"taxon_name": "Apis"})
    assert result["metadata"]["rank"] == "genus"
    assert len(result["data"]) == 2


def test_explicit_rank_is_respected():
    result, _ = _search({"taxon_name": "Apis", "rank": "species"})
    assert result["metadata"]["rank"] == "species"
