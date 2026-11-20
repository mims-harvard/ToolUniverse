"""ClinVar's clinical features arrive without their labels, and the schema must say so.

Measured 2026-11-13 against VCV000013961 (BRAF V600E, 45 submissions): the
tool returns 11 `clinical_features` across 2 submissions and EVERY ONE of them
is `{"name": null, "hpo_id": "HP:...", "status": "present"}`. The raw efetch
XML explains why -- each Trait carries only

    <Trait ClinicalFeaturesAffectedStatus="present" Type="Finding">
      <XRef DB="HP" ID="HP:0000543" />
    </Trait>

with no <Name> child at all. So the label is absent upstream, not dropped by
the wrapper: this is the paper's L3, where the fix we owe is the disclosure.

Before this commit `name` was declared `["string", "null"]` with NO description
whatsoever, which reads as "sometimes a submitter leaves it blank" rather than
"this is null essentially always and the label lives in another tool".
"""

import json
from pathlib import Path

import pytest

_DATA = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "tooluniverse"
    / "data"
    / "clinvar_submitted_tools.json"
)


@pytest.fixture(scope="module")
def clinical_features():
    for tool in json.loads(_DATA.read_text()):
        if tool["name"] == "ClinVar_get_submitted_records":
            return tool["return_schema"]["oneOf"][0]["properties"]["submissions"][
                "items"
            ]["properties"]["clinical_features"]
    pytest.fail("ClinVar_get_submitted_records is gone from its data file")


def test_the_name_field_says_when_it_is_null(clinical_features):
    described = clinical_features["items"]["properties"]["name"].get("description", "")
    assert described, "`name` is null in every measured record and says nothing about it"
    assert "null" in described.lower()


def test_the_caller_is_told_where_the_label_actually_lives(clinical_features):
    text = json.dumps(clinical_features)
    assert (
        "HPO_get_term" in text
    ), "disclosing a missing label without naming the tool that has it is half a disclosure"


def test_a_null_label_is_not_read_as_an_unnamed_phenotype(clinical_features):
    described = clinical_features["items"]["properties"]["name"]["description"]
    assert "not that the phenotype is unnamed" in described.lower().replace(",", "")
