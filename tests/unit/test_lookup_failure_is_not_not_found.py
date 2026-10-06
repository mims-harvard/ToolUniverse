"""A name lookup that failed is not a name that does not exist.

Found looking for #753's pattern elsewhere: a resolver swallows the
exception, returns the same None it returns for a miss, and the tool tells
the user the thing does not exist. CIViC answered a timeout with "Gene 'X' not
found in CIViC database"; ChEMBL, BRENDA (via UniProt) and the PubChem name
resolver did the same. Each resolver now records why it failed, and the
callers say so instead.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"


def _resp(status, payload=None):
    r = MagicMock()
    r.status_code = status
    r.json.return_value = payload if payload is not None else {}
    r.raise_for_status = MagicMock(
        side_effect=None if status < 400 else requests.HTTPError(f"HTTP {status}")
    )
    return r


# ---------- CIViC ----------


def _civic():
    from tooluniverse.civic_tool import CIViCTool

    tools = json.loads((DATA / "civic_tools.json").read_text("utf-8"))
    config = next(t for t in tools if t["name"] == "civic_get_variants_by_gene")
    return CIViCTool(config)


def test_civic_timeout_is_not_reported_as_a_missing_gene():
    tool = _civic()

    with patch(
        "tooluniverse.civic_tool.requests.post",
        side_effect=requests.ConnectTimeout("connect timed out"),
    ):
        result = tool.run({"gene_name": "BRAF"})

    assert result["status"] == "error"
    assert "not found in CIViC" not in result["error"]
    assert "CIViC did not answer" in result["error"]


def test_civic_a_real_miss_still_says_not_found():
    tool = _civic()
    empty = _resp(200, {"data": {"genes": {"nodes": []}}})

    with patch("tooluniverse.civic_tool.requests.post", return_value=empty):
        result = tool.run({"gene_name": "NOTAGENE"})

    assert result["error"] == "Gene 'NOTAGENE' not found in CIViC database"


def test_civic_a_5xx_counts_as_a_failure():
    tool = _civic()
    failures = []

    with patch("tooluniverse.civic_tool.requests.post", return_value=_resp(502)):
        assert tool._lookup_gene_id("BRAF", failures) is None
    assert failures == ["HTTP 502"]


# ---------- ChEMBL ----------


def test_chembl_lookup_records_failures_and_not_misses():
    from tooluniverse.chem_tool import ChEMBLRESTTool

    tool = ChEMBLRESTTool.__new__(ChEMBLRESTTool)
    tool.base_url = "https://www.ebi.ac.uk/chembl/api/data"
    tool.session = MagicMock()

    failures = []
    with patch(
        "tooluniverse.chem_tool.request_with_retry",
        side_effect=requests.ReadTimeout("read timed out"),
    ):
        assert tool._lookup_chembl_id_by_name("sotorasib", failures) is None
    assert len(failures) == 2

    failures = []
    with patch(
        "tooluniverse.chem_tool.request_with_retry",
        return_value=_resp(200, {"molecules": []}),
    ):
        assert tool._lookup_chembl_id_by_name("notadrug", failures) is None
    assert failures == []


def test_chembl_caller_names_the_outage():
    source = (
        Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "chem_tool.py"
    ).read_text("utf-8")

    assert "ChEMBL did not answer" in source
    assert "self._lookup_chembl_id_by_name(drug_name, failures)" in source


# ---------- BRENDA (UniProt name -> EC) ----------


@pytest.mark.parametrize(
    ("effect", "expected"),
    [
        (requests.ConnectionError("reset"), ["reset"]),
        (_resp(503), ["UniProt HTTP 503"]),
        (_resp(200, {"results": []}), []),
    ],
)
def test_brenda_resolver_separates_failure_from_miss(effect, expected):
    from tooluniverse.brenda_tool import BRENDATool

    tool = BRENDATool.__new__(BRENDATool)
    failures = []
    kwargs = (
        {"side_effect": effect}
        if isinstance(effect, Exception)
        else {"return_value": effect}
    )

    with patch("tooluniverse.brenda_tool.requests.get", **kwargs):
        assert tool._resolve_ec_from_name("hexokinase", failures) is None
    assert failures == expected


# ---------- PubChem name -> SMILES ----------


@pytest.mark.parametrize(
    ("effect", "expected"),
    [
        (requests.ReadTimeout("slow"), ["slow"]),
        (_resp(503), ["PubChem HTTP 503"]),
        (_resp(404), []),  # PubChem's answer for an unknown name
    ],
)
def test_pubchem_resolver_separates_failure_from_unknown_name(effect, expected):
    from tooluniverse.molecule_2d_tool import Molecule2DTool

    tool = Molecule2DTool.__new__(Molecule2DTool)
    failures = []
    kwargs = (
        {"side_effect": effect}
        if isinstance(effect, Exception)
        else {"return_value": effect}
    )

    with patch("tooluniverse.molecule_2d_tool.requests.get", **kwargs):
        assert tool._resolve_molecule_name("aspirin", failures) is None
    assert failures == expected


def test_resolvers_keep_their_old_signature():
    """Existing callers pass only the name; that still works."""
    from tooluniverse.brenda_tool import BRENDATool

    tool = BRENDATool.__new__(BRENDATool)
    with patch(
        "tooluniverse.brenda_tool.requests.get",
        side_effect=requests.ConnectionError("x"),
    ):
        assert tool._resolve_ec_from_name("hexokinase") is None


# ---------- OpenAIRE: errors wrapped in a success envelope ----------


def _openaire():
    from tooluniverse.openaire_tool import OpenAIRETool

    tools = json.loads((DATA / "openaire_tools.json").read_text("utf-8"))
    return OpenAIRETool(
        next(t for t in tools if t["name"] == "OpenAIRE_search_publications")
    )


@pytest.mark.parametrize(
    ("arguments", "effect"),
    [
        ({"query": "cancer"}, requests.ReadTimeout("read timed out")),
        ({"query": ""}, None),
        ({"query": "cancer", "type": "nonsense"}, None),
    ],
)
def test_openaire_failures_are_errors_at_the_top(arguments, effect):
    """Run 37273817054 quoted openaire as a schema mismatch on
    {'status': 'error', ...} inside data: the outer envelope said success, so
    the failure was also cacheable."""
    from tooluniverse.execute_function import ToolUniverse

    tool = _openaire()
    with patch("tooluniverse.openaire_tool.requests.get", side_effect=effect):
        out = tool.run(arguments)

    assert out["status"] == "error" and out["error"]
    assert out["data"]["status"] == "error"  # kept for existing callers
    assert ToolUniverse._is_error_result(out)


def test_openaire_network_error_carries_its_reason():
    tool = _openaire()
    with patch(
        "tooluniverse.openaire_tool.requests.get",
        side_effect=requests.ReadTimeout("read timed out"),
    ):
        out = tool.run({"query": "cancer"})

    assert "read timed out" in out["error"]
