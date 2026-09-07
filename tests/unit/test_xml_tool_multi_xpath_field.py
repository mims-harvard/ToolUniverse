"""Regression guard for Fix Round 25: a flat `field_mappings` value may be a
LIST of XPath expressions, tried in order with the first non-empty result winning.

drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id mapped
molecular_formula/molecular_weight only to
<experimental-properties>, but DrugBank files those two properties under
<calculated-properties> for small molecules -- so the two fields the tool's own
description promises came back "" for EVERY small molecule (confirmed live:
{"drug_name": "Ivermectin"} returned molecular_formula="" while melting_point
and water_solubility were populated). Biotech/peptide records genuinely do carry
them under <experimental-properties>, so the fix must consult both sections.
ElementTree/lxml findall() does not support `|` XPath unions, hence a list.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

NS = {"db": "http://www.drugbank.ca"}

# Two records mirroring the real dataset's two shapes: a small molecule with
# the properties under <calculated-properties>, and a biotech entry with them
# under <experimental-properties>.
SAMPLE_XML = """<?xml version="1.0" encoding="UTF-8"?>
<drugbank xmlns="http://www.drugbank.ca">
  <drug type="small molecule">
    <drugbank-id primary="true">DB00602</drugbank-id>
    <name>Ivermectin</name>
    <experimental-properties>
      <property><kind>Melting Point</kind><value>155 &#176;C</value></property>
    </experimental-properties>
    <calculated-properties>
      <property><kind>Molecular Formula</kind><value>C95H146O28</value></property>
      <property><kind>Molecular Weight</kind><value>1736.185</value></property>
    </calculated-properties>
  </drug>
  <drug type="biotech">
    <drugbank-id primary="true">DB00001</drugbank-id>
    <name>Lepirudin</name>
    <experimental-properties>
      <property><kind>Molecular Formula</kind><value>C287H440N80O111S6</value></property>
      <property><kind>Molecular Weight</kind><value>6979.0</value></property>
    </experimental-properties>
  </drug>
</drugbank>
"""

CALCULATED = "db:calculated-properties/db:property[db:kind='{}']/db:value"
EXPERIMENTAL = "db:experimental-properties/db:property[db:kind='{}']/db:value"


def _make_tool(tmp_path, formula_mapping, weight_mapping):
    from tooluniverse.xml_tool import XMLDatasetTool

    xml_path = tmp_path / "drugbank_sample.xml"
    xml_path.write_text(SAMPLE_XML, encoding="utf-8")

    return XMLDatasetTool(
        {
            "name": "drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id",
            "parameter": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
            "settings": {
                "local_dataset_path": str(xml_path),
                "namespaces": NS,
                "record_xpath": "db:drug",
                "search_fields": ["drug_name", "drugbank_id"],
                "field_mappings": {
                    "drug_name": "db:name",
                    "drugbank_id": "db:drugbank-id[@primary='true']",
                    "molecular_formula": formula_mapping,
                    "molecular_weight": weight_mapping,
                    "melting_point": EXPERIMENTAL.format("Melting Point"),
                },
            },
        }
    )


def _lookup(tool, query):
    result = tool.run({"query": query})
    assert result["status"] == "success", result
    records = result["data"]["results"]
    assert len(records) == 1, records
    return records[0]


@pytest.fixture
def tool(tmp_path):
    """A tool configured the way the shipped config now is: list-valued."""
    return _make_tool(
        tmp_path,
        [
            CALCULATED.format("Molecular Formula"),
            EXPERIMENTAL.format("Molecular Formula"),
        ],
        [
            CALCULATED.format("Molecular Weight"),
            EXPERIMENTAL.format("Molecular Weight"),
        ],
    )


def test_small_molecule_falls_to_calculated_properties(tool):
    """The bug: this record has NO experimental Molecular Formula at all."""
    record = _lookup(tool, "Ivermectin")
    assert record["molecular_formula"] == "C95H146O28"
    assert record["molecular_weight"] == "1736.185"
    # The fields that already worked must be untouched.
    assert record["melting_point"] == "155 °C"


def test_biotech_still_resolves_via_experimental_fallback(tool):
    """Second XPath in the list wins when the first yields nothing."""
    record = _lookup(tool, "Lepirudin")
    assert record["molecular_formula"] == "C287H440N80O111S6"
    assert record["molecular_weight"] == "6979.0"


def test_plain_string_mapping_behaviour_is_unchanged(tmp_path):
    """A str value must behave exactly as before -- including yielding ''."""
    tool = _make_tool(
        tmp_path,
        EXPERIMENTAL.format("Molecular Formula"),
        EXPERIMENTAL.format("Molecular Weight"),
    )
    assert _lookup(tool, "Ivermectin")["molecular_formula"] == ""
    assert _lookup(tool, "Lepirudin")["molecular_formula"] == "C287H440N80O111S6"


def test_list_mapping_yields_empty_string_when_no_xpath_matches(tmp_path):
    tool = _make_tool(
        tmp_path,
        [CALCULATED.format("Nonexistent"), EXPERIMENTAL.format("Nonexistent")],
        [CALCULATED.format("Nonexistent")],
    )
    record = _lookup(tool, "Ivermectin")
    assert record["molecular_formula"] == ""
    assert record["molecular_weight"] == ""


def test_list_valued_mapping_still_lands_in_default_search_fields(tmp_path):
    """search_fields defaults to list(field_mappings.keys()); a list value
    must not break that, nor the config echo in get_dataset_info()."""
    from tooluniverse.xml_tool import XMLDatasetTool

    xml_path = tmp_path / "drugbank_sample.xml"
    xml_path.write_text(SAMPLE_XML, encoding="utf-8")
    tool = XMLDatasetTool(
        {
            "name": "t",
            "settings": {
                "local_dataset_path": str(xml_path),
                "namespaces": NS,
                "record_xpath": "db:drug",
                "field_mappings": {
                    "molecular_formula": [
                        CALCULATED.format("Molecular Formula"),
                        EXPERIMENTAL.format("Molecular Formula"),
                    ]
                },
            },
        }
    )
    assert tool.search_fields == ["_text", "molecular_formula"]
    info = tool.get_dataset_info()
    assert isinstance(info["field_mappings"]["molecular_formula"], list)
    # get_dataset_info() feeds JSON responses; a list value must serialize.
    json.dumps(info["field_mappings"])


def test_shipped_config_lists_calculated_before_experimental():
    # Resolve via the installed package rather than the process cwd, so the
    # test does not depend on pytest being invoked from the repository root.
    import tooluniverse

    config_path = Path(tooluniverse.__file__).parent / "data" / "xml_tools.json"
    with open(config_path) as f:
        tools = json.load(f)
    settings = next(
        t
        for t in tools
        if t["name"] == "drugbank_get_drug_chemistry_by_drug_name_or_drugbank_id"
    )["settings"]
    for field, kind in (
        ("molecular_formula", "Molecular Formula"),
        ("molecular_weight", "Molecular Weight"),
    ):
        mapping = settings["field_mappings"][field]
        assert mapping == [CALCULATED.format(kind), EXPERIMENTAL.format(kind)], field
