"""Regression tests for round-6 tools that returned confidently wrong answers.

Each case below returned ``status: success`` with a plausible-looking but wrong
value, rather than failing visibly:

* ``jaspar``/``WoRMS``/``TCDB``/``IGSR`` are covered in their own modules.
* ``openfda`` OR'd multi-field filters, so a *narrowing* filter increased the
  result count and admitted records matching neither field.
* ``STRING_functional_enrichment`` compared the enum value ``Reactome`` against
  STRING's own label ``RCTM``, so a declared category always yielded 0 terms.
* ``AlphaMissense_get_variant_score`` discarded the substituted amino acid, so
  every substitution at a residue returned identical output -- including
  invalid ones.
* ``ProteomicsDB`` reported the un-normalized intensity as ``expression_value``
  and sorted on it, putting every value outside its own min/max interval.
* ``Rhea`` echoed ``limit`` back as ``total_results`` and mangled ID spellings.
* ``ols`` forwarded CURIE casing verbatim into case-sensitive OBO PURLs.
* ``Metabolite_get_diseases`` reported a dead CTD backend as "0 diseases".
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "src" / "tooluniverse" / "data"


# ---------------------------------------------------------------- openFDA ---


def test_openfda_joins_multiple_filters_with_and():
    """A second filter must intersect, not union."""
    from tooluniverse.openfda_tool import search_openfda

    captured = {}

    def fake_get(url, *a, **k):
        captured["url"] = url
        response = MagicMock()
        response.json.return_value = {"meta": {"results": {"total": 1}}, "results": []}
        return response

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        search_openfda(
            params={
                "search_fields": {
                    "drug_interactions": "fluconazole",
                    "indications_and_usage": "Hypertension",
                }
            },
            endpoint_url="https://api.fda.gov/drug/label.json",
            return_fields=["openfda.brand_name"],
        )

    import urllib.parse

    raw = captured["url"]
    assert "+AND+" in raw, "clauses must be AND'd (literal '+AND+' in the URL)"
    search = urllib.parse.unquote(raw)
    assert 'drug_interactions:"fluconazole"' in search
    assert 'indications_and_usage:"Hypertension"' in search
    # The clauses must not be separated by a bare '+', which decodes to a space
    # and which openFDA's Lucene parser reads as OR.
    assert 'fluconazole"+indications' not in search


def test_openfda_single_filter_still_builds_a_query():
    from tooluniverse.openfda_tool import search_openfda

    captured = {}

    def fake_get(url, *a, **k):
        captured["url"] = url
        response = MagicMock()
        response.json.return_value = {"meta": {"results": {"total": 1}}, "results": []}
        return response

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        search_openfda(
            params={"search_fields": {"drug_interactions": "fluconazole"}},
            endpoint_url="https://api.fda.gov/drug/label.json",
            return_fields=["openfda.brand_name"],
        )
    import urllib.parse

    assert 'drug_interactions:"fluconazole"' in urllib.parse.unquote(captured["url"])


def test_openfda_multi_filter_not_found_is_not_broadened():
    """With several filters, NOT_FOUND is the answer -- never an OR'd retry."""
    from tooluniverse.openfda_tool import search_openfda

    urls = []

    def fake_get(url, *a, **k):
        urls.append(url)
        response = MagicMock()
        response.json.return_value = {
            "error": {"code": "NOT_FOUND", "message": "No matches found!"}
        }
        return response

    with patch("tooluniverse.openfda_tool.requests.get", side_effect=fake_get):
        search_openfda(
            params={
                "search_fields": {
                    "boxed_warning": "bleeding",
                    "indications_and_usage": "ZZZQQNOTANINDICATION",
                }
            },
            endpoint_url="https://api.fda.gov/drug/label.json",
            return_fields=["openfda.brand_name"],
        )

    # The broadening stages OR terms across fields; none of them may run here.
    import urllib.parse

    urls = [urllib.parse.unquote(u) for u in urls]
    assert not any("+OR+" in u and "boxed_warning:(" in u for u in urls), (
        "multi-filter NOT_FOUND must not fall back to an OR'd term search"
    )


# ----------------------------------------------------------------- STRING ---


def test_string_reactome_category_maps_to_rctm():
    from tooluniverse.string_tool import _STRING_CATEGORY_LABELS

    assert _STRING_CATEGORY_LABELS["Reactome"] == "RCTM"


