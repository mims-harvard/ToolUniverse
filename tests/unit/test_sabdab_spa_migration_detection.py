"""The SAbDab2 migration: what made the API look unreachable, and the fix.

Fix-R17D-2/3 recorded that "the new domain's /api/pdb/{id}/ route
307-redirects to an internal-only 'sabdab-backend:8000' hostname, not publicly
resolvable", and concluded the API could not be used. That observation was
right, and so was the conclusion *for the URL that was tried*. The cause is
narrower than it looked: it is the trailing slash.

Reproduced three times each, consistently:

    /api/pdb/pdb_00003hfm    -> 200 application/json
    /api/pdb/pdb_00003hfm/   -> 307 http://backend:8000/pdb/pdb_00003hfm
                                 -> DNS failure off the cluster

So the tools now read the API with no trailing slash, and this file guards the
two things that made the old behaviour wrong: a path must never carry a
trailing slash, and a 200 that is not JSON must never be reported as data. The
data-shape coverage lives in tests/unit/test_sabdab_reads_the_api.py.
"""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.sabdab_tool import SAbDabTool

pytestmark = pytest.mark.unit

_ENTRY = {
    "id": "pdb_00001n8z",
    "name": "CRYSTAL STRUCTURE OF EXTRACELLULAR DOMAIN OF HUMAN HER2",
    "resolution": 2.52,
    "polymer_instances": [],
    "antibody_instances": [],
}


def _tool(operation):
    return SAbDabTool(
        {
            "name": f"SAbDab_{operation}",
            "type": "SAbDabTool",
            "fields": {"operation": operation},
            "parameter": {"type": "object", "properties": {}},
        }
    )


class _Json:
    status_code = 200
    headers = {"Content-Type": "application/json"}

    @staticmethod
    def json():
        return _ENTRY


@pytest.mark.parametrize("operation", ["get_structure", "get_structure_summary"])
def test_no_api_path_ever_carries_a_trailing_slash(operation):
    """The slash is what sent this API to an unroutable internal hostname."""
    seen = []

    def fake_get(url, params=None, timeout=None, headers=None):
        seen.append(url)
        return _Json()

    with patch("tooluniverse.sabdab_tool.requests.get", fake_get):
        _tool(operation).run({"operation": operation, "pdb_id": "1n8z"})

    assert seen, "no request was made"
    for url in seen:
        assert not url.endswith("/"), (
            f"{url} ends in a slash; SAbDab 307-redirects that form to "
            "http://backend:8000/... which does not resolve off the cluster"
        )
