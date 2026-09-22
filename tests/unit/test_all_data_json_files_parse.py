"""Every JSON file shipped under src/tooluniverse/data must be valid JSON.

broken_apis/mobidb_rest.json (an archive of a retired API's attempted config) had a
trailing comma after its last investigation note, so it did not parse; anything that
scans the data directory tripped over it ("Could not read tools from ...").
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def test_every_data_json_file_parses():
    failures = []
    for path in sorted(DATA.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except ValueError as exc:
            failures.append(f"{path.relative_to(DATA)}: {exc}")
    assert not failures, "\n".join(failures)