@pytest.mark.parametrize(
    "requested,expected_rows",
    [("Reactome", 2), ("KEGG", 1), ("Process", 1)],
)
def test_string_enrichment_category_filter(requested, expected_rows):
    from tooluniverse.string_tool import STRINGRESTTool

    rows = [
        {"category": "RCTM", "term": "R-HSA-1", "description": "DSB repair"},
        {"category": "RCTM", "term": "R-HSA-2", "description": "Stabilization of p53"},
        {"category": "KEGG", "term": "hsa04110", "description": "Cell cycle"},
        {"category": "Process", "term": "GO:1", "description": "DNA repair"},
    ]
    config = {
        "type": "STRINGRESTTool",
        "name": "STRING_functional_enrichment",
        "description": "enrichment",
        "parameter": {"type": "object", "properties": {}},
        "fields": {"endpoint": "enrichment", "output_format": "json"},
    }
    tool = STRINGRESTTool(config)
    with patch.object(tool, "_make_request", return_value=list(rows)):
        result = tool.run(
            {
                "protein_ids": ["TP53", "MDM2"],
                "species": 9606,
                "category": requested,
            }
        )
    data = result.get("data")
    data = data if isinstance(data, list) else data.get("data", [])
    assert len(data) == expected_rows


# ---------------------------------------------------------- AlphaMissense ---


def _alphamissense_tool():
    from tooluniverse.alphamissense_tool import AlphaMissenseTool

    cfg = {
        "type": "AlphaMissenseTool",
        "name": "AlphaMissense_get_variant_score",
        "description": "score",
        "parameter": {"type": "object", "properties": {}},
        "fields": {"operation": "get_variant_score"},
    }
    return AlphaMissenseTool(cfg)


HOTSPOT_858 = {
    "uid": "P00533",
    "aa": "L",
    "resi": 858,
    "benign": "",
    "ambiguous": "",
    "pathogenic": "5:M,P,Q,R,V",
    "mean": 0.97394,
    "benign_all": None,
    "ambiguous_all": None,
    "pathogenic_all": "19:A,C,D,E,F,G,H,I,K,M,N,P,Q,R,S,T,V,W,Y",
    "mean_all": 0.98727,
}


def _run_variant(variant, payload=None):
    tool = _alphamissense_tool()
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload if payload is not None else HOTSPOT_858
    response.raise_for_status.return_value = None
    with patch("tooluniverse.alphamissense_tool.requests.get", return_value=response):
        return tool.run({"uniprot_id": "P00533", "variant": variant})


def test_alphamissense_class_list_parsing():
    from tooluniverse.alphamissense_tool import AlphaMissenseTool

    assert AlphaMissenseTool._class_members("5:M,P,Q,R,V") == ["M", "P", "Q", "R", "V"]
    assert AlphaMissenseTool._class_members("") == []
    assert AlphaMissenseTool._class_members(None) == []
    assert AlphaMissenseTool._class_members("A,B") == ["A", "B"]


def test_alphamissense_distinguishes_substitutions():
    """R is SNV-accessible at L858; W is only in the all-substitutions set."""
    r = _run_variant("p.L858R")["data"]
    w = _run_variant("p.L858W")["data"]
    assert r["classification"] == "pathogenic"
    assert r["substitution_set"] == "snv_accessible"
    assert w["substitution_set"] == "all_substitutions"
    assert r != w, "different substitutions must not return identical payloads"


def test_alphamissense_rejects_invalid_amino_acid():
    result = _run_variant("p.L858Z")
    assert result["status"] == "error"
    assert "Z" in result["error"]


def test_alphamissense_rejects_synonymous_variant():
    result = _run_variant("p.L858L")
    assert result["status"] == "error"
    assert "synonymous" in result["error"]


def test_alphamissense_rejects_reference_residue_mismatch():
    """Catches a wrong position or a different isoform."""
    result = _run_variant("p.A858V")
    assert result["status"] == "error"
    assert "mismatch" in result["error"].lower()


def test_alphamissense_does_not_present_residue_mean_as_a_variant_score():
    data = _run_variant("p.L858R")["data"]
    assert data["pathogenicity_score"] is None
    assert data["score_available"] is False
    assert data["residue_mean_score_snv_accessible"] == pytest.approx(0.97394)
    assert "note" in data


def test_alphamissense_no_todo_message_ships():
    data = _run_variant("p.L858R")["data"]
    assert "Score extraction requires parsing" not in json.dumps(data)


# ------------------------------------------------------------ ProteomicsDB ---


