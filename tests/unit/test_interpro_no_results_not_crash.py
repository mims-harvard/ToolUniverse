"""Regression guard: the EBI InterPro API answers a zero-hit search with
HTTP 204 No Content and a zero-length body, not a 200 carrying
{"count": 0, "results": []}.

``requests``' ``raise_for_status()`` treats 204 as success, so the tools fell
straight through to ``response.json()``, which raised a JSONDecodeError. That
escaped the blanket ``except Exception`` as an opaque internal error:

    Pfam_search_families {"query": "trypanothione"}
      -> Error: Unexpected error querying Pfam API:
         Expecting value: line 1 column 1 (char 0)

Confirmed live (2026-08):
    /entry/pfam/?search=trypanothione&page_size=20   -> HTTP 204, len(body)=0
    /entry/pfam/?search=kinase&page_size=5           -> HTTP 200
    /entry/interpro?search=zzzznotarealzzz           -> HTTP 204, len(body)=0

A caller could not distinguish "no such family" from "the tool is broken".
A 204 is now reported as a well-formed empty result set (status "success",
count 0, empty list), with the hit-producing shape left untouched.

These tests are offline: ``requests.get`` is patched in each module.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.interpro_entry_tool import InterProEntryTool
from tooluniverse.pfam_tool import PfamTool

pytestmark = pytest.mark.unit


def _no_content_response():
    """A response shaped like the real HTTP 204: empty body, .json() raises."""
    resp = MagicMock()
    resp.status_code = 204
    resp.text = ""
    resp.content = b""
    resp.raise_for_status.return_value = None
    # requests raises requests.exceptions.JSONDecodeError, a ValueError subclass.
    resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")
    return resp


def _ok_response(body):
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b'{"stub": true}'
    resp.raise_for_status.return_value = None
    resp.json.return_value = body
    return resp


def _pfam_search_tool():
    return PfamTool({"name": "Pfam_search_families", "fields": {"endpoint": "search_families"}})


def _interpro_search_tool():
    return InterProEntryTool(
        {"name": "InterPro_search_entries", "fields": {"endpoint": "search_entries"}}
    )


class TestPfamSearchFamiliesNoResults:
    def test_204_is_empty_success_not_error(self):
        tool = _pfam_search_tool()

        with patch(
            "tooluniverse.pfam_tool.requests.get", return_value=_no_content_response()
        ):
            result = tool.run({"query": "trypanothione"})

        assert result["status"] == "success"
        assert result["data"]["families"] == []
        assert result["data"]["total_results"] == 0
        assert result["data"]["returned"] == 0
        assert result["data"]["query"] == "trypanothione"

    def test_200_with_empty_body_is_also_empty_success(self):
        """Defensive: a 200 carrying no body must not crash either."""
        tool = _pfam_search_tool()
        resp = _no_content_response()
        resp.status_code = 200

        with patch("tooluniverse.pfam_tool.requests.get", return_value=resp):
            result = tool.run({"query": "trypanothione"})

        assert result["status"] == "success"
        assert result["data"]["total_results"] == 0
        assert result["data"]["families"] == []

    def test_hit_producing_response_shape_unchanged(self):
        tool = _pfam_search_tool()
        body = {
            "count": 304,
            "results": [
                {
                    "metadata": {
                        "accession": "PF00069",
                        "name": "Protein kinase domain",
                        "type": "domain",
                        "integrated": "IPR000719",
                    }
                }
            ],
        }

        with patch("tooluniverse.pfam_tool.requests.get", return_value=_ok_response(body)):
            result = tool.run({"query": "kinase"})

        assert result["status"] == "success"
        assert result["data"]["total_results"] == 304
        assert result["data"]["returned"] == 1
        assert result["data"]["families"] == [
            {
                "accession": "PF00069",
                "name": "Protein kinase domain",
                "type": "domain",
                "integrated_interpro": "IPR000719",
            }
        ]


class TestInterProSearchEntriesNoResults:
    def test_204_is_empty_success_not_error(self):
        tool = _interpro_search_tool()

        with patch(
            "tooluniverse.interpro_entry_tool.requests.get",
            return_value=_no_content_response(),
        ):
            result = tool.run({"query": "zzzznotarealfamilyzzzz"})

        assert result["status"] == "success"
        assert result["data"]["entries"] == []
        assert result["data"]["total_results"] == 0
        assert result["data"]["returned"] == 0
        assert result["data"]["query"] == "zzzznotarealfamilyzzzz"

    def test_200_with_empty_body_is_also_empty_success(self):
        tool = _interpro_search_tool()
        resp = _no_content_response()
        resp.status_code = 200

        with patch("tooluniverse.interpro_entry_tool.requests.get", return_value=resp):
            result = tool.run({"query": "zzzznotarealfamilyzzzz"})

        assert result["status"] == "success"
        assert result["data"]["total_results"] == 0
        assert result["data"]["entries"] == []

    def test_hit_producing_response_shape_unchanged(self):
        tool = _interpro_search_tool()
        body = {
            "count": 2,
            "results": [
                {
                    "metadata": {
                        "accession": "IPR000719",
                        "name": "Protein kinase domain",
                        "type": "domain",
                        "counters": {
                            "proteins": 1000,
                            "structures": 50,
                            "taxa": 20,
                        },
                    }
                }
            ],
        }

        with patch(
            "tooluniverse.interpro_entry_tool.requests.get",
            return_value=_ok_response(body),
        ):
            result = tool.run({"query": "kinase"})

        assert result["status"] == "success"
        assert result["data"]["total_results"] == 2
        assert result["data"]["returned"] == 1
        assert result["data"]["entries"] == [
            {
                "accession": "IPR000719",
                "name": "Protein kinase domain",
                "type": "domain",
                "protein_count": 1000,
                "structure_count": 50,
                "taxa_count": 20,
            }
        ]


class TestNoExceptionEscapes:
    """The failure mode was an exception leaking through the blanket handler."""

    def test_pfam_204_raises_nothing(self):
        tool = _pfam_search_tool()
        with patch(
            "tooluniverse.pfam_tool.requests.get", return_value=_no_content_response()
        ):
            result = tool.run({"query": "schistosoma"})
        assert "error" not in result

    def test_interpro_204_raises_nothing(self):
        tool = _interpro_search_tool()
        with patch(
            "tooluniverse.interpro_entry_tool.requests.get",
            return_value=_no_content_response(),
        ):
            result = tool.run({"query": "schistosoma"})
        assert "error" not in result
