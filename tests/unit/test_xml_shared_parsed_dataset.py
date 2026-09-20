"""XMLDatasetTool instances that use the same file share one parsed tree.

DrugBank is ~1.5 GB of XML (several times that as an lxml tree) and 15 tool
definitions point at it. Each instance used to parse its own copy in __init__, so
memory scaled with the number of DrugBank tools used in a session (an eager load of
all of them exceeded 100 GB). The parsed tree is read-only, so it is now shared per
(file, record_xpath, namespaces); per-tool state must stay independent.

Uses a tiny synthetic XML file via `local_dataset_path` -- no network, no big data.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

pytestmark = pytest.mark.unit

NS = "http://www.drugbank.ca"


@pytest.fixture(autouse=True)
def _fresh_cache():
    from tooluniverse import xml_tool

    xml_tool._PARSED_DATASETS.clear()
    yield
    xml_tool._PARSED_DATASETS.clear()


def _write(tmp_path, names=("Aspirin", "Ibuprofen"), filename="db.xml"):
    drugs = "".join(
        f"<drug><drugbank-id primary='true'>DB{i:05d}</drugbank-id>"
        f"<name>{n}</name><description>{n} description</description></drug>"
        for i, n in enumerate(names)
    )
    path = tmp_path / filename
    path.write_text(f'<drugbank xmlns="{NS}">{drugs}</drugbank>', encoding="utf-8")
    return str(path)


def _tool(path, record_xpath="db:drug", mappings=None, name="t"):
    from tooluniverse.xml_tool import XMLDatasetTool

    return XMLDatasetTool(
        {
            "name": name,
            "parameter": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "settings": {
                "local_dataset_path": path,
                "record_xpath": record_xpath,
                "namespaces": {"db": NS},
                "search_fields": ["drug_name"],
                "field_mappings": mappings or {"drug_name": "db:name"},
            },
        }
    )


def test_same_file_and_settings_share_the_parsed_tree(tmp_path):
    path = _write(tmp_path)
    a, b = _tool(path, name="a"), _tool(path, name="b")
    assert a.records and len(a.records) == 2
    assert a.xml_root is b.xml_root
    assert a.records is b.records


def test_different_record_xpath_is_not_shared(tmp_path):
    path = _write(tmp_path)
    a = _tool(path, record_xpath="db:drug")
    b = _tool(path, record_xpath="db:drug/db:name")
    assert len(a.records) == 2 and len(b.records) == 2
    assert a.records is not b.records
    assert a.records[0].tag != b.records[0].tag


def test_per_tool_field_mappings_and_caches_stay_independent(tmp_path):
    path = _write(tmp_path)
    a = _tool(path, mappings={"drug_name": "db:name"}, name="a")
    b = _tool(
        path,
        mappings={"drug_name": "db:name", "blurb": "db:description"},
        name="b",
    )
    assert a.records is b.records  # tree shared ...
    ra = a.run({"query": "aspirin"})["data"]["results"][0]
    rb = b.run({"query": "aspirin"})["data"]["results"][0]
    assert ra["drug_name"] == "Aspirin"
    assert "blurb" not in ra  # ... but each tool extracts its own fields
    assert rb["blurb"] == "Aspirin description"
    assert a._record_cache is not b._record_cache


def test_replaced_file_is_reparsed_not_served_stale(tmp_path):
    path = _write(tmp_path, names=("Aspirin", "Ibuprofen"))
    a = _tool(path)
    assert len(a.records) == 2
    _write(tmp_path, names=("Aspirin", "Ibuprofen", "Naproxen"))
    st = os.stat(path)
    os.utime(path, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    b = _tool(path)
    assert len(b.records) == 3
    assert b.records is not a.records
    assert len(a.records) == 2  # the earlier instance keeps its own parse


def test_missing_file_still_yields_an_empty_tool_without_raising(tmp_path):
    tool = _tool(str(tmp_path / "does_not_exist.xml"))
    assert tool.records == []
