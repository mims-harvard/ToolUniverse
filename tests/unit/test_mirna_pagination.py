import ast
import json
from pathlib import Path

import pytest
from jsonschema import validate

from tooluniverse.mirna_tool import miRNAGetTool, miRNASearchTool


ROOT = Path(__file__).parents[2]
CONFIGS = {}
for config_file in ("mirna_tools.json", "lncrna_tools.json"):
    CONFIGS.update(
        {
            item["name"]: item
            for item in json.loads(
                (ROOT / "src/tooluniverse/data" / config_file).read_text()
            )
        }
    )


class _Response:
    ok = True
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


def _entry(identifier):
    return {
        "id": identifier,
        "fields": {
            "description": [identifier],
            "rna_type": ["miRNA"],
            "length": ["22"],
            "expert_db": ["MIRBASE"],
        },
    }


def test_mirna_search_forwards_start_and_exposes_continuation(monkeypatch):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response({"hitCount": 8, "entries": [_entry("URS3"), _entry("URS4")]})

    monkeypatch.setattr("tooluniverse.mirna_tool.requests.get", fake_get)
    result = miRNASearchTool(CONFIGS["miRBase_search_mirna"]).run(
        {"query": "miR-21", "size": 2, "start": 3}
    )

    assert captured["start"] == 3
    assert captured["size"] == 2
    assert result["data"]["start"] == 3
    assert result["data"]["next_start"] == 5
    assert result["data"]["has_more"] is True
    assert result["data"]["truncated"] is True
    validate(result["data"], CONFIGS["miRBase_search_mirna"]["return_schema"])


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("LNCipedia_search_lncrna", {"query": "MALAT1"}),
        (
            "LNCipedia_search_ncrna_by_type",
            {"query": "SNORD", "rna_type": "snoRNA"},
        ),
    ],
)
def test_lncrna_search_configs_expose_shared_pagination(monkeypatch, name, arguments):
    captured = {}

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response({"hitCount": 7, "entries": [_entry("URS2")]})

    monkeypatch.setattr("tooluniverse.mirna_tool.requests.get", fake_get)
    result = miRNASearchTool(CONFIGS[name]).run({**arguments, "size": 1, "start": 2})
    assert captured["start"] == 2
    assert result["data"]["next_start"] == 3
    validate(result["data"], CONFIGS[name]["return_schema"])


@pytest.mark.parametrize(
    "name,endpoint,list_key,total_key",
    [
        (
            "miRBase_get_mirna_publications",
            "get_publications",
            "publications",
            "total_publications",
        ),
        (
            "miRBase_get_mirna_xrefs",
            "get_xrefs",
            "cross_references",
            "total_xrefs",
        ),
        (
            "LNCipedia_get_lncrna_publications",
            "get_publications",
            "publications",
            "total_publications",
        ),
        (
            "LNCipedia_get_lncrna_xrefs",
            "get_xrefs",
            "cross_references",
            "total_xrefs",
        ),
    ],
)
def test_rnacentral_pages_are_forwarded_and_bidirectional(
    monkeypatch, name, endpoint, list_key, total_key
):
    captured = {}
    if endpoint == "get_publications":
        row = {
            "title": "A paper",
            "authors": ["A"],
            "publication": "Journal",
            "pubmed_id": "123",
            "doi": None,
            "expert_db": False,
        }
    else:
        row = {
            "database": "MIRBASE",
            "taxid": 9606,
            "is_active": True,
            "accession": {
                "id": "MIMAT0000076",
                "external_id": "hsa-miR-21-5p",
                "description": "microRNA 21",
                "species": "Homo sapiens",
                "rna_type": "miRNA",
                "gene": "MIR21",
                "expert_db_url": None,
            },
            "mirbase_mature_products": None,
            "mirbase_precursor": None,
        }

    def fake_get(_url, **kwargs):
        captured.update(kwargs["params"])
        return _Response(
            {
                "count": 12,
                "next": "https://example/page=3",
                "previous": "https://example/page=1",
                "results": [row, row],
            }
        )

    monkeypatch.setattr("tooluniverse.mirna_tool.requests.get", fake_get)
    tool = miRNAGetTool(CONFIGS[name])
    result = tool.run({"rnacentral_id": "URS000039ED8D", "page_size": 2, "page": 2})

    assert captured == {"format": "json", "page_size": 2, "page": 2}
    assert result["data"][total_key] == 12
    assert len(result["data"][list_key]) == 2
    assert result["data"]["previous_page"] == 1
    assert result["data"]["next_page"] == 3
    assert result["data"]["result_set_complete"] is False
    if endpoint == "get_publications":
        assert result["metadata"]["upstream_total_is_record_count"] is True
        assert result["metadata"]["unique_pmids_not_guaranteed"] is True
        assert "unique PMID" in result["metadata"]["warning"]
    validate(result["data"], CONFIGS[name]["return_schema"])


@pytest.mark.parametrize("value", [0, 51, True, "10", 1.5])
def test_rnacentral_rejects_invalid_page_size_before_network(monkeypatch, value):
    def fail(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr("tooluniverse.mirna_tool.requests.get", fail)
    result = miRNAGetTool(CONFIGS["miRBase_get_mirna_publications"]).run(
        {"rnacentral_id": "URS000039ED8D", "page_size": value}
    )
    assert result["status"] == "error"
    assert result["parameter"] == "page_size"


@pytest.mark.parametrize("value", [0, -1, True, "2", 1.5])
def test_rnacentral_rejects_invalid_page_before_network(monkeypatch, value):
    def fail(*_args, **_kwargs):
        raise AssertionError("network must not be called")

    monkeypatch.setattr("tooluniverse.mirna_tool.requests.get", fail)
    result = miRNAGetTool(CONFIGS["miRBase_get_mirna_xrefs"]).run(
        {"rnacentral_id": "URS000039ED8D", "page": value}
    )
    assert result["status"] == "error"
    assert result["parameter"] == "page"


@pytest.mark.parametrize(
    "filename,expected_defaults",
    [
        ("miRBase_search_mirna.py", [None, 10, 0]),
        ("miRBase_get_mirna_publications.py", [10, 1]),
        ("miRBase_get_mirna_xrefs.py", [10, 1]),
        ("LNCipedia_search_lncrna.py", [None, 10, 0]),
        ("LNCipedia_search_ncrna_by_type.py", [None, None, 10, 0]),
        ("LNCipedia_get_lncrna_publications.py", [10, 1]),
        ("LNCipedia_get_lncrna_xrefs.py", [10, 1]),
    ],
)
def test_generated_wrappers_publish_pagination_defaults(filename, expected_defaults):
    tree = ast.parse((ROOT / "src/tooluniverse/tools" / filename).read_text())
    function = next(node for node in tree.body if isinstance(node, ast.FunctionDef))
    defaults = [ast.literal_eval(node) for node in function.args.defaults]
    assert defaults == expected_defaults
