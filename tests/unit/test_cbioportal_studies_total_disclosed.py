"""Regression guard: cBioPortal paginated results must disclose the real total.

`cBioPortal_get_cancer_studies` defaults to `pageSize=20` while cBioPortal
holds 539 studies (verified live: `GET /api/studies` returns 539 records and
`GET /api/studies?projection=META` reports `Total-Count: 539`). The tool used
to answer with `count: 20` and nothing else, so a page read exactly like the
complete catalogue and a study at position 21 read as "not in cBioPortal".

The tool now reports `total_available` next to `count`, sets a top-level
`truncated` flag plus a `truncation_note`, and supports `offset` for paging.
`count` keeps its old meaning -- the number of records actually returned -- so
its meaning never flips depending on whether the page limit binds.
"""

from unittest.mock import MagicMock

import pytest

from tooluniverse.cbioportal_tool import CBioPortalRESTTool

pytestmark = pytest.mark.unit


def _studies_tool():
    return CBioPortalRESTTool(
        {
            "name": "cBioPortal_get_cancer_studies",
            "parameter": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "default": 20},
                    "offset": {"type": "integer", "default": 0},
                },
            },
            "fields": {
                "endpoint": "https://www.cbioportal.org/api/studies?pageSize={limit}"
            },
        }
    )


def _panels_tool():
    return CBioPortalRESTTool(
        {
            "name": "cBioPortal_get_gene_panels",
            "parameter": {
                "type": "object",
                "properties": {"page_size": {"type": "integer", "default": 50}},
            },
            "fields": {
                "endpoint": "https://www.cbioportal.org/api/gene-panels?pageSize={page_size}"
            },
        }
    )


def _fake_session(tool, *, page, total):
    """Route the data request and the projection=META total probe separately."""
    calls = []

    def _get(url, **kwargs):
        calls.append(url)
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.status_code = 200
        if "projection=META" in url:
            response.json.return_value = []
            response.headers = {"Total-Count": str(total)}
        else:
            response.json.return_value = page
            response.headers = {}
        return response

    tool.session.get = _get
    return calls


def test_truncated_study_page_reports_catalogue_total():
    tool = _studies_tool()
    page = [{"studyId": f"study_{i}"} for i in range(20)]
    calls = _fake_session(tool, page=page, total=539)

    result = tool.run({})

    assert result["status"] == "success"
    assert result["count"] == 20, "count must stay the number of records returned"
    assert result["total_available"] == 539
    assert result["truncated"] is True
    assert "539" in result["truncation_note"]
    assert "offset" in result["truncation_note"]
    # The total came from a dedicated META probe with the paging params
    # stripped -- /api/studies clamps the META count to pageSize otherwise.
    probe = [u for u in calls if "projection=META" in u]
    assert len(probe) == 1
    assert "pageSize" not in probe[0]


def test_complete_study_list_is_not_flagged_truncated():
    tool = _studies_tool()
    page = [{"studyId": f"study_{i}"} for i in range(539)]
    calls = _fake_session(tool, page=page, total=539)

    result = tool.run({"limit": 1000})

    assert result["count"] == 539
    assert result["total_available"] == 539
    assert result["truncated"] is False
    assert "truncation_note" not in result
    # A short page proves the set is exhausted, so no probe is spent.
    assert not [u for u in calls if "projection=META" in u]


def test_offset_pages_past_the_first_slice():
    tool = _studies_tool()
    page = [{"studyId": f"study_{i}"} for i in range(25)]
    _fake_session(tool, page=page, total=539)

    result = tool.run({"limit": 5, "offset": 20})

    assert [s["studyId"] for s in result["data"]] == [
        f"study_{i}" for i in range(20, 25)
    ]
    assert result["offset"] == 20
    assert result["count"] == 5
    assert result["total_available"] == 539
    assert result["truncated"] is True


def test_unknown_total_is_reported_as_unknown_not_invented():
    tool = _studies_tool()
    page = [{"studyId": f"study_{i}"} for i in range(20)]

    def _get(url, **kwargs):
        response = MagicMock()
        response.raise_for_status.return_value = None
        if "projection=META" in url:
            response.status_code = 503
            response.headers = {}
        else:
            response.status_code = 200
            response.json.return_value = page
            response.headers = {}
        return response

    tool.session.get = _get
    result = tool.run({})

    assert result["total_available"] is None
    assert result["truncated"] is True
    assert "did not report the total" in result["truncation_note"]


def test_sibling_paginated_tool_also_discloses_total():
    """The same silent-slice shape existed on the other paged endpoints."""
    tool = _panels_tool()
    page = [{"genePanelId": f"panel_{i}"} for i in range(50)]
    _fake_session(tool, page=page, total=69)

    result = tool.run({})

    assert result["count"] == 50
    assert result["total_available"] == 69
    assert result["truncated"] is True
    assert "page_size" in result["truncation_note"]


def test_unpaginated_endpoint_is_left_alone():
    """Endpoints with no pageSize return their whole set; no probe, no flags."""
    tool = CBioPortalRESTTool(
        {
            "name": "cBioPortal_get_cancer_types",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"endpoint": "https://www.cbioportal.org/api/cancer-types"},
        }
    )
    calls = _fake_session(tool, page=[{"cancerTypeId": "acc"}], total=897)

    result = tool.run({})

    assert result["count"] == 1
    assert "total_available" not in result
    assert "truncated" not in result
    assert not [u for u in calls if "projection=META" in u]
