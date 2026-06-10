"""
Unit tests for the cell-imaging depth tools (mocked HTTP).

Covers the drill-down / provenance tools added to close cell-imaging coverage
gaps. Each tool gets a parse test (success path, real verified IDs in the
mocked payload) and an error-path test. No live network access is used here;
all HTTP calls are patched.

Tools under test:
- IDR_list_dataset_images          (BaseRESTTool, GET dataset -> images)
- IDR_get_image_map_annotations    (BaseRESTTool, GET image map annotations)
- BioImageArchive_list_study_files (BioImageArchiveTool, action list_study_files)
- HuBMAP_get_dataset_provenance    (HuBMAPTool, operation get_provenance)
- CryoET_list_tiltseries           (CryoETTool, operation list_tiltseries)
- CryoET_list_depositions          (CryoETTool, operation list_depositions)
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit

DATA_DIR = Path(__file__).parent.parent.parent / "src" / "tooluniverse" / "data"


def _load_config(filename, tool_name):
    with open(DATA_DIR / filename) as f:
        tools = json.load(f)
    by_name = {t["name"]: t for t in tools}
    assert tool_name in by_name, f"{tool_name} missing from {filename}"
    return by_name[tool_name]


def _mock_response(json_payload=None, status_code=200, raise_for_status=False):
    """Build a MagicMock standing in for a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = json_payload if json_payload is not None else {}
    resp.text = json.dumps(json_payload) if json_payload is not None else ""
    if raise_for_status:
        import requests

        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


# --------------------------------------------------------------------------- #
# IDR_list_dataset_images  (BaseRESTTool via request_with_retry)
# --------------------------------------------------------------------------- #
class TestIDRListDatasetImages:
    def _tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        return BaseRESTTool(_load_config("idr_tools.json", "IDR_list_dataset_images"))

    def test_parse_success(self):
        """Success path: mocked payload parses into the documented envelope."""
        payload = {
            "data": [
                {"@id": 1884807, "Name": "img1"},
                {"@id": 1884808, "Name": "img2"},
            ],
            "meta": {"offset": 0, "limit": 5, "maxLimit": 1000, "totalCount": 33},
        }
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"dataset_id": 51, "limit": 5})

        # Endpoint path substitution must put the dataset id in the URL.
        called_url = mocked.call_args[0][2]
        assert "/datasets/51/images/" in called_url

        assert result["status"] == "success"
        inner = result["data"]
        assert inner["meta"]["totalCount"] == 33
        assert [x["@id"] for x in inner["data"]] == [1884807, 1884808]

    def test_error_path(self):
        """Error path: non-2xx HTTP yields a status=error envelope, no raise."""
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response({"message": "not found"}, status_code=404),
        ):
            result = tool.run({"dataset_id": 999999999, "limit": 5})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# IDR_get_image_map_annotations  (BaseRESTTool via request_with_retry)
# --------------------------------------------------------------------------- #
class TestIDRGetImageMapAnnotations:
    def _tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        return BaseRESTTool(
            _load_config("idr_tools.json", "IDR_get_image_map_annotations")
        )

    def test_parse_success(self):
        """Success path: mocked payload parses into the documented envelope."""
        payload = {
            "annotations": [
                {"id": 1, "values": [["Cell Line", "HeLa"]]},
                {"id": 2, "values": [["Gene Symbol", "CDK5RAP2"]]},
                {"id": 3, "values": [["Gene Identifier", "ENSG00000136861"]]},
                {"id": 4, "values": [["Antibody Target", "CDK5RAP2-C"]]},
            ],
            "experimenters": [],
        }
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"image": 1884807})

        # type=map default param and the image query param must be forwarded.
        params = mocked.call_args.kwargs["params"]
        assert params.get("type") == "map"
        assert params.get("image") == 1884807

        assert result["status"] == "success"
        anns = result["data"]["annotations"]
        assert len(anns) == 4
        flat = [v for a in anns for v in a["values"]]
        assert ["Cell Line", "HeLa"] in flat
        assert ["Gene Symbol", "CDK5RAP2"] in flat
        assert ["Gene Identifier", "ENSG00000136861"] in flat

    def test_error_path(self):
        """Error path: non-2xx HTTP yields a status=error envelope, no raise."""
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response({"message": "bad request"}, status_code=400),
        ):
            result = tool.run({"image": -1})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# BioImageArchive_list_study_files  (BioImageArchiveTool)
