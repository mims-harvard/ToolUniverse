"""KEGG DBLINKS PubChem values are substance IDs, and must say so.

KEGG deposits its records into PubChem as substances, so C05443's
"PubChem: 7805" is SID 7805 (cholecalciferol, CID 5280795). Emitting it under
the bare key "PubChem" invited callers to pass it to a CID-based tool, which
answers with CID 7805 -- 1-bromo-4-methylbenzene -- as a plain success.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.kegg_ext_tool import _store_dblink

pytestmark = pytest.mark.unit


def test_pubchem_is_labelled_as_a_substance_id():
    dblinks = {}
    _store_dblink(dblinks, "PubChem", " 7805 ")

    assert dblinks == {"PubChem_SID": "7805"}
    assert "PubChem" not in dblinks


def test_other_cross_references_keep_their_own_namespace():
    dblinks = {}
    _store_dblink(dblinks, "ChEBI", "28940")
    _store_dblink(dblinks, "CAS", "67-97-0")

    assert dblinks == {"ChEBI": "28940", "CAS": "67-97-0"}
