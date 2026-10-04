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
    # The 2026-10-03 sweep found four more. The allowlist above could not have
    # found them: it pins what was verified, it does not detect the class.
    # test_an_optional_key_cannot_mean_no_data below is the part that generalises.
    "iucn_tools.json": (["IUCN_API_KEY"], {"IUCN_get_conservation_status"}),
    "ldlink_tools.json": (["LDLINK_TOKEN"], {"LDlink_get_proxies"}),
    # Hugging Face serverless inference is token-gated even for a public model:
    # facebook/esm2_t33_650M_UR50D answers 200 anonymously for its config and
    # weights, and the inference endpoint still answers 401. The model being
    # downloadable is a different question from inference being free.
    "esm2_variant_effect_tools.json": (
        ["HF_TOKEN"],
        {"ESM2_score_missense_variant"},
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
    # VEuPathDB's record-type listing still answers 200 with no credential
    # while every other endpoint answers 401. Gating the whole file would
    # retire a working tool.
    "veupathdb_tools.json": {"VEuPathDB_list_record_types"},
}

# VEuPathDB gates four of its five endpoints. Verified by calling them: the
# key goes in a bare Authorization header, which their own 401 bodies reveal
# -- "Valid API Key required for this endpoint." with no header, "HTTP 401
# Unauthorized" with a bogus one.
VEUPATHDB_GATED = {
    "VEuPathDB_list_gene_searches",
    "VEuPathDB_list_organism_searches",
    "VEuPathDB_search_genes_by_organism",
    "VEuPathDB_get_gene_record",
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


def test_veupathdb_gates_only_the_endpoints_that_answer_401():
    tools = _tools("veupathdb_tools.json")

    for name in sorted(VEUPATHDB_GATED):
        assert tools[name].get("required_api_keys") == ["VEUPATHDB_API_KEY"], name


def test_veupathdb_actually_sends_the_key_it_demands():
    """Declaring a key a tool never transmits leaves the user no better off."""
    source = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "tooluniverse"
        / "veupathdb_tool.py"
    ).read_text("utf-8")

    assert 'self.credential("VEUPATHDB_API_KEY")' in source
    # A bare value, not Bearer: with "Bearer <key>" the service answers with
    # its "Valid API Key required" body, i.e. it does not see a key at all.
    # Checked against the assignment, not the prose, which explains the choice.
    assert 'headers["Authorization"] = api_key' in source
    assert 'f"Bearer' not in source

    config = _tools("veupathdb_tools.json")
    for name in ("VEuPathDB_list_gene_searches", "VEuPathDB_list_organism_searches"):
        auth = (config[name].get("fields") or {}).get("auth_header") or {}
        assert auth.get("env_var") == "VEUPATHDB_API_KEY", name
        assert auth.get("header") == "Authorization", name


def test_an_optional_key_cannot_mean_no_data():
    """The check that generalises, rather than pinning today's list.

    IUCN_API_KEY and LDLINK_TOKEN were declared optional while the catalogue
    entry for each said "no data without it" -- the contradiction was sitting
    in the generated file the whole time, and the sweep counted the failures.
    """
    catalogue = json.loads((DATA / "api_keys_catalog.json").read_text("utf-8"))
    rows = catalogue if isinstance(catalogue, list) else catalogue.get("keys") or []

    contradictions = [
        row["name"]
        for row in rows
        if isinstance(row, dict)
        and row.get("requirement") == "optional"
        and "no data without it" in (row.get("without") or "").lower()
    ]
    assert not contradictions, (
        "these keys are declared optional but their own note says no data "
        f"without them, so every call fails and the sweep counts it: {contradictions}"
    )
