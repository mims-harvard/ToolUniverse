"""Regression guard for OpenTargets_get_associated_drugs_by_disease_efoId.

The query asks the current Open Targets API for `drugAndClinicalCandidates`, whose
rows carry `drug` and `maxClinicalStage`. The return schema still described the
retired `knownDrugs` rows: drug.maximumClinicalTrialPhase, isApproved,
hasBeenWithdrawn and tradeNames, plus a row-level mechanismOfAction and target.
None of those was ever requested, so every one came back absent while the schema
promised it, and the one stage field that did come back (drug.maximumClinicalStage)
was undeclared. A caller that trusted the schema to pick this tool for "known
drugs with phase, approval and mechanism" got none of the three.

The query now requests the drug's type and its mechanisms of action with targets,
and the schema declares exactly the fields the query requests.
"""
import glob
import json
import re

import pytest
from jsonschema import validate

NAME = "OpenTargets_get_associated_drugs_by_disease_efoId"
# Fields the GraphQL tool adds beside Open Targets' own `count` + `rows`.
ADDED = {"returned", "truncated"}


def _load(name):
    for f in glob.glob("src/tooluniverse/data/*.json"):
        try:
            data = json.load(open(f))
        except ValueError:
            continue
        if isinstance(data, list):
            for tool in data:
                if isinstance(tool, dict) and tool.get("name") == name:
                    return tool
    raise AssertionError(f"tool config not found: {name}")


def _selection(query):
    """A GraphQL selection set as nested dicts ({field: subselection or None})."""
    body = query[query.index("{", query.index(")")) :]
    tokens = re.findall(r"\{|\}|[A-Za-z_][A-Za-z0-9_]*(?:\([^)]*\))?", body)
    stack, current, last = [], {}, None
    for token in tokens[1:-1]:
        if token == "{":
            stack.append(current)
            current[last] = {}
            current = current[last]
        elif token == "}":
            current = stack.pop()
        else:
            last = token.split("(")[0]
            current[last] = None
    return current


def _declared(schema):
    """A JSON schema's object properties as nested dicts, arrays looked through."""
    while schema.get("type") == "array" or "items" in schema:
        schema = schema["items"]
    properties = schema.get("properties")
    if not properties:
        return None
    return {k: _declared(v) for k, v in properties.items()}


def _rows(tree):
    return tree["disease"]["drugAndClinicalCandidates"]["rows"]


@pytest.mark.unit
def test_every_declared_row_field_is_requested_and_every_requested_one_declared():
    tool = _load(NAME)
    requested = _selection(tool["query_schema"])
    declared = _declared(tool["return_schema"]["properties"]["data"])
    assert _rows(declared) == _rows(requested)
    container = declared["disease"]["drugAndClinicalCandidates"]
    assert set(container) - ADDED == set(requested["disease"]["drugAndClinicalCandidates"])


@pytest.mark.unit
def test_the_retired_known_drugs_fields_are_gone():
    rows = _rows(_declared(_load(NAME)["return_schema"]["properties"]["data"]))
    for retired in ("maximumClinicalTrialPhase", "isApproved", "hasBeenWithdrawn", "tradeNames"):
        assert retired not in rows["drug"]
    assert "mechanismOfAction" not in rows and "target" not in rows


@pytest.mark.unit
def test_a_live_shaped_response_matches_the_schema():
    # Two rows as the API returned them for necrotizing enterocolitis (MONDO_0005313)
    # and pain (HP_0012531): one with a mechanism, one without.
    response = {
        "data": {
            "disease": {
                "id": "MONDO_0005313",
                "name": "necrotizing enterocolitis",
                "drugAndClinicalCandidates": {
                    "count": 2,
                    "returned": 2,
                    "truncated": False,
                    "rows": [
                        {
                            "drug": {
                                "id": "CHEMBL1082",
                                "name": "AMOXICILLIN",
                                "drugType": "Small molecule",
                                "maximumClinicalStage": "APPROVAL",
                                "mechanismsOfAction": {
                                    "rows": [
                                        {
                                            "mechanismOfAction": "Bacterial penicillin-binding protein inhibitor",
                                            "targets": [],
                                        }
                                    ]
                                },
                            },
                            "maxClinicalStage": "PHASE_3",
                        },
                        {
                            "drug": {
                                "id": "CHEMBL55214",
                                "name": "NERIDRONIC ACID",
                                "drugType": "Small molecule",
                                "maximumClinicalStage": "APPROVAL",
                                "mechanismsOfAction": None,
                            },
                            "maxClinicalStage": "PHASE_2_3",
                        },
                    ],
                },
            }
        }
    }
    validate(response, _load(NAME)["return_schema"])


@pytest.mark.unit
def test_the_description_separates_the_two_stages():
    description = _load(NAME)["description"]
    assert "maxClinicalStage" in description and "drug.maximumClinicalStage" in description