# --------------------------------------------------------------------------- #
class TestBioImageArchiveListStudyFiles:
    def _tool(self):
        from tooluniverse.bioimage_archive_tool import BioImageArchiveTool

        return BioImageArchiveTool(
            _load_config("bioimage_archive_tools.json", "BioImageArchive_list_study_files")
        )

    def test_parse_success(self):
        """Success path: mocked payload parses into the documented envelope."""
        payload = {
            "recordsTotal": 223,
            "data": [
                {
                    "Name": "experimentA_01_WT_PDMP.czi",
                    "Size": "1577024",
                    "Section": "StudyComponent-1",
                    "staining": "click chemistry and IF",
                    "cells": "WT",
                    "treatment": "20 µM PDMP",
                    "Channel_1": "pacSph",
                    "Channel_2": "Lamp1",
                    "timepoint": "continuous labelling",
                    "path": "experiments/experimentA_01_WT_PDMP.czi",
                    "type": "file",
                    "size": 1577024,
                }
            ],
        }
        tool = self._tool()
        with patch("requests.get", return_value=_mock_response(payload)) as mocked:
            result = tool.run({"accession": "S-BIAD144", "limit": 5})

        url = mocked.call_args[0][0]
        assert url.endswith("/files/S-BIAD144")
        assert mocked.call_args.kwargs["params"]["length"] == 5

        assert result["status"] == "success"
        assert result["metadata"]["records_total"] == 223
        row = result["data"][0]
        assert row["Name"] == "experimentA_01_WT_PDMP.czi"
        assert row["path"] == "experiments/experimentA_01_WT_PDMP.czi"
        assert row["size"] == 1577024
        anns = row["annotations"]
        assert anns["staining"] == "click chemistry and IF"
        assert anns["cells"] == "WT"
        assert anns["Channel_1"] == "pacSph"
        assert anns["Channel_2"] == "Lamp1"
        # Structural keys must not leak into the annotations bag.
        assert "Name" not in anns
        assert "path" not in anns

    def test_error_missing_accession(self):
        """Missing required accession returns a status=error envelope."""
        tool = self._tool()
        result = tool.run({"limit": 5})
        assert result["status"] == "error"
        assert "accession" in result["error"]

    def test_error_http(self):
        """Upstream HTTP error is caught and returned as status=error."""
        tool = self._tool()
        with patch(
            "requests.get",
            return_value=_mock_response({}, status_code=500, raise_for_status=True),
        ):
            result = tool.run({"accession": "S-BIADXXXX"})
        assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# HuBMAP_get_dataset_provenance  (HuBMAPTool)
# --------------------------------------------------------------------------- #
class TestHuBMAPGetDatasetProvenance:
    def _tool(self):
        from tooluniverse.hubmap_tool import HuBMAPTool

        return HuBMAPTool(
            _load_config("hubmap_tools.json", "HuBMAP_get_dataset_provenance")
        )

    def test_parse_success_orders_lineage(self):
        """Success path: shuffled ancestors are re-ordered Dataset->Sample->Donor."""
        # Deliberately shuffled so the test proves the tool re-orders the chain
        # Dataset -> Sample(section -> block -> organ) -> Donor.
        ancestors = [
            {"entity_type": "Sample", "hubmap_id": "HBM865.MWHF.489",
             "uuid": "u-organ", "sample_category": "organ", "organ": "LK"},
            {"entity_type": "Donor", "hubmap_id": "HBM758.JRSC.348", "uuid": "u-donor"},
            {"entity_type": "Dataset", "hubmap_id": "HBM386.RVHN.555",
             "uuid": "u-ds", "dataset_type": "Auto-fluorescence"},
            {"entity_type": "Sample", "hubmap_id": "HBM364.WDPC.959",
             "uuid": "u-block", "sample_category": "block"},
            {"entity_type": "Sample", "hubmap_id": "HBM522.MQPX.944",
             "uuid": "u-section", "sample_category": "section"},
        ]
        tool = self._tool()
        with patch("requests.get", return_value=_mock_response(ancestors)) as mocked:
            result = tool.run({"uuid": "b1ca0a28b39e5ee6a252403e03247db6"})

        url = mocked.call_args[0][0]
        assert url.endswith("/ancestors/b1ca0a28b39e5ee6a252403e03247db6")

        assert result["status"] == "success"
        data = result["data"]
        assert data["ancestor_count"] == 5
        ordered = [(e["entity_type"], e["hubmap_id"]) for e in data["lineage"]]
        assert ordered == [
            ("Dataset", "HBM386.RVHN.555"),
            ("Sample", "HBM522.MQPX.944"),
            ("Sample", "HBM364.WDPC.959"),
            ("Sample", "HBM865.MWHF.489"),
            ("Donor", "HBM758.JRSC.348"),
        ]
        organ_entry = [e for e in data["lineage"] if e["sample_category"] == "organ"][0]
        assert organ_entry["organ"] == "LK"

    def test_error_missing_uuid(self):
        """Missing required uuid returns a status=error envelope."""
        tool = self._tool()
        result = tool.run({})
        assert result["status"] == "error"

    def test_error_not_found(self):
        """404 from the entity API returns a status=error envelope."""
        tool = self._tool()
        with patch("requests.get", return_value=_mock_response({}, status_code=404)):
            result = tool.run({"uuid": "deadbeef"})
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()


