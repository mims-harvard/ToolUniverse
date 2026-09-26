"""The "child safety" and "pediatric use" label tools say which section they return.

``FDA_get_child_safety_info_by_drug_name`` was described as "Retrieve child
safety information for a specific drug based on its name", but it returns the
``keep_out_of_reach_of_children`` section: for ibuprofen, "Keep out of reach of
children. In case of overdose, get medical help ...", and for a prescription
drug such as montelukast, NOT_FOUND, because prescription labels have no such
section. Whether a drug is safe or effective in children is in ``pediatric_use``,
the section ``FDA_get_pediatric_use_info_by_drug_name`` returns. The two
descriptions now name their sections and point at each other. Tool behaviour,
parameters and fields are unchanged.
"""

import json
import pathlib

import pytest

from tooluniverse import openfda_tool

pytestmark = pytest.mark.unit

PACKAGE = pathlib.Path(openfda_tool.__file__).parent
CONFIGS = {
    tool["name"]: tool
    for tool in json.loads(
        (PACKAGE / "data" / "fda_drug_labeling_tools.json").read_text(encoding="utf-8")
    )
}
CHILD = "FDA_get_child_safety_info_by_drug_name"
PEDIATRIC = "FDA_get_pediatric_use_info_by_drug_name"
SECTION = {CHILD: "keep_out_of_reach_of_children", PEDIATRIC: "pediatric_use"}


@pytest.mark.parametrize("name", [CHILD, PEDIATRIC])
def test_the_description_names_the_section_the_tool_returns(name):
    config = CONFIGS[name]
    assert config["fields"]["return_fields"] == [SECTION[name]]
    assert f"FDA label's {SECTION[name]} section" in config["description"]


def test_child_safety_says_it_is_not_pediatric_use_and_points_there():
    description = CONFIGS[CHILD]["description"]
    assert "accidental-ingestion" in description
    assert "does not provide a general assessment of pediatric use" in description
    assert PEDIATRIC in description
    assert PEDIATRIC in CONFIGS  # the tool it points at exists


def test_pediatric_use_says_it_is_not_the_access_warning():
    description = CONFIGS[PEDIATRIC]["description"]
    assert "pediatric populations" in description
    assert "distinct from keep_out_of_reach_of_children" in description


@pytest.mark.parametrize("name", [CHILD, PEDIATRIC])
def test_a_missing_section_is_not_read_as_safety(name):
    assert (
        "A missing section does not establish safety or lack of risk"
        in CONFIGS[name]["description"]
    )


@pytest.mark.parametrize("name", [CHILD, PEDIATRIC])
def test_only_the_description_changed(name):
    config = CONFIGS[name]
    assert config["type"] == "FDADrugLabel"
    assert config["fields"]["search_fields"] == {
        "drug_name": [
            "openfda.brand_name",
            "openfda.generic_name",
            "spl_product_data_elements",
        ]
    }
    assert set(config["parameter"]["properties"]) == {"drug_name", "limit", "skip"}


@pytest.mark.parametrize("name", [CHILD, PEDIATRIC])
def test_the_generated_wrapper_carries_the_new_description(name):
    description = CONFIGS[name]["description"]
    # generate_tools.generate_tool_file shortens descriptions over 100 chars
    expected = description[:97] + "..." if len(description) > 100 else description
    wrapper = (PACKAGE / "tools" / f"{name}.py").read_text(encoding="utf-8")
    assert wrapper.count(expected) == 2  # module and function docstrings