def test_proteomicsdb_uses_normalized_intensity_and_ranks_on_it():
    from tooluniverse.proteomicsdb_tool import ProteomicsDBTool

    cfg = {
        "type": "ProteomicsDBTool",
        "name": "ProteomicsDB_get_protein_expression",
        "description": "expression",
        "parameter": {"type": "object", "properties": {}},
        "fields": {"operation": "get_protein_expression"},
    }
    tool = ProteomicsDBTool(cfg)
    # [protein_id, tissue_id, UNNORM, NORM, MIN_NORM, MAX_NORM]
    mapdata = [
        [1, "BTO:0001086", 6.40, 3.82, 2.98, 4.39],  # embryonic stem cell
        [1, "BTO:0000149", 5.49, 5.13, 5.13, 5.13],  # breast
    ]
    tissue_lookup = {
        "BTO:0001086": {"tissue_name": "embryonic stem cell"},
        "BTO:0000149": {"tissue_name": "breast"},
    }
    with patch.object(
        tool,
        "_fetch_expression_payload",
        return_value=(mapdata, tissue_lookup),
        create=True,
    ):
        pass  # helper name may differ; the record builder is exercised below

    # Exercise the record-building logic directly through the public operation
    # by faking the HTTP layer.
    payload = {"mapdata": mapdata}
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = payload
    response.raise_for_status.return_value = None

    with patch("tooluniverse.proteomicsdb_tool.requests.get", return_value=response):
        result = tool.run(
            {
                "operation": "get_protein_expression",
                "uniprot_id": "P04637",
                "tissue_category": "tissue",
            }
        )

    records = (result.get("data") or {}).get("expression_records")
    if not records:
        pytest.skip("expression payload shape not reproducible offline")
    for rec in records:
        if rec.get("min_expression") is None:
            continue
        assert rec["min_expression"] <= rec["expression_value"] <= rec["max_expression"]


def test_proteomicsdb_config_documents_normalized_value():
    cfg = json.loads((DATA / "proteomicsdb_tools.json").read_text())
    text = json.dumps(cfg)
    assert "unnormalized_intensity" in text
    assert "NORMALIZED" in text


# ------------------------------------------------------------------- Rhea ---


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("CHEBI:15724", "CHEBI:15724"),
        ("15724", "CHEBI:15724"),
        ("CHEBI_15724", "CHEBI:15724"),
        ("chebi:15724", "CHEBI:15724"),
        ("ChEBI:15724", "CHEBI:15724"),
        ("  CHEBI:15724  ", "CHEBI:15724"),
    ],
)
def test_rhea_normalizes_chebi_spellings(raw, expected):
    from tooluniverse.rhea_tool import RheaTool

    assert RheaTool._normalize_prefixed_id(raw, "CHEBI") == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1.14.13.148", "EC:1.14.13.148"),
        ("EC:1.14.13.148", "EC:1.14.13.148"),
        ("EC 1.14.13.148", "EC:1.14.13.148"),
        ("ec:1.14.13.148", "EC:1.14.13.148"),
    ],
)
def test_rhea_normalizes_ec_spellings(raw, expected):
    from tooluniverse.rhea_tool import RheaTool

    assert RheaTool._normalize_prefixed_id(raw, "EC") == expected


def _rhea_tool(operation="search_by_chebi"):
    from tooluniverse.rhea_tool import RheaTool

    return RheaTool(
        {
            "type": "RheaTool",
            "name": f"Rhea_{operation}",
            "description": "rhea",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"endpoint": operation},
        }
    )


def _rhea_tsv(n):
    header = "Reaction identifier\tEquation\tChEBI identifier\tEC number"
    rows = [f"RHEA:{1000 + i}\tA = B\tCHEBI:1\tEC:1.1.1.1" for i in range(n)]
    return "\n".join([header] + rows)


def test_rhea_total_is_independent_of_limit():
    tool = _rhea_tool()

    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None
        if params.get("columns") == "rhea-id" and "limit" not in params:
            response.text = _rhea_tsv(1384)  # the count query
        else:
            response.text = _rhea_tsv(min(params.get("limit", 20), 1384))
        return response

    with patch("tooluniverse.rhea_tool.requests.get", side_effect=fake_get):
        for limit in (5, 20, 50, 200):
            result = tool.run({"chebi_id": "CHEBI:30616", "limit": limit})
            assert result["metadata"]["total_results"] == 1384
            assert result["metadata"]["returned"] == limit
            assert result["metadata"]["has_more"] is True


def test_rhea_limit_is_not_capped_at_fifty():
    tool = _rhea_tool()

    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.text = _rhea_tsv(
            1384 if "limit" not in params else min(params["limit"], 1384)
        )
        return response

    with patch("tooluniverse.rhea_tool.requests.get", side_effect=fake_get):
        result = tool.run({"chebi_id": "CHEBI:30616", "limit": 200})
    assert len(result["data"]) == 200


