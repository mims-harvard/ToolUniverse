"""Regression guard for Fix-R18B-2: ReactomeInteractorsTool sent
page=-1 (a Reactome-specific "ignore pagination, return everything"
signal), so the tool's own documented page_size parameter had zero effect
-- confirmed live that page=-1&pageSize=10 returned all 153 interactors for
P31749, while page=1&pageSize=10 correctly returned 10.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.reactome_interactors_tool import ReactomeInteractorsTool

pytestmark = pytest.mark.unit


def _tool():
    return ReactomeInteractorsTool(
        {"name": "ReactomeInteractors_get_protein_interactors", "fields": {}}
    )


def test_page_size_is_honored_via_correct_page_param():
    tool = _tool()
    captured = {}

    def fake_get(url, params=None, **kwargs):
        captured["params"] = params
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.json.return_value = {
            "resource": "IntAct",
            "entities": [
                {
                    "acc": "P31749",
                    "count": 10,
                    "interactors": [
                        {"acc": f"P{i}", "alias": None, "score": 0.5, "evidences": []}
                        for i in range(10)
                    ],
                }
            ],
        }
        return resp

    with patch(
        "tooluniverse.reactome_interactors_tool.requests.get", side_effect=fake_get
    ):
        result = tool._get_interactors({"accession": "P31749", "page_size": 10})

    assert captured["params"]["page"] == 1
    assert captured["params"]["pageSize"] == 10
    assert len(result["data"]["interactors"]) == 10
