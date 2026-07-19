"""Regression guard for Fix-R25C-1: OmicsDI_search_datasets's
omics_type/organism/tissue filters were sent as separate query params,
which the upstream API silently ignores -- confirmed live that
`?query=KLK3&omics_type=Proteomics` still returned Transcriptomics-
dominated results identical to an unfiltered search, while folding the
filter into the Lucene query string (`query AND omics_type:"Proteomics"`)
correctly narrowed results (58182 -> 62 total hits for an organism
filter, verified separately). Fixed by building the composite query
string in Python before delegating to BaseRESTTool.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.omicsdi_tool import OmicsDITool

pytestmark = pytest.mark.unit


def _tool():
    return OmicsDITool(
        {
            "name": "OmicsDI_search_datasets",
            "fields": {"endpoint": "https://www.omicsdi.org/ws/dataset/search"},
            "parameter": {"properties": {}},
        }
    )


def _resp(json_body):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = json_body
    r.headers = {"content-type": "application/json"}
    return r


class TestFilterFolding:
    def test_omics_type_folded_into_query_string(self):
        tool = _tool()
        resp = _resp({"count": 1, "datasets": [], "facets": []})

        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ) as mock_request:
            tool.run({"query": "KLK3", "omics_type": "Proteomics", "size": 5})

        sent_params = mock_request.call_args.kwargs["params"]
        assert sent_params["query"] == 'KLK3 AND omics_type:"Proteomics"'
        assert "omics_type" not in sent_params

    def test_all_three_filters_folded_together(self):
        tool = _tool()
        resp = _resp({"count": 1, "datasets": [], "facets": []})

        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ) as mock_request:
            tool.run(
                {
                    "query": "insulin",
                    "omics_type": "Proteomics",
                    "organism": "Mus musculus",
                    "tissue": "liver",
                }
            )

        sent_params = mock_request.call_args.kwargs["params"]
        assert sent_params["query"] == (
            'insulin AND omics_type:"Proteomics" AND organism:"Mus musculus" '
            'AND tissue:"liver"'
        )
        assert "organism" not in sent_params
        assert "tissue" not in sent_params

    def test_no_filters_leaves_query_unchanged(self):
        tool = _tool()
        resp = _resp({"count": 1, "datasets": [], "facets": []})

        with patch(
            "tooluniverse.base_rest_tool.request_with_retry", return_value=resp
        ) as mock_request:
            tool.run({"query": "Alzheimer brain"})

        sent_params = mock_request.call_args.kwargs["params"]
        assert sent_params["query"] == "Alzheimer brain"
