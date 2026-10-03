"""A tool that cannot work without a credential has to say so.

24 of the failures in the weekly health check were not defects. ICD-11, UMLS
and HuggingFace Inference each refuse to run without a credential and say so
clearly in their error, but none of them declared `required_api_keys` -- so the
sweep ran them, they failed, and the report counted 6 + 5 + 13 failures that no
fix could ever clear. The harness already skips a tool whose declared keys are
absent; it just had nothing to read.

Only tools that genuinely cannot work are declared. `FDA_API_KEY`,
`NCBI_API_KEY` and `ONCOKB_API_TOKEN` are read by their modules too, and those
tools pass without them -- the key only raises a rate limit. Declaring those
would skip 186 working FDA tools and make the report blinder, not clearer.
"""

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.unit

DATA = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "data"

# Verified by calling each tool with no credential present: these refuse, with
# an error naming the credential.
MUST_DECLARE = {
    "icd_tools.json": (
        ["ICD_CLIENT_ID", "ICD_CLIENT_SECRET"],
        {"ICD11_search_diseases", "ICD11_get_entity", "ICD11_browse_hierarchy"},
    ),
    "umls_tools.json": (
        ["UMLS_API_KEY"],
        {
            "umls_search_concepts",
            "umls_get_concept_details",
            "icd_search_codes",
            "snomed_search_concepts",
            "loinc_search_codes",
        },
    ),
    "huggingface_inference_tools.json": (
        ["HF_TOKEN"],
        {
            "HFInference_classify_text",
            "HFInference_embed_text",
            "HFInference_fill_mask",
            "HFInference_summarize",
            "HFInference_zero_shot_classify",
            "HFInference_ner",
            "HFInference_question_answering",
            "HFInference_translate",
            "HFInference_classify_image",
            "HFInference_detect_objects",
        },
    ),
}

# Verified to work without a credential; declaring one would skip them.
MUST_NOT_DECLARE = {
    "icd_tools.json": {"ICD10_search_codes", "ICD10_get_code_info"},
}


def _tools(file_name):
    return {t["name"]: t for t in json.loads((DATA / file_name).read_text("utf-8"))}


@pytest.mark.parametrize("file_name", sorted(MUST_DECLARE))
def test_tools_that_refuse_without_a_credential_declare_it(file_name):
    keys, names = MUST_DECLARE[file_name]
    tools = _tools(file_name)

    for name in sorted(names):
        assert name in tools, f"{name} is gone from {file_name}"
        assert tools[name].get("required_api_keys") == keys, (
            f"{name} refuses to run without {keys} and must declare them, or "
            "the weekly sweep counts it as a failure no fix can clear"
        )


@pytest.mark.parametrize("file_name", sorted(MUST_NOT_DECLARE))
def test_tools_that_work_without_a_credential_do_not_declare_one(file_name):
    tools = _tools(file_name)

    for name in sorted(MUST_NOT_DECLARE[file_name]):
        assert not tools[name].get("required_api_keys"), (
            f"{name} works without a credential; declaring one would have the "
            "sweep skip a tool it can actually check"
        )


def test_the_declared_keys_are_in_the_api_key_catalogue():
    """An undocumented key name leaves a user with nothing to act on."""
    catalogue = json.loads((DATA / "api_keys_catalog.json").read_text("utf-8"))
    rows = catalogue if isinstance(catalogue, list) else catalogue.get("keys") or []
    known = {row["name"] for row in rows if isinstance(row, dict) and row.get("name")}

    for keys, _ in MUST_DECLARE.values():
        for key in keys:
            assert key in known, f"{key} is declared but not in api_keys_catalog.json"
