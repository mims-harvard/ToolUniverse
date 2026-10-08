"""RCSB *_by_entity_id examples must be real entity IDs ("4HHB_1"), not "1".

The examples used entity_id "1", which RCSB answers with an empty list, so
`tu test` (and the docs) showed nothing for these tools.
"""

import json
import re
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src/tooluniverse/data/rcsb_pdb_tools.json"


def test_entity_id_examples_look_like_entity_ids():
    tools = [
        t for t in json.loads(DATA.read_text()) if t["name"].endswith("_by_entity_id")
    ]
    assert tools
    for tool in tools:
        for example in tool["test_examples"]:
            assert re.fullmatch(r"[0-9][A-Za-z0-9]{3}_\d+", example["entity_id"]), tool[
                "name"
            ]
