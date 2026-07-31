"""Regression guard for Fix-R8C-2: ClinicalTrials_search_studies had no
additionalProperties restriction, so an unrecognized parameter (e.g.
"drug" -- the real key is "query_intr", or its later-added alias
"intervention" -- see Fix-R9D-1) was silently ignored rather than
rejected, and the query ran anyway using only the recognized params.
Matches the same additionalProperties: false fix already applied to the
sibling search_clinical_trials tool.
"""

import json

import jsonschema
import pytest

pytestmark = pytest.mark.unit


def _load_schema():
    with open("src/tooluniverse/data/clinicaltrials_gov_tools.json") as f:
        tools = json.load(f)
    tool = next(t for t in tools if t["name"] == "ClinicalTrials_search_studies")
    return tool["parameter"]


def test_schema_rejects_unrecognized_key():
    schema = _load_schema()
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(
            {"condition": "hearing loss", "drug": "gene therapy"}, schema
        )


def test_schema_accepts_documented_alias_and_real_params():
    schema = _load_schema()
    jsonschema.validate({"condition": "hearing loss", "max_results": 5}, schema)
    jsonschema.validate({"query_cond": "hearing loss", "query_intr": "gene therapy"}, schema)
    # Fix-R9D-1: "intervention" was later added as a real, working alias
    # for query_intr -- it must be accepted, not rejected.
    jsonschema.validate(
        {"condition": "hearing loss", "intervention": "gene therapy"}, schema
    )
