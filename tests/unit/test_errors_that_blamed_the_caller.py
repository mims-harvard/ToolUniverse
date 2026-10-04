"""Four tools whose errors were wrong, or whose requests were.

From the 2026-10-04 sweep. Three said the caller had made a mistake when they
had not; one built a request its upstream could not read.

  gsa         "No GSA accession found" for an accession that exists: the
              record page is now a JavaScript browser check
  swissadme   "Verify the SMILES is valid" for aspirin: the server answers 403
  regulomedb  404 for every variant: the API moved to api.regulomedb.org
  zinc        "No Valid SMILES" for aspirin: the form was sent with GET
  fpbase      the API renamed agg_exc_max__* to ex_max__* and said so
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src" / "tooluniverse"
DATA = SRC / "data"

# The page GSA serves in front of its records, abridged.
GSA_CHECK = (
    "<!DOCTYPE html><html><head><title>正在进行安全检查...</title></head>"
    "<body><h2>正在验证您的浏览器，请稍候...</h2><script>var secret = "
    "'my_nginx_salt_' + dateStr;</script></body></html>"
)


class _Resp:
    def __init__(self, status_code, text=""):
        self.status_code = status_code
        self.text = text

    def raise_for_status(self):
        return None


def test_gsa_reports_the_browser_check_not_a_missing_accession(monkeypatch):
    import tooluniverse.gsa_tool as gsa

    monkeypatch.setattr(gsa.requests, "get", lambda *a, **k: _Resp(200, GSA_CHECK))
    tool = gsa.GSATool({"name": "GSA_get_accession", "description": "t",
                        "parameter": {}})

    result = tool.run({"accession": "CRA002926"})

    assert result["status"] == "error"
    assert "browser check" in result["error"]
    assert "does not mean the accession is missing" in result["error"]
    assert "No GSA accession found" not in result["error"]


def test_gsa_does_not_work_around_the_check():
    """Its intent is stated in the page; the salt is in it too. Not used."""
    source = (SRC / "gsa_tool.py").read_text("utf-8")

    assert "my_nginx_salt" not in source
    assert "/gsa/search" not in source, (
        "routing to a GSA page the check has not yet covered would be working "
        "against the operator's stated intent"
    )


def test_gsa_still_says_not_found_for_a_real_miss(monkeypatch):
    import tooluniverse.gsa_tool as gsa

    monkeypatch.setattr(
        gsa.requests, "get", lambda *a, **k: _Resp(200, "<html><body></body></html>")
    )
    tool = gsa.GSATool({"name": "GSA_get_accession", "description": "t",
                        "parameter": {}})

    assert "No GSA accession found" in tool.run({"accession": "CRA999999"})["error"]


def test_swissadme_names_a_refusal_instead_of_blaming_the_smiles():
    from tooluniverse.swissadme_tool import SwissADMETool

    tool = SwissADMETool({"name": "x", "description": "t", "parameter": {}})
    tool.session.post = lambda *a, **k: _Resp(403)

    result = tool.run({"operation": "calculate_adme",
                       "smiles": "CC(=O)Oc1ccccc1C(=O)O"})

    assert "HTTP 403" in result["error"]
    assert "not a judgement on the molecule" in result["error"]
    assert "Verify the SMILES" not in result["error"]


def test_swissadme_does_not_carry_a_reason_into_the_next_call():
    """The reset lives in the helper, so every caller gets it.

    My first version reset at one caller and missed _check_druglikeness; the
    second attempt landed after a `return`, where it never ran. Checked with
    two calls on one instance, which is the case that would leak.
    """
    from tooluniverse.swissadme_tool import SwissADMETool

    tool = SwissADMETool({"name": "x", "description": "t", "parameter": {}})
    responses = [_Resp(403), _Resp(200, "<html>no results link</html>")]
    tool.session.post = lambda *a, **k: responses.pop(0)

    assert tool._submit_and_get_csv("CCO") is None
    assert "403" in tool._last_failure
    assert tool._submit_and_get_csv("CCO") is None
    assert tool._last_failure is None, "the 403 from the previous call leaked"


def test_regulomedb_reads_the_api_subdomain():
    tools = json.loads((DATA / "regulomedb_tools.json").read_text("utf-8"))
    raw = json.dumps(tools)

    assert "regulomedb.org/regulome-search" not in raw
    assert "https://api.regulomedb.org/search?" in raw


def test_zinc_submits_its_structure_search_as_a_post():
    source = (SRC / "zinc_tool.py").read_text("utf-8")

    assert "self.session.post(submit_url, files=form" in source
    assert "self.session.get(submit_url, files=form" not in source, (
        "CartBlanche ignores a body on a GET and answers 'No Valid SMILES'"
    )


def test_fpbase_maps_the_renamed_parameters_and_keeps_the_public_names():
    tool = next(
        t for t in json.loads((DATA / "fpbase_tools.json").read_text("utf-8"))
        if t["name"] == "FPbase_search_by_spectrum"
    )
    mapping = tool["fields"]["param_mapping"]

    assert mapping == {
        "agg_exc_max__gte": "ex_max__gte",
        "agg_exc_max__lte": "ex_max__lte",
        "agg_em_max__gte": "em_max__gte",
        "agg_em_max__lte": "em_max__lte",
    }
    # A caller's argument names do not change.
    assert "agg_exc_max__gte" in tool["parameter"]["properties"]
