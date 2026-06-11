"""
Unit tests for the clinical-imaging-archives depth tools (mocked HTTP).

Covers the drill-down / faceting / provenance tools added to close coverage
gaps for TCIA (The Cancer Imaging Archive, NBIA REST API) and OpenNeuro
(GraphQL). Each tool gets a parse test (success path with real verified IDs
in the mocked payload) and an error-path test. No live network access is used;
all HTTP calls are patched.

Tools under test:
- TCIA_get_patients                 (BaseRESTTool, getPatient)
- TCIA_get_sop_instance_uids        (BaseRESTTool, getSOPInstanceUIDs)
- TCIA_get_manufacturer_values      (BaseRESTTool, getManufacturerValues)
- OpenNeuro_get_snapshot_files      (OpenNeuroTool, snapshot.files)
- OpenNeuro_get_snapshot_validation (OpenNeuroTool, snapshot.validation)
- OpenNeuro_advanced_search         (OpenNeuroTool, participantCount + advancedSearch)
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


def _mock_response(json_payload=None, status_code=200, text=None):
    """Build a MagicMock standing in for a requests.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.ok = 200 <= status_code < 300
    resp.headers = {"content-type": "application/json"}
    resp.json.return_value = json_payload if json_payload is not None else {}
    if text is not None:
        resp.text = text
    else:
        resp.text = json.dumps(json_payload) if json_payload is not None else ""
    resp.raise_for_status.return_value = None
    return resp


# --------------------------------------------------------------------------- #
# TCIA_get_patients  (BaseRESTTool via request_with_retry)
# --------------------------------------------------------------------------- #
class TestTCIAGetPatients:
    def _tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        return BaseRESTTool(_load_config("tcia_tools.json", "TCIA_get_patients"))

    def test_parse_success(self):
        """Success path: getPatient payload parses with patient-level fields."""
        payload = [
            {
                "PatientId": "LIDC-IDRI-0001",
                "PatientName": "",
                "Collection": "LIDC-IDRI",
                "Phantom": "NO",
                "SpeciesCode": "337915000",
                "SpeciesDescription": "Homo sapiens",
            },
            {
                "PatientId": "LIDC-IDRI-0002",
                "PatientName": "",
                "Collection": "LIDC-IDRI",
                "Phantom": "NO",
                "SpeciesCode": "337915000",
                "SpeciesDescription": "Homo sapiens",
            },
        ]
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"Collection": "LIDC-IDRI"})

        # Collection must be forwarded as a query param to getPatient.
        called_url = mocked.call_args[0][2]
        assert called_url.endswith("/getPatient")
        params = mocked.call_args.kwargs["params"]
        assert params.get("Collection") == "LIDC-IDRI"

        assert result["status"] == "success"
        assert result["count"] == 2
        first = result["data"][0]
        assert first["PatientId"] == "LIDC-IDRI-0001"
        assert first["Phantom"] == "NO"
        assert first["SpeciesCode"] == "337915000"
        assert first["SpeciesDescription"] == "Homo sapiens"

    def test_error_path(self):
        """Error path: non-2xx HTTP yields a status=error envelope, no raise."""
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response({"message": "bad"}, status_code=500),
        ):
            result = tool.run({"Collection": "NO-SUCH-COLLECTION"})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# TCIA_get_sop_instance_uids  (BaseRESTTool via request_with_retry)
# --------------------------------------------------------------------------- #
class TestTCIAGetSopInstanceUids:
    SERIES = "1.3.6.1.4.1.14519.5.2.1.6279.6001.179049373636438705059720603192"

    def _tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        return BaseRESTTool(
            _load_config("tcia_tools.json", "TCIA_get_sop_instance_uids")
        )

    def test_parse_success(self):
        """Success path: getSOPInstanceUIDs returns per-image SOP UID objects."""
        payload = [
            {
                "SOPInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.143451261327128179989900675595"
            },
            {
                "SOPInstanceUID": "1.3.6.1.4.1.14519.5.2.1.6279.6001.000000000000000000000000000002"
            },
        ]
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"SeriesInstanceUID": self.SERIES})

        called_url = mocked.call_args[0][2]
        assert called_url.endswith("/getSOPInstanceUIDs")
        params = mocked.call_args.kwargs["params"]
        assert params.get("SeriesInstanceUID") == self.SERIES

        assert result["status"] == "success"
        assert result["count"] == 2
        assert (
            result["data"][0]["SOPInstanceUID"]
            == "1.3.6.1.4.1.14519.5.2.1.6279.6001.143451261327128179989900675595"
        )

    def test_error_path(self):
        """Error path: non-2xx HTTP yields a status=error envelope, no raise."""
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response({"message": "bad"}, status_code=400),
        ):
            result = tool.run({"SeriesInstanceUID": "not-a-real-uid"})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# TCIA_get_manufacturer_values  (BaseRESTTool via request_with_retry)
