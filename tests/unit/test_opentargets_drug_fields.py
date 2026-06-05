"""OpenTargets drug query must not request fields removed from the schema.

Regression: OpenTargets removed `yearOfFirstApproval` from the Drug type and
renamed `maximumClinicalTrialPhase` -> `maximumClinicalStage`. The
OpenTargets_get_drug_description_by_chemblId query still requested the old
names, so every call returned HTTP 400 "Cannot query field ...". The query must
use only current fields.
"""

import json
import os

import pytest

pytestmark = pytest.mark.unit

_CONFIG = os.path.join(
    os.path.dirname(__file__),
    "..",
    "..",
    "src",
    "tooluniverse",
    "data",
    "opentarget_tools.json",
)


def _tool(name):
    with open(_CONFIG) as fh:
        for t in json.load(fh):
            if isinstance(t, dict) and t.get("name") == name:
                return t
    raise AssertionError(f"{name} not found in opentarget_tools.json")


def test_drug_description_query_uses_current_fields():
    tool = _tool("OpenTargets_get_drug_description_by_chemblId")
    query = tool.get("query_schema", "")
    # removed / renamed fields must be gone from the GraphQL query
    assert "yearOfFirstApproval" not in query
    assert "maximumClinicalTrialPhase" not in query
    # the current replacement field must be present
    assert "maximumClinicalStage" in query


def test_drug_description_has_real_example():
    tool = _tool("OpenTargets_get_drug_description_by_chemblId")
    examples = tool.get("test_examples", [])
    assert examples and examples[0].get("chemblId")


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
