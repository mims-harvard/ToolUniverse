"""Regression guard for Fix-R3D-002: EPAFRSFacilitiesTool field mapping.

The FRS facility_site table exposes both `state_code` (the 2-letter field
the query actually filters on) and a separate, unreliable `state_name`
column that frequently belongs to a different state than the one requested.
Likewise `registry_id` (the real FRS identifier) is a distinct field from
`parent_registry_id` (null for nearly every row). `_summarize` used to read
the wrong field in both cases, silently returning facilities that looked
like they were from the wrong state with no registry_id at all.
"""

import pytest

from tooluniverse.epa_envirofacts_tool import EPAFRSFacilitiesTool

pytestmark = pytest.mark.unit


def test_summarize_reads_state_code_not_state_name():
    row = {
        "std_name": "SOME FACILITY",
        "state_code": "TX",
        "state_name": "CALIFORNIA",  # mismatched, as observed live
        "registry_id": "110049814322",
        "parent_registry_id": None,
    }
    out = EPAFRSFacilitiesTool._summarize(row)
    assert out["state"] == "TX"
    assert out["registry_id"] == "110049814322"


def test_summarize_falls_back_gracefully_when_fields_missing():
    out = EPAFRSFacilitiesTool._summarize({})
    assert out["state"] is None
    assert out["registry_id"] is None
