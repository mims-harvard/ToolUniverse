"""Regression guard for Fix-R57-2: a merged HPO term returned an empty success
from the annotation tools, while the term tool in the same module already
detected the merge.

Confirmed live against the host the tool calls, ``ontology.jax.org``:

    HPO_get_diseases_by_phenotype {"term_id": "HP:0003114"} -> diseases [],
        total 0                    (HP:0003114 was merged into HP:0001626,
                                    which returns total 4962)
    HPO_get_term                  {"term_id": "HP:0003114"} -> already reports
        requested_id HP:0003114 / resolved_id HP:0001626 and a note

The annotation endpoint answers a merged ID with HTTP 200 and empty arrays --
``curl .../api/network/annotation/HP:0003114`` returns
``{"diseases":[],"genes":[],...}`` -- so upstream really has nothing to return
and the tool must disclose rather than recover. The detection already existed
one method away: ``/api/hp/terms/<id>`` silently serves the replacement term's
record, so a mismatch between the requested and returned id is the merge.

Cost: one extra request, on the empty path only.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.hpo_tool import HPOTool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return HPOTool(
        {"name": f"hpo_{endpoint}", "type": "HPOTool", "fields": {"endpoint": endpoint}}
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


MERGED_TERM = {"id": "HP:0001626", "name": "Abnormality of the cardiovascular system"}
LIVE_TERM = {"id": "HP:0003114", "name": "a term nobody has annotated"}
NO_ANNOTATIONS = {"diseases": [], "genes": [], "assays": [], "medicalActions": []}

ANNOTATION_ENDPOINTS = ["get_associated_diseases", "get_associated_genes"]


def _dispatch(term_payload, annotations=NO_ANNOTATIONS, calls=None):
    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        if "/network/annotation/" in url:
            return _resp(annotations)
        return _resp(term_payload)

    return fake_get


class TestMergedTermDisclosure:
    @pytest.mark.parametrize("endpoint", ANNOTATION_ENDPOINTS)
    def test_empty_annotations_report_the_replacement_term(self, endpoint):
        with patch(
            "tooluniverse.hpo_tool.requests.get", side_effect=_dispatch(MERGED_TERM)
        ):
            result = _tool(endpoint).run({"term_id": "HP:0003114"})

        assert result["status"] == "success"
        metadata = result["metadata"]
        assert metadata["total"] == 0
        assert metadata["requested_id"] == "HP:0003114"
        assert metadata["resolved_id"] == "HP:0001626"
        assert "merged into HP:0001626" in metadata["note"]

    @pytest.mark.parametrize("endpoint", ANNOTATION_ENDPOINTS)
    def test_live_term_with_no_annotations_is_not_called_merged(self, endpoint):
        with patch(
            "tooluniverse.hpo_tool.requests.get", side_effect=_dispatch(LIVE_TERM)
        ):
            result = _tool(endpoint).run({"term_id": "HP:0003114"})

        assert result["metadata"]["total"] == 0
        assert "resolved_id" not in result["metadata"]
        assert "note" not in result["metadata"]

    def test_populated_annotations_cost_no_extra_request(self):
        calls = []
        annotations = {"diseases": [{"id": "OMIM:1", "name": "d", "mondoId": None}]}
        with patch(
            "tooluniverse.hpo_tool.requests.get",
            side_effect=_dispatch(MERGED_TERM, annotations=annotations, calls=calls),
        ):
            result = _tool("get_associated_diseases").run({"term_id": "HP:0003114"})

        assert result["metadata"]["total"] == 1
        assert "resolved_id" not in result["metadata"]
        assert not any("/terms/" in u for u in calls), calls

    def test_probe_failure_leaves_the_empty_result_intact(self):
        def fake_get(url, **kwargs):
            if "/network/annotation/" in url:
                return _resp(NO_ANNOTATIONS)
            raise OSError("jax down")

        with patch("tooluniverse.hpo_tool.requests.get", side_effect=fake_get):
            result = _tool("get_associated_genes").run({"term_id": "HP:0003114"})

        assert result["status"] == "success"
        assert result["data"] == {"genes": []}
        assert "resolved_id" not in result["metadata"]

    def test_get_term_note_is_unchanged(self):
        """The wording moved into a shared helper; it must not have drifted."""
        with patch(
            "tooluniverse.hpo_tool.requests.get", return_value=_resp(MERGED_TERM)
        ):
            result = _tool("get_term").run({"term_id": "HP:0003114"})

        metadata = result["metadata"]
        assert metadata["requested_id"] == "HP:0003114"
        assert metadata["resolved_id"] == "HP:0001626"
        assert metadata["note"].startswith(
            "The requested term ID (HP:0003114) differs from the returned "
            "term's ID (HP:0001626)."
        )
