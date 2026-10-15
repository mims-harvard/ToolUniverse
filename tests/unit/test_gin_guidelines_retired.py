"""GIN_Guidelines_Search is retired: the GIN library portal has no programmatic search.

Its ?q= filter searched only the portal's promoted front-page items, so the
tool answered "No guidelines found" to 63 of 65 calls in ATHENA's MedR and
NOHARM runs. The investigation is recorded in broken_apis/gin_guidelines.json.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def test_gin_is_no_longer_a_loaded_tool():
    names = {
        t["name"]
        for t in json.loads((DATA / "unified_guideline_tools.json").read_text())
    }
    assert "GIN_Guidelines_Search" not in names
    assert "EuropePMC_Guidelines_Search" in names  # the documented workaround stays


def test_the_retirement_is_documented_with_its_config():
    doc = json.loads((DATA / "broken_apis" / "gin_guidelines.json").read_text())
    for field in (
        "api_name",
        "base_url",
        "failure_mode",
        "root_cause",
        "confirmed_broken_date",
        "retry_count",
        "retry_after",
        "workaround",
        "attempted_config_file",
    ):
        assert doc[field], field
    assert doc["retry_count"] >= 3
    archived = json.loads(
        (DATA / "broken_apis" / "gin_guidelines_tools.json").read_text()
    )
    assert [t["name"] for t in archived] == ["GIN_Guidelines_Search"]
