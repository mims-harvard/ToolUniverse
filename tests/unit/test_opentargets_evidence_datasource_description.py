"""Regression guard for Fix-R31D-2: OpenTargets_get_evidence_by_datasource's
description listed "chembl" as a valid datasourceId, but confirmed live
that "chembl" now returns 0 rows on the current Open Targets platform even
for well-documented drug-target-disease evidence (e.g. EGFR/non-small cell
lung carcinoma), while "clinical_precedence" -- not listed -- returns the
real data. GraphQL introspection against the target's own evidence rows
confirmed "clinical_precedence" is the current id; "chembl" appears
retired/renamed upstream.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

_DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _tool_config(name):
    configs = json.loads((_DATA_DIR / "opentarget_tools.json").read_text())
    for cfg in configs:
        if cfg["name"] == name:
            return cfg
    raise AssertionError(f"{name} not found")


def test_description_no_longer_lists_retired_chembl_datasource():
    cfg = _tool_config("OpenTargets_get_evidence_by_datasource")
    valid_sources_text = cfg["description"]
    assert "clinical_precedence" in valid_sources_text
    # "chembl" is still mentioned (as a note that it was renamed), but must
    # not appear as a bare comma-separated entry in the valid-sources list.
    assert ", chembl," not in valid_sources_text
