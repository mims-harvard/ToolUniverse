"""DDBJ BioProject records leave the top-level organism null.

The organism is only in the submitted project XML, under
properties.Project.Project.ProjectType. DDBJ_get_entry and DDBJ_search_entries
read only the top-level field, so every BioProject came back with
organism None (e.g. PRJDB3490 is mouse gut metagenome, taxid 410661).
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ddbj_tool import DDBJTool

pytestmark = pytest.mark.unit


def _tool(name):
    with open("src/tooluniverse/data/ddbj_tools.json") as fh:
        config = next(t for t in json.load(fh) if t["name"] == name)
    return DDBJTool(config)


def _response(payload):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _bioproject(identifier, project_type):
    return {
        "identifier": identifier,
        "type": "bioproject",
        "title": "t",
        "organism": None,
        "properties": {"Project": {"Project": {"ProjectType": project_type}}},
    }


SUBMISSION = {
    "ProjectTypeSubmission": {
        "Target": {
            "sample_scope": "eEnvironment",
            "Organism": {"taxID": "410661", "OrganismName": "mouse gut metagenome"},
        }
    }
}
UMBRELLA = {
    "ProjectTypeTopAdmin": {
        "subtype": "eOther",
        "Organism": {"taxID": "41880", "OrganismName": "Pycnococcus provasolii"},
    }
}
MULTISPECIES = {"ProjectTypeSubmission": {"Target": {"sample_scope": "eMultispecies"}}}


def test_get_entry_reads_the_bioproject_organism():
    with patch(
        "tooluniverse.ddbj_tool.requests.get",
        return_value=_response(_bioproject("PRJDB3490", SUBMISSION)),
    ):
        result = _tool("DDBJ_get_entry").run({"accession": "PRJDB3490"})

    assert result["status"] == "success"
    assert result["data"]["organism"] == "mouse gut metagenome"
    assert result["data"]["taxonomy_id"] == "410661"


def test_search_rows_read_the_bioproject_organism_including_umbrella_projects():
    payload = {
        "items": [
            _bioproject("PRJDB3490", SUBMISSION),
            _bioproject("PRJDB11533", UMBRELLA),
            _bioproject("PRJNA1423897", MULTISPECIES),
        ],
        "pagination": {"total": 3},
    }
    with patch("tooluniverse.ddbj_tool.requests.get", return_value=_response(payload)):
        result = _tool("DDBJ_search_entries").run(
            {"entry_type": "bioproject", "keywords": "gut"}
        )

    assert [r["organism"] for r in result["data"]] == [
        "mouse gut metagenome",
        "Pycnococcus provasolii",
        None,
    ]


def test_top_level_organism_still_wins_for_other_types():
    record = {
        "identifier": "SAMD00000345",
        "type": "biosample",
        "organism": {"identifier": "1202668", "name": "Secundilactobacillus oryzae"},
    }
    with patch("tooluniverse.ddbj_tool.requests.get", return_value=_response(record)):
        result = _tool("DDBJ_get_entry").run({"accession": "SAMD00000345"})

    assert result["data"]["organism"] == "Secundilactobacillus oryzae"
    assert result["data"]["taxonomy_id"] == "1202668"
