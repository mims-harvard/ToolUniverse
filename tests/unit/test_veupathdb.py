"""VEuPathDB WDK POST tools.

Covers POST body construction, project -> (subdir, project_id) mapping,
report/record parsing, and error paths (missing input, unknown project,
HTTP error, empty record) using mocks — no live VEuPathDB calls.
"""

import json
import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _search_tool(project_default=None):
    from tooluniverse.veupathdb_tool import VEuPathDBTool

    return VEuPathDBTool(
        {
            "name": "VEuPathDB_search_genes_by_organism",
            "type": "VEuPathDBTool",
            "fields": {"operation": "search_genes_by_organism"},
        }
    )


def _record_tool():
    from tooluniverse.veupathdb_tool import VEuPathDBTool

    return VEuPathDBTool(
        {
            "name": "VEuPathDB_get_gene_record",
            "type": "VEuPathDBTool",
            "fields": {"operation": "get_gene_record"},
        }
    )


def _resp(status_code=200, json_body=None, text=""):
    r = MagicMock()
    r.status_code = status_code
    r.text = text
    if json_body is None:
        r.json.side_effect = ValueError("no json")
    else:
        r.json.return_value = json_body
    r.raise_for_status = MagicMock()
    return r


SEARCH_PAYLOAD = {
    "records": [
        {
            "id": [
                {"name": "source_id", "value": "PF3D7_0100100"},
                {"name": "project_id", "value": "PlasmoDB"},
            ],
            "attributes": {
                "primary_key": "PF3D7_0100100",
                "product": "erythrocyte membrane protein 1, PfEMP1",
                "organism": "<i>P. falciparum 3D7</i>",
                "gene_type": "protein coding gene",
            },
        }
    ],
    "meta": {"totalCount": 5720},
}

RECORD_PAYLOAD = {
    "id": [{"name": "source_id", "value": "PF3D7_0417200"}],
    "recordClassName": "GeneRecordClasses.GeneRecordClass",
    "attributes": {
        "primary_key": "PF3D7_0417200",
        "product": "bifunctional dihydrofolate reductase-thymidylate synthase",
        "organism": "<i>P. falciparum 3D7</i>",
        "chromosome": "04",
    },
}


