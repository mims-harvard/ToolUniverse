"""visualize_molecule_2d's parameter schema must not require all three
mutually-alternative identifier params at once.

Regression (Fix-R25B-1): the JSON schema had
`"required": ["smiles", "inchi", "molecule_name"]`, forcing every one of
the three params even though the tool's own implementation
(molecule_2d_tool.py) explicitly supports providing just one of them via
an if/elif/elif chain, with its own clear
"Either smiles, inchi, or molecule_name must be provided" error when none
are given. The sibling tool visualize_molecule_3d has no `required` key
at all for the same three-way-alternative param set -- that's the correct
shape. Confirmed live: passing only `smiles` previously failed parameter
validation before ever reaching the tool's own logic.
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
    "molecule_2d_tools.json",
)


def _tool(name):
    with open(_CONFIG) as fh:
        for t in json.load(fh):
            if isinstance(t, dict) and t.get("name") == name:
                return t
    raise AssertionError(f"{name} not found in molecule_2d_tools.json")


def test_visualize_molecule_2d_does_not_require_all_three_identifiers():
    tool = _tool("visualize_molecule_2d")
    required = tool["parameter"].get("required")
    assert not required, (
        f"visualize_molecule_2d should not force smiles+inchi+molecule_name "
        f"together, but required={required!r}"
    )