# --------------------------------------------------------------------------- #
# CryoET_list_tiltseries  (CryoETTool)
# --------------------------------------------------------------------------- #
class TestCryoETListTiltseries:
    def _tool(self):
        from tooluniverse.cryoet_tool import CryoETTool

        return CryoETTool(_load_config("cryoet_tools.json", "CryoET_list_tiltseries"))

    def test_parse_success(self):
        """Success path: mocked payload parses into the documented envelope."""
        gql_payload = {
            "data": {
                "tiltseries": [
                    {
                        "id": 8009,
                        "runId": 8260,
                        "microscopeManufacturer": "TFS",
                        "microscopeModel": "Krios",
                        "accelerationVoltage": 300000,
                        "tiltMin": -65.0,
                        "tiltMax": 65.0,
                        "tiltStep": 1.0,
                        "totalFlux": 120.0,
                        "cameraModel": "K2",
                        "dataAcquisitionSoftware": "UCSFTomo",
                        "httpsMrcFile": "https://files/ts.mrc",
                    }
                ]
            }
        }
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response(gql_payload),
        ) as mocked:
            result = tool.run({"operation": "list_tiltseries", "limit": 1})

        # Query body should request the tiltseries collection.
        body = mocked.call_args.kwargs["json"]["query"]
        assert "tiltseries(" in body

        assert result["status"] == "success"
        assert result["data"]["count"] == 1
        ts = result["data"]["tiltseries"][0]
        assert ts["id"] == 8009
        assert ts["runId"] == 8260
        assert ts["microscopeModel"] == "Krios"
        assert ts["accelerationVoltage"] == 300000
        assert ts["totalFlux"] == 120.0
        assert ts["httpsMrcFile"]

    def test_run_id_filter_injected(self):
        """run_id is injected as a GraphQL where-filter on runId."""
        gql_payload = {"data": {"tiltseries": []}}
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response(gql_payload),
        ) as mocked:
            result = tool.run(
                {"operation": "list_tiltseries", "run_id": 8260, "limit": 2}
            )
        body = mocked.call_args.kwargs["json"]["query"]
        assert "runId: {_eq: 8260}" in body
        assert result["status"] == "success"
        assert result["data"]["run_id"] == 8260

    def test_error_graphql(self):
        """GraphQL-level errors are surfaced as a status=error envelope."""
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"operation": "list_tiltseries", "limit": 1})
        assert result["status"] == "error"


# --------------------------------------------------------------------------- #
# CryoET_list_depositions  (CryoETTool)
# --------------------------------------------------------------------------- #
class TestCryoETListDepositions:
    def _tool(self):
        from tooluniverse.cryoet_tool import CryoETTool

        return CryoETTool(_load_config("cryoet_tools.json", "CryoET_list_depositions"))

    def test_parse_success(self):
        """Success path: mocked payload parses into the documented envelope."""
        gql_payload = {
            "data": {
                "depositions": [
                    {
                        "id": 10014,
                        "title": "Dolichospermum flos-aquae ... by Przemek Dutka",
                        "relatedDatabaseEntries": "EMD-29922,EMD-29923,EMD-29924,EMD-29925",
                    },
                    {
                        "id": 10019,
                        "title": "Bacillus subtilis ...",
                        "relatedDatabaseEntries": None,
                    },
                ]
            }
        }
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response(gql_payload),
        ) as mocked:
            result = tool.run({"operation": "list_depositions", "limit": 2})

        body = mocked.call_args.kwargs["json"]["query"]
        assert "depositions(" in body

        assert result["status"] == "success"
        assert result["data"]["count"] == 2
        deps = result["data"]["depositions"]
        assert deps[0]["id"] == 10014
        assert deps[0]["relatedDatabaseEntries"].startswith("EMD-29922")
        assert deps[1]["id"] == 10019

    def test_deposition_id_filter_injected(self):
        """deposition_id is injected as a GraphQL where-filter on id."""
        gql_payload = {"data": {"depositions": []}}
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response(gql_payload),
        ) as mocked:
            result = tool.run(
                {"operation": "list_depositions", "deposition_id": 10014}
            )
        body = mocked.call_args.kwargs["json"]["query"]
        assert "id: {_eq: 10014}" in body
        assert result["status"] == "success"

    def test_error_graphql(self):
        """GraphQL-level errors are surfaced as a status=error envelope."""
        tool = self._tool()
        with patch(
            "tooluniverse.cryoet_tool.requests.post",
            return_value=_mock_response({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"operation": "list_depositions", "limit": 2})
        assert result["status"] == "error"