# --------------------------------------------------------------------------- #
class TestTCIAGetManufacturerValues:
    def _tool(self):
        from tooluniverse.base_rest_tool import BaseRESTTool

        return BaseRESTTool(
            _load_config("tcia_tools.json", "TCIA_get_manufacturer_values")
        )

    def test_parse_success(self):
        """Success path: getManufacturerValues returns distinct manufacturers."""
        payload = [
            {"Manufacturer": "GE MEDICAL SYSTEMS"},
            {"Manufacturer": "Philips"},
            {"Manufacturer": "SIEMENS"},
            {"Manufacturer": "TOSHIBA"},
        ]
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"Collection": "LIDC-IDRI", "Modality": "CT"})

        called_url = mocked.call_args[0][2]
        assert called_url.endswith("/getManufacturerValues")
        params = mocked.call_args.kwargs["params"]
        assert params.get("Collection") == "LIDC-IDRI"
        assert params.get("Modality") == "CT"

        assert result["status"] == "success"
        assert result["count"] == 4
        names = [m["Manufacturer"] for m in result["data"]]
        assert "GE MEDICAL SYSTEMS" in names
        assert "SIEMENS" in names

    def test_error_path(self):
        """Error path: non-2xx HTTP yields a status=error envelope, no raise."""
        tool = self._tool()
        with patch(
            "tooluniverse.base_rest_tool.request_with_retry",
            return_value=_mock_response({"message": "bad"}, status_code=500),
        ):
            result = tool.run({"Collection": "LIDC-IDRI"})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# OpenNeuro_get_snapshot_files  (OpenNeuroTool -> GraphQLTool.execute_query)
