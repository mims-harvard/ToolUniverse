"""
Regression tests for return_schema mismatches reported in issue #246.

`tu test` (see tooluniverse/cli.py) validates a tool's response via
``jsonschema.validate(result.get("data"), return_schema)`` -- i.e. it
validates only the inner ``data`` payload, not the full ``{"status", "data"}``
envelope. The nine tools covered here previously declared ``return_schema``
as a full envelope (``oneOf`` branches requiring ``status``/``data``/
``metadata`` or ``status``/``error``), which can never match a bare
``data`` payload and always failed validation regardless of how correct
the live API response was. This file pins down the fix: each declared
``return_schema`` must validate a representative live-shaped payload
under the exact call cli.py makes, and must reject the old enveloped
shape as a payload (proving the schema now genuinely describes ``data``,
not the envelope).
"""

import json

import jsonschema
import pytest

from tooluniverse import ToolUniverse


@pytest.fixture(scope="module")
def tool_configs():
    tu = ToolUniverse()
    tu.load_tools()
    return {tool["name"]: tool for tool in tu.all_tools if isinstance(tool, dict)}


CASES = [
    (
        "UniProt_get_entry_by_accession",
        {
            "entryType": "UniProtKB reviewed (Swiss-Prot)",
            "primaryAccession": "P04637",
            "uniProtkbId": "P53_HUMAN",
            "protein_name": "Cellular tumor antigen p53",
            "gene_names": ["TP53"],
            "organism": {"scientificName": "Homo sapiens", "taxonId": 9606},
            "sequence": {"value": "MEEP", "length": 393},
            "xref_count": 1079,
        },
    ),
    (
        "RCSBData_get_entry",
        {
            "pdb_id": "4HHB",
            "title": "THE CRYSTAL STRUCTURE OF HUMAN DEOXYHAEMOGLOBIN",
            "method": "X-RAY DIFFRACTION",
            "resolution": 1.74,
            "unit_cell": {"a": 63.15, "b": 83.59, "c": 53.8},
        },
    ),
    (
        "ClinicalTrials_search_studies",
        {
            "studies": [
                {
                    "nct_id": "NCT05732831",
                    "brief_title": "Safety and Tolerability of TNG462",
                    "phases": ["PHASE1", "PHASE2"],
                    "enrollment": 225,
                }
            ],
            "total_count": 104,
            "next_page_token": "ZVNj7o2Elu8o3lp3Utj4srbumpOQJJxuZ_Gt1fYW",
        },
    ),
    (
        "ClinicalTrials_get_database_stats",
        {
            # gaierror-free: total_studies/average_byte_size legitimately null upstream
            "total_studies": None,
            "average_byte_size": None,
            "largest_studies": [{"id": "NCT02723955", "sizeBytes": 3596689}],
        },
    ),
    (
        "gnomad_get_gene_constraints",
        {
            "gene": {
                "symbol": "BRCA1",
                "gene_id": "ENSG00000012048",
                "exac_constraint": None,
                "gnomad_constraint": {
                    "exp_lof": 173.65,
                    "obs_lof": 140,
                    "oe_lof": 0.806,
                    "pLI": 5.5e-38,
                    "exp_mis": 2172.4,
                    "obs_mis": 1983,
                    "oe_mis": 0.912,
                    "exp_syn": 756.0,
                    "obs_syn": 662,
                    "oe_syn": 0.875,
                },
            }
        },
    ),
    (
        "GTEx_get_tissue_sites",
        [
            {
                "tissueSiteDetailId": "Adipose_Subcutaneous",
                "colorHex": "FF6600",
                "colorRgb": "255,102,0",
                "datasetId": "gtex_v8",
                "expressedGeneCount": 28830,
                "hasEGenes": True,
                "hasSGenes": True,
                "mappedInHubmap": False,
            }
        ],
    ),
    (
        "gwas_search_associations",
        [
            {
                "association_id": 214063945,
                "p_value": 2e-10,
                "beta": "6.365012 z-score increase",
                "efo_traits": [
                    {"efo_id": "MONDO_0005010", "efo_trait": "coronary artery disorder"}
                ],
                "accession_id": "GCST90668075",
            }
        ],
    ),
    (
        "PharmGKB_search_drugs",
        [
            {
                "objCls": "Chemical",
                "id": "PA451906",
                "name": "warfarin",
                "types": ["Drug"],
            }
        ],
    ),
    (
        "ENCODE_search_histone_experiments",
        {
            "total": 458,
            "experiments": [
                {
                    "accession": "ENCSR864OOO",
                    "histone_mark": "H3K27ac",
                    "biosample_summary": "Homo sapiens liver tissue",
                    "status": "released",
                    "lab": "Bradley Bernstein, Broad",
                    "date_released": None,
                }
            ],
        },
    ),
]


@pytest.mark.parametrize("tool_name,sample_data", CASES)
def test_return_schema_validates_live_shaped_data(tool_configs, tool_name, sample_data):
    """The exact call cli.py's `tu test` makes must accept a real-shaped payload."""
    return_schema = tool_configs[tool_name]["return_schema"]
    result = {"status": "success", "data": sample_data}

    jsonschema.validate(result.get("data"), return_schema)


@pytest.mark.parametrize("tool_name,sample_data", CASES)
def test_return_schema_accepts_error_shape(tool_configs, tool_name, sample_data):
    """The oneOf error branch must still validate a plain {"error": ...} payload."""
    return_schema = tool_configs[tool_name]["return_schema"]

    jsonschema.validate({"error": "upstream request failed"}, return_schema)


@pytest.mark.parametrize("tool_name,sample_data", CASES)
def test_return_schema_rejects_old_envelope_shape(tool_configs, tool_name, sample_data):
    """Guards against regressing to the issue #246 bug: a schema describing the
    full {"status", "data", "metadata"} envelope can never match a bare `data`
    payload, so re-wrapping `sample_data` in an envelope must fail validation."""
    return_schema = tool_configs[tool_name]["return_schema"]
    enveloped = {"status": "success", "data": sample_data, "metadata": {}}

    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(enveloped, return_schema)


def test_all_cases_reference_real_tools(tool_configs):
    missing = [name for name, _ in CASES if name not in tool_configs]
    assert not missing, f"Tool(s) not found in registry: {missing}"