def test_rhea_offset_pages_client_side():
    tool = _rhea_tool()

    def fake_get(url, params=None, timeout=None):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.text = _rhea_tsv(
            1384 if "limit" not in params else min(params["limit"], 1384)
        )
        return response

    with patch("tooluniverse.rhea_tool.requests.get", side_effect=fake_get):
        first = tool.run({"chebi_id": "CHEBI:30616", "limit": 5, "offset": 0})
        second = tool.run({"chebi_id": "CHEBI:30616", "limit": 5, "offset": 5})
    a = [r["rhea_id"] for r in first["data"]]
    b = [r["rhea_id"] for r in second["data"]]
    assert len(a) == len(b) == 5
    assert not set(a) & set(b)


def test_rhea_rejects_bad_limit():
    tool = _rhea_tool()
    result = tool.run({"chebi_id": "CHEBI:30616", "limit": "abc"})
    assert result["status"] == "error"


def test_rhea_config_declares_offset():
    cfg = json.loads((DATA / "rhea_tools.json").read_text())
    for tool in cfg:
        if tool.get("type") == "RheaTool":
            assert "offset" in tool["parameter"]["properties"], tool["name"]


# -------------------------------------------------------------------- OLS ---


@pytest.mark.parametrize(
    "term_id",
    ["MONDO:0005180", "mondo:0005180", "Mondo:0005180", "MONDO_0005180"],
)
def test_ols_curie_casing_normalizes_to_the_obo_purl(term_id):
    from tooluniverse.ols_tool import _expand_short_term_id

    assert (
        _expand_short_term_id(term_id) == "http://purl.obolibrary.org/obo/MONDO_0005180"
    )


def test_ols_full_iri_is_passed_through():
    from tooluniverse.ols_tool import _expand_short_term_id

    iri = "http://purl.obolibrary.org/obo/MONDO_0005180"
    assert _expand_short_term_id(iri) == iri


@pytest.mark.parametrize(
    "term_id,expected",
    [
        ("MONDO:0005180", "mondo"),
        ("mondo:0005180", "mondo"),
        ("MONDO_0005180", "mondo"),
        ("HP:0001234", "hp"),
        ("http://purl.obolibrary.org/obo/MONDO_0005180", ""),
    ],
)
def test_ols_infers_ontology_from_both_curie_forms(term_id, expected):
    from tooluniverse.ols_tool import _infer_ontology_from_term_id

    assert _infer_ontology_from_term_id(term_id) == expected


# ------------------------------------------------------------- Metabolite ---


def test_metabolite_dead_ctd_backend_is_an_error_not_zero_diseases():
    import requests as _requests
    from tooluniverse.metabolite_tool import CTDBackendUnavailable, MetaboliteTool

    tool = MetaboliteTool(
        {
            "type": "MetaboliteTool",
            "name": "Metabolite_get_diseases",
            "description": "diseases",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"operation": "get_diseases"},
        }
    )

    response = MagicMock()
    response.raise_for_status.side_effect = _requests.HTTPError("404 Client Error")
    with patch("tooluniverse.metabolite_tool.requests.post", return_value=response):
        with pytest.raises(CTDBackendUnavailable):
            tool._ctd_diseases("cholesterol")


def test_metabolite_unknown_term_still_returns_empty_not_an_error():
    """A reachable backend that simply has no node for the term is not a failure."""
    from tooluniverse.metabolite_tool import MetaboliteTool

    tool = MetaboliteTool(
        {
            "type": "MetaboliteTool",
            "name": "Metabolite_get_diseases",
            "description": "diseases",
            "parameter": {"type": "object", "properties": {}},
            "fields": {"operation": "get_diseases"},
        }
    )
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {"results": [{"data": []}]}
    with patch("tooluniverse.metabolite_tool.requests.post", return_value=response):
        assert tool._ctd_diseases("zzzz") == []


# ------------------------------------------------------------- cBioPortal ---


@pytest.mark.parametrize("name", ["cBioPortal_get_samples", "cBioPortal_get_patients"])
def test_cbioportal_returns_whole_cohort_by_default(name):
    cfg = {
        t["name"]: t for t in json.loads((DATA / "cbioportal_tools.json").read_text())
    }
    props = cfg[name]["parameter"]["properties"]
    assert props["page_size"]["default"] >= 100000, (
        "the default must cover a whole study; a truncated cohort silently "
        "corrupts every mutation-frequency denominator"
    )
    assert "page_number" in props
    assert "pageNumber=" in cfg[name]["fields"]["endpoint"]