class TestSearchGenesByOrganism(unittest.TestCase):
    def test_missing_organism_rejected(self):
        result = _search_tool().run({"project": "plasmodb"})
        self.assertEqual(result["status"], "error")
        self.assertIn("organism", result["error"])

    def test_unknown_project_rejected(self):
        result = _search_tool().run(
            {"organism": "Plasmodium falciparum 3D7", "project": "nopedb"}
        )
        self.assertEqual(result["status"], "error")
        self.assertIn("Unknown project", result["error"])

    def test_post_body_and_url_for_plasmodb(self):
        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, SEARCH_PAYLOAD)
            result = tool.run(
                {
                    "organism": "Plasmodium falciparum 3D7",
                    "project": "plasmodb",
                    "limit": 5,
                }
            )

        self.assertEqual(result["status"], "success")
        # URL uses the plasmo subdir.
        url = (
            post.call_args.args[0]
            if post.call_args.args
            else post.call_args.kwargs["url"]
        )
        self.assertIn("plasmodb.org/plasmo/service", url)
        self.assertIn("GenesByTaxonGene/reports/standard", url)
        # organism param is a JSON-encoded array string.
        body = post.call_args.kwargs["json"]
        organism_param = body["searchConfig"]["parameters"]["organism"]
        self.assertEqual(json.loads(organism_param), ["Plasmodium falciparum 3D7"])
        # limit -> pagination numRecords.
        self.assertEqual(body["reportConfig"]["pagination"]["numRecords"], 5)
        # primary_key is always present in attributes.
        self.assertIn("primary_key", body["reportConfig"]["attributes"])

    def test_report_parsed_into_clean_rows(self):
        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, SEARCH_PAYLOAD)
            result = tool.run(
                {"organism": "Plasmodium falciparum 3D7", "project": "plasmodb"}
            )
        rows = result["data"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["primary_key"], "PF3D7_0100100")
        # HTML italics stripped from organism.
        self.assertEqual(rows[0]["organism"], "P. falciparum 3D7")
        self.assertEqual(result["metadata"]["total_count"], 5720)
        self.assertEqual(result["metadata"]["project"], "PlasmoDB")
        self.assertEqual(result["metadata"]["returned"], 1)

    def test_default_project_is_plasmodb(self):
        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, SEARCH_PAYLOAD)
            tool.run({"organism": "Plasmodium falciparum 3D7"})
        url = (
            post.call_args.args[0]
            if post.call_args.args
            else post.call_args.kwargs["url"]
        )
        self.assertIn("plasmodb.org/plasmo/service", url)

    def test_toxodb_subdir_mapping(self):
        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, {"records": [], "meta": {"totalCount": 0}})
            tool.run({"organism": "Toxoplasma gondii ME49", "project": "toxodb"})
        url = (
            post.call_args.args[0]
            if post.call_args.args
            else post.call_args.kwargs["url"]
        )
        self.assertIn("toxodb.org/toxo/service", url)

    def test_cryptodb_subdir_mapping(self):
        # cryptodb's subdir is 'cryptodb', not the abbreviated 'crypto'.
        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, {"records": [], "meta": {"totalCount": 0}})
            tool.run(
                {"organism": "Cryptosporidium parvum Iowa II", "project": "cryptodb"}
            )
        url = (
            post.call_args.args[0]
            if post.call_args.args
            else post.call_args.kwargs["url"]
        )
        self.assertIn("cryptodb.org/cryptodb/service", url)

    def test_http_error_returns_envelope_not_raise(self):
        import requests as _requests

        tool = _search_tool()
        err = _requests.exceptions.HTTPError("400")
        err.response = _resp(400, text="bad organism")
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value.raise_for_status.side_effect = err
            result = tool.run(
                {"organism": "Plasmodium falciparum 3D7", "project": "plasmodb"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("400", result["error"])

    def test_timeout_returns_envelope(self):
        import requests as _requests

        tool = _search_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.side_effect = _requests.exceptions.Timeout()
            result = tool.run(
                {"organism": "Plasmodium falciparum 3D7", "project": "plasmodb"}
            )
        self.assertEqual(result["status"], "error")
        self.assertIn("timed out", result["error"])


class TestGetGeneRecord(unittest.TestCase):
    def test_missing_gene_id_rejected(self):
        result = _record_tool().run({"project": "plasmodb"})
        self.assertEqual(result["status"], "error")
        self.assertIn("gene_id", result["error"])

    def test_record_post_body_includes_project_id(self):
        tool = _record_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, RECORD_PAYLOAD)
            result = tool.run({"gene_id": "PF3D7_0417200", "project": "plasmodb"})

        self.assertEqual(result["status"], "success")
        url = (
            post.call_args.args[0]
            if post.call_args.args
            else post.call_args.kwargs["url"]
        )
        self.assertIn("plasmodb.org/plasmo/service/record-types/gene/records", url)
        body = post.call_args.kwargs["json"]
        pk = {p["name"]: p["value"] for p in body["primaryKey"]}
        self.assertEqual(pk["source_id"], "PF3D7_0417200")
        # project_id matches the PlasmoDB site stamp.
        self.assertEqual(pk["project_id"], "PlasmoDB")

    def test_toxodb_record_uses_toxodb_project_id(self):
        tool = _record_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(
                200, {"attributes": {"primary_key": "TGME49_200010", "product": "x"}}
            )
            tool.run({"gene_id": "TGME49_200010", "project": "toxodb"})
        body = post.call_args.kwargs["json"]
        pk = {p["name"]: p["value"] for p in body["primaryKey"]}
        self.assertEqual(pk["project_id"], "ToxoDB")

    def test_record_attributes_parsed_and_cleaned(self):
        tool = _record_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, RECORD_PAYLOAD)
            result = tool.run({"gene_id": "PF3D7_0417200", "project": "plasmodb"})
        data = result["data"]
        self.assertEqual(
            data["product"],
            "bifunctional dihydrofolate reductase-thymidylate synthase",
        )
        self.assertEqual(data["organism"], "P. falciparum 3D7")
        self.assertEqual(result["metadata"]["gene_id"], "PF3D7_0417200")

    def test_empty_attributes_is_error(self):
        tool = _record_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, {"attributes": {}})
            result = tool.run({"gene_id": "NOPE_0000000", "project": "plasmodb"})
        self.assertEqual(result["status"], "error")
        self.assertIn("No gene record", result["error"])

    def test_primary_key_alias_accepted(self):
        tool = _record_tool()
        with patch("tooluniverse.veupathdb_tool.requests.post") as post:
            post.return_value = _resp(200, RECORD_PAYLOAD)
            result = tool.run({"primary_key": "PF3D7_0417200", "project": "plasmodb"})
        self.assertEqual(result["status"], "success")


if __name__ == "__main__":
    unittest.main()
