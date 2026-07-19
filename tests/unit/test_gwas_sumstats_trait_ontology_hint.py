"""Regression guard for Fix-R21E-2: GWASSumStats_get_trait_studies's 404
error for an unrecognized trait_id gave no hint about *why* -- a very
natural trap since a sibling database (PGS Catalog) uses MONDO ids for
the same diseases this API only recognizes by EFO id.

Confirmed live: trait_id=MONDO_0004975 (Alzheimer disease's MONDO id, as
returned by PGSCatalog_search_traits) 404s identically to a genuinely
nonexistent EFO id, while EFO_0000249 (the same disease's real EFO id)
works. Fixed by naming the likely cause when trait_id doesn't look like
an EFO id.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.gwas_sumstats_tool import GWASSumStatsTool

pytestmark = pytest.mark.unit


def _tool():
    return GWASSumStatsTool(
        {"name": "gwas_sumstats_test", "fields": {"endpoint_type": "get_trait_studies"}}
    )


def _resp(status_code, json_body=None):
    r = MagicMock()
    r.status_code = status_code
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body or {}
    return r


def test_non_efo_trait_id_gets_ontology_hint():
    tool = _tool()
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_resp(404)
    ):
        result = tool.run({"trait_id": "MONDO_0004975"})

    assert result["status"] == "error"
    assert "MONDO_0004975" in result["error"]
    assert "EFO" in result["error"]


def test_efo_shaped_but_nonexistent_trait_id_no_hint():
    """A trait_id that already looks like an EFO id but still 404s (a
    genuinely nonexistent EFO id) doesn't need the ontology-mismatch
    hint -- it's not a namespace problem."""
    tool = _tool()
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_resp(404)
    ):
        result = tool.run({"trait_id": "EFO_9999999"})

    assert result["status"] == "error"
    assert "EFO_9999999" in result["error"]
    assert "another ontology" not in result["error"]


def test_valid_efo_trait_id_succeeds():
    tool = _tool()
    body = {"_embedded": {"studies": [{"study_accession": "GCST002245"}]}}
    with patch(
        "tooluniverse.gwas_sumstats_tool.requests.get", return_value=_resp(200, body)
    ):
        result = tool.run({"trait_id": "EFO_0000249"})

    assert result["status"] == "success"
    assert result["data"][0]["study_accession"] == "GCST002245"
