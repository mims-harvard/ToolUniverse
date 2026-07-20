"""Regression guard for Fix-R23E-1: AHA_ACC_search_guidelines's PubMed
query hard-required a Corporate Author tag ("American Heart
Association"[Corporate Author] OR "American College of
Cardiology"[Corporate Author]) -- confirmed live via PubMed E-utilities
that recent joint-committee guidelines (e.g. the 2024 HCM guideline, PMID
38718139) carry no Corporate Author field at all, only named individual
authors, with the sponsoring societies appearing solely in the title. The
Corporate-Author-only filter silently excluded these, making a
year_from-scoped search return zero results even though a current,
directly relevant guideline exists. Fixed by also matching on title text.
"""

from unittest.mock import patch

import pytest

from tooluniverse.clinical_society_tools import AHAACCGuidelineTool

pytestmark = pytest.mark.unit


def _tool():
    return AHAACCGuidelineTool(
        {"name": "aha_acc_test", "fields": {"operation": "search"}}
    )


class TestGuidelineQueryBroadening:
    def test_query_matches_title_not_just_corporate_author(self):
        tool = _tool()

        with patch(
            "tooluniverse.clinical_society_tools._search_and_fetch",
            return_value={"status": "success", "result": []},
        ) as mock_fetch:
            tool.run(
                {"query": "hypertrophic cardiomyopathy", "limit": 5, "year_from": 2020}
            )

        query_arg = mock_fetch.call_args[0][0]
        assert '"American Heart Association"[Corporate Author]' in query_arg
        assert '"American Heart Association"[Title]' in query_arg
        assert '"American College of Cardiology"[Title]' in query_arg
        assert '"guideline"[Title]' in query_arg or "practice guideline" in query_arg
