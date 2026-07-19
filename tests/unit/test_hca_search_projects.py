"""Regression guard for two Fix-R24E bugs in HCATool.search_projects.

Fix-R24E-1 (disease filter facet name): the Azul HCA API rejects a
"disease" filter facet outright with a 400 "Additional properties are not
allowed ('disease' was unexpected)" error -- confirmed live. The real facet
name is "donorDisease". Every call passing `disease` previously errored.

Fix-R24E-2 (organ/donorDisease extraction): each hit's organ and disease
values live under nested "specimens"/"donorOrganisms" array fields, not
top-level "modelOrgan"/"donorDisease" dict keys -- confirmed live those
top-level keys don't exist at all, so reading them always silently
returned None regardless of the real data.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hca_tool import HCATool

pytestmark = pytest.mark.unit

_HIT = {
    "entryId": "894ae6ac-5b48-41a8-a72f-315a9b60a62e",
    "projects": [
        {"projectTitle": "A Single-Cell Transcriptome Atlas of the Human Pancreas."}
    ],
    "specimens": [{"organ": ["pancreas"], "disease": ["normal"]}],
    "donorOrganisms": [{"disease": ["normal"]}],
}


def _resp(json_body):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = json_body
    return r


class TestDiseaseFilterFacetName:
    def test_disease_arg_uses_donor_disease_facet(self):
        tool = HCATool({"name": "hca_test"})
        resp = _resp({"hits": [_HIT], "pagination": {"total": 1}})

        with patch("tooluniverse.hca_tool.requests.get", return_value=resp) as mock_get:
            tool.search_projects(organ="pancreas", disease="normal", limit=3)

        filters_param = mock_get.call_args.kwargs["params"]["filters"]
        assert '"donorDisease"' in filters_param
        assert '"disease": {"is"' not in filters_param.replace(" ", "")


class TestOrganAndDiseaseExtraction:
    def test_organ_and_disease_populated_from_nested_fields(self):
        tool = HCATool({"name": "hca_test"})
        resp = _resp({"hits": [_HIT], "pagination": {"total": 1}})

        with patch("tooluniverse.hca_tool.requests.get", return_value=resp):
            result = tool.search_projects(organ="pancreas", limit=3)

        project = result["projects"][0]
        assert project["organ"] == ["pancreas"]
        assert project["donorDisease"] == ["normal"]

    def test_missing_specimens_or_donors_does_not_crash(self):
        tool = HCATool({"name": "hca_test"})
        bare_hit = {"entryId": "x", "projects": [{}]}
        resp = _resp({"hits": [bare_hit], "pagination": {"total": 1}})

        with patch("tooluniverse.hca_tool.requests.get", return_value=resp):
            result = tool.search_projects(organ="pancreas", limit=3)

        project = result["projects"][0]
        assert project["organ"] is None
        assert project["donorDisease"] is None