# --------------------------------------------------------------------------- #
class TestOpenNeuroGetSnapshotFiles:
    def _tool(self):
        from tooluniverse.openneuro_tool import OpenNeuroTool

        return OpenNeuroTool(
            _load_config("openneuro_tools.json", "OpenNeuro_get_snapshot_files")
        )

    def test_parse_success(self):
        """Success path: snapshot.files returns file manifest with download URLs."""
        payload = {
            "data": {
                "snapshot": {
                    "id": "ds000001:00006",
                    "tag": "00006",
                    "files": [
                        {
                            "filename": "dataset_description.json",
                            "size": 965,
                            "directory": False,
                            "urls": [
                                "https://openneuro.org/crn/datasets/ds000001/objects/d21a47a8"
                            ],
                        },
                        {
                            "filename": "sub-01",
                            "size": 0,
                            "directory": True,
                            "urls": [],
                        },
                    ],
                }
            }
        }
        tool = self._tool()
        # OpenNeuroTool delegates to GraphQLTool.execute_query, which posts via
        # the graphql_tool module's requests handle.
        with patch(
            "tooluniverse.graphql_tool.requests.post",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"datasetId": "ds000001", "tag": "00006"})

        sent = mocked.call_args.kwargs["json"]
        assert sent["variables"]["datasetId"] == "ds000001"
        assert sent["variables"]["tag"] == "00006"

        assert result["status"] == "success"
        snap = result["data"]["snapshot"]
        assert snap["tag"] == "00006"
        files = snap["files"]
        assert files[0]["filename"] == "dataset_description.json"
        assert files[0]["size"] == 965
        assert files[0]["urls"][0].startswith("https://openneuro.org/")

    def test_error_path(self):
        """Error path: GraphQL errors yield a status=error envelope."""
        tool = self._tool()
        # GraphQL errors -> execute_query returns None -> status=error envelope.
        with patch(
            "tooluniverse.graphql_tool.requests.post",
            return_value=_mock_response({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"datasetId": "ds999999", "tag": "00001"})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# OpenNeuro_get_snapshot_validation  (OpenNeuroTool -> GraphQLTool.execute_query)
# --------------------------------------------------------------------------- #
class TestOpenNeuroGetSnapshotValidation:
    def _tool(self):
        from tooluniverse.openneuro_tool import OpenNeuroTool

        return OpenNeuroTool(
            _load_config("openneuro_tools.json", "OpenNeuro_get_snapshot_validation")
        )

    def test_parse_success(self):
        """Success path: snapshot.validation returns BIDS error/warning counts."""
        payload = {
            "data": {
                "snapshot": {
                    "id": "ds000001:00006",
                    "tag": "00006",
                    "issuesStatus": {"errors": 0, "warnings": 2},
                    "validation": {"errors": 1, "warnings": 2556},
                }
            }
        }
        tool = self._tool()
        with patch(
            "tooluniverse.graphql_tool.requests.post",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"datasetId": "ds000001", "tag": "00006"})

        sent = mocked.call_args.kwargs["json"]
        assert sent["variables"]["datasetId"] == "ds000001"
        assert sent["variables"]["tag"] == "00006"

        assert result["status"] == "success"
        snap = result["data"]["snapshot"]
        assert snap["issuesStatus"]["errors"] == 0
        assert snap["issuesStatus"]["warnings"] == 2
        assert snap["validation"]["errors"] == 1
        assert snap["validation"]["warnings"] == 2556

    def test_error_path(self):
        """Error path: GraphQL errors yield a status=error envelope."""
        tool = self._tool()
        with patch(
            "tooluniverse.graphql_tool.requests.post",
            return_value=_mock_response({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"datasetId": "ds999999", "tag": "00001"})
        assert result["status"] == "error"
        assert "error" in result


# --------------------------------------------------------------------------- #
# OpenNeuro_advanced_search  (OpenNeuroTool._run_advanced_search)
# --------------------------------------------------------------------------- #
class TestOpenNeuroAdvancedSearch:
    def _tool(self):
        from tooluniverse.openneuro_tool import OpenNeuroTool

        return OpenNeuroTool(
            _load_config("openneuro_tools.json", "OpenNeuro_advanced_search")
        )

    def test_parse_success_assembles_query_object(self):
        """Flat facet args are collected into the DatasetSearchInput $query var."""
        payload = {
            "data": {
                "participantCount": 79790,
                "advancedSearch": {
                    "pageInfo": {"count": 1599},
                    "edges": [{"node": {"id": "ds007955"}}],
                },
            }
        }
        tool = self._tool()
        # advancedSearch uses the openneuro_tool module's own requests.post.
        with patch(
            "tooluniverse.openneuro_tool.requests.post",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({"species": "human", "first": 3})

        sent = mocked.call_args.kwargs["json"]
        # facet args go into the query object; non-facet args stay top-level.
        assert sent["variables"]["query"] == {"species": "human"}
        assert sent["variables"]["first"] == 3

        assert result["status"] == "success"
        assert result["data"]["participantCount"] == 79790
        assert result["data"]["advancedSearch"]["pageInfo"]["count"] == 1599
        assert result["data"]["advancedSearch"]["edges"][0]["node"]["id"] == "ds007955"

    def test_empty_facets_sends_empty_query_object(self):
        """No facet args -> empty DatasetSearchInput matching the whole archive."""
        payload = {
            "data": {
                "participantCount": 79790,
                "advancedSearch": {"pageInfo": {"count": 3130}, "edges": []},
            }
        }
        tool = self._tool()
        with patch(
            "tooluniverse.openneuro_tool.requests.post",
            return_value=_mock_response(payload),
        ) as mocked:
            result = tool.run({})

        sent = mocked.call_args.kwargs["json"]
        assert sent["variables"]["query"] == {}
        assert result["status"] == "success"
        assert result["data"]["advancedSearch"]["pageInfo"]["count"] == 3130

    def test_partial_data_with_permission_errors_is_kept(self):
        """Partial data + per-dataset errors -> success with an explanatory note."""
        payload = {
            "data": {
                "participantCount": 79790,
                "advancedSearch": {
                    "pageInfo": {"count": 1599},
                    "edges": [{"node": {"id": "ds007955"}}, None],
                },
            },
            "errors": [{"message": "You do not have access to read this dataset."}],
        }
        tool = self._tool()
        with patch(
            "tooluniverse.openneuro_tool.requests.post",
            return_value=_mock_response(payload),
        ):
            result = tool.run({"species": "human", "first": 3})

        assert result["status"] == "success"
        assert result["data"]["participantCount"] == 79790
        assert result["data"]["advancedSearch"]["pageInfo"]["count"] == 1599
        assert "note" in result["metadata"]

    def test_error_path_http(self):
        """Error path: non-2xx HTTP yields a status=error envelope."""
        tool = self._tool()
        with patch(
            "tooluniverse.openneuro_tool.requests.post",
            return_value=_mock_response({"message": "boom"}, status_code=500),
        ):
            result = tool.run({"species": "human"})
        assert result["status"] == "error"
        assert "error" in result

    def test_error_path_no_data(self):
        """Fatal GraphQL error with no usable data -> status=error."""
        tool = self._tool()
        with patch(
            "tooluniverse.openneuro_tool.requests.post",
            return_value=_mock_response({"errors": [{"message": "boom"}]}),
        ):
            result = tool.run({"species": "human"})
        assert result["status"] == "error"
        assert "error" in result
