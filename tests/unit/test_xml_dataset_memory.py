"""The xml category was killed by the OOM killer on every weekly sweep.

Measured 2026-10-03, running the 19 xml tools in one process:

    peak 120.7 GB RSS, exit 137 (SIGKILL) after 138 s

and the report could only say "incomplete or invalid test output", because the
process died before printing a summary. Three separate causes, each measured:

    share one parsed tree per file      120.7 GB -> 27.5 GB
    stop caching the full extraction     27.5 GB -> 26.1 GB
    one copy of DrugBank, not two        26.1 GB -> 14.6 GB   20/20 passing

MeSH_desc2025.xml is 299 MB and drugbank_full_database.xml is 1.5 GB, and lxml
holds a tree at several times the file size: DrugBank alone measures 11 GB
parsed. _load_dataset() runs from __init__, so every instance used to build its
own. Four of the fifteen DrugBank tools also set save_to_local_dir, which gave
them a second copy of the file at a different path -- and dropped 1.5 GB inside
the installed package.

14.6 GB is still more than a 16 GB CI runner can hold alongside everything
else, so these tests pin the three fixes rather than claiming the category now
fits in CI. A tree that size needs a streaming reader, which is a redesign.
"""

import json
from pathlib import Path

import pytest

import tooluniverse.xml_tool as xml_tool

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "src" / "tooluniverse" / "data"

RECORDS_XML = """<?xml version="1.0"?>
<DescriptorRecordSet>
  <DescriptorRecord><DescriptorUI>D001</DescriptorUI>
    <DescriptorName><String>Analgesics</String></DescriptorName></DescriptorRecord>
  <DescriptorRecord><DescriptorUI>D002</DescriptorUI>
    <DescriptorName><String>Anaesthetics</String></DescriptorName></DescriptorRecord>
</DescriptorRecordSet>
"""


@pytest.fixture
def dataset(tmp_path):
    xml_tool.clear_dataset_cache()
    path = tmp_path / "records.xml"
    path.write_text(RECORDS_XML, encoding="utf-8")
    yield path
    xml_tool.clear_dataset_cache()


def _config(path):
    return {
        "name": "test_tool",
        "description": "test",
        "parameter": {"type": "object", "properties": {}},
        "settings": {
            "local_dataset_path": str(path),
            "record_xpath": "DescriptorRecord",
            "field_mappings": {
                "id": "DescriptorUI",
                "name": "DescriptorName/String",
            },
        },
    }


def test_two_tools_on_one_file_parse_it_once(dataset, monkeypatch):
    parses = []
    real_parse = xml_tool.ET.parse

    def counting_parse(source, *args, **kwargs):
        parses.append(str(source))
        return real_parse(source, *args, **kwargs)

    monkeypatch.setattr(xml_tool.ET, "parse", counting_parse)

    first = xml_tool.XMLDatasetTool(_config(dataset))
    second = xml_tool.XMLDatasetTool(_config(dataset))

    assert len(parses) == 1, (
        "each instance parsed its own tree; 15 DrugBank tools did that to a "
        "1.5 GB file"
    )
    assert first.xml_root is second.xml_root
    assert len(first.records) == len(second.records) == 2


def test_the_shared_tree_still_answers_correctly(dataset):
    tool = xml_tool.XMLDatasetTool(_config(dataset))

    result = tool.run({"query": "Analgesics", "limit": 5})

    assert result["status"] == "success"
    assert [r["id"] for r in result["data"]["results"]] == ["D001"]


def test_a_second_tool_reading_the_shared_tree_answers_the_same(dataset):
    first = xml_tool.XMLDatasetTool(_config(dataset))
    second = xml_tool.XMLDatasetTool(_config(dataset))

    assert first.run({"query": "Anaesthetics", "limit": 5}) == second.run(
        {"query": "Anaesthetics", "limit": 5}
    )


def test_searching_does_not_retain_every_extracted_record(dataset):
    """_search ranks every record and keeps only the matches."""
    tool = xml_tool.XMLDatasetTool(_config(dataset))

    tool.run({"query": "Analgesics", "limit": 5})

    assert tool._record_cache == [], (
        "the full extraction was cached for the object's lifetime, which cost "
        "about as much as the shared tree again"
    )


def test_iterating_records_yields_one_at_a_time(dataset):
    tool = xml_tool.XMLDatasetTool(_config(dataset))

    records = tool._iter_records_data()

    assert next(records)["id"] == "D001"
    assert tool._record_cache == []
    assert next(records)["id"] == "D002"


def test_no_xml_tool_writes_its_dataset_into_the_package():
    """save_to_local_dir put 1.5 GB in src/tooluniverse/test and gave those
    four tools a second copy of the tree."""
    offenders = []
    for tool in json.loads((DATA / "xml_tools.json").read_text("utf-8")):
        hf = (tool.get("settings") or {}).get("hf_dataset_path") or {}
        if isinstance(hf, dict) and hf.get("save_to_local_dir"):
            offenders.append((tool["name"], hf["save_to_local_dir"]))

    assert not offenders, offenders


def test_the_xml_tools_read_at_most_two_distinct_sources():
    """19 tools, two files. A third source means a third tree."""
    sources = set()
    for tool in json.loads((DATA / "xml_tools.json").read_text("utf-8")):
        settings = tool.get("settings") or {}
        hf = settings.get("hf_dataset_path")
        if isinstance(hf, dict):
            sources.add((hf.get("repo_id"), hf.get("path_in_repo"),
                         hf.get("save_to_local_dir")))
        elif settings.get("local_dataset_path"):
            sources.add(settings["local_dataset_path"])

    assert len(sources) <= 2, sorted(str(s) for s in sources)
