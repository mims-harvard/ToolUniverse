"""Regression tests for PDC_search_studies field-scoped matching.

PDC_search_studies used to call ``studySearch(name:)``, which only compares the
query against the study title. Searching PDC's own curated disease name
("Lung Adenocarcinoma") returned zero studies even though PDC annotates
PDC000153 with exactly that ``disease_type`` - the documented "search by
disease name" capability only appeared to work when a study title happened to
contain the word.

The search now pulls PDC's study catalog (``getPaginatedUIStudy``) and matches
the query against the curated structured fields as well as the title, and
reports which field produced each hit.

Fully mocked - no network.
"""

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.unit

import tooluniverse.pdc_tool as pdc_mod
from tooluniverse.pdc_tool import PDCTool


# Three studies modelled on real PDC records:
#  - PDC000153 is annotated Lung Adenocarcinoma AND titled "... LUAD ..."
#  - PDC000231 is annotated Lung Adenocarcinoma but has no "LUAD" in its title
#  - PDC000154 is titled "... LUAD ..." but curated as disease_type "Other"
#  - PDC000315 belongs to the CPTAC program but no field spells out "CPTAC"
CATALOG = [
    {
        "study_id": "uuid-153",
        "pdc_study_id": "PDC000153",
        "submitter_id_name": "CPTAC LUAD Discovery Study - Proteome",
        "disease_type": "Lung Adenocarcinoma;Other",
        "primary_site": "Bronchus and lung;Not Reported",
        "analytical_fraction": "Proteome",
        "experiment_type": "TMT10",
        "program_name": "Clinical Proteomic Tumor Analysis Consortium",
        "project_name": "CPTAC3 Discovery and Confirmatory",
    },
    {
        "study_id": "uuid-231",
        "pdc_study_id": "PDC000231",
        "submitter_id_name": "Georgetown Lung Cancer Proteomics Study",
        "disease_type": "Lung Adenocarcinoma;Other",
        "primary_site": "Bronchus and lung;Lung",
        "analytical_fraction": "Proteome",
        "experiment_type": "iTRAQ8",
        "program_name": "Georgetown Proteomics Research Program",
        "project_name": "Georgetown Lung Cancer Proteomics Study",
    },
    {
        "study_id": "uuid-154",
        "pdc_study_id": "PDC000154",
        "submitter_id_name": "CPTAC LUAD Discovery Study - CompRef Proteome",
        "disease_type": "Other",
        "primary_site": "Not Reported",
        "analytical_fraction": "Proteome",
        "experiment_type": "TMT10",
        "program_name": "Clinical Proteomic Tumor Analysis Consortium",
        "project_name": "CPTAC3 Discovery and Confirmatory",
    },
    {
        "study_id": "uuid-315",
        "pdc_study_id": "PDC000315",
        "submitter_id_name": "AML Gilteritinib Resistance - Proteome",
        "disease_type": "Other",
        "primary_site": "Not Reported",
        "analytical_fraction": "Proteome",
        "experiment_type": "TMT11",
        "program_name": "Clinical Proteomic Tumor Analysis Consortium",
        "project_name": "Proteogenomic Translational Research Centers (PTRC)",
    },
]

# Which studies PDC's controlled program vocabulary returns for "CPTAC".
PROGRAM_VOCABULARY = {"CPTAC": ["PDC000153", "PDC000154", "PDC000315"]}


def _tool():
    return PDCTool(
        {
            "name": "PDC_search_studies",
            "type": "PDCTool",
            "parameter": {"required": ["query"]},
        }
    )


def _fake_post_factory(calls=None):
    """Fake requests.post that serves the study catalog and program filter.

    Distinguishes the two GraphQL documents the search issues: an unfiltered
    catalog page and a ``program_name``-filtered lookup.
    """

    def _fake_post(url, json=None, headers=None, timeout=None):
        document = (json or {}).get("query", "")
        if calls is not None:
            calls.append(document)

        if "program_name:" in document:
            matched = []
            for term, ids in PROGRAM_VOCABULARY.items():
                if '"%s"' % term in document:
                    matched = ids
                    break
            studies = [{"pdc_study_id": i} for i in matched]
        else:
            studies = CATALOG

        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "data": {
                "getPaginatedUIStudy": {
                    "total": len(CATALOG),
                    "uiStudies": studies,
                }
            }
        }
        return resp

    return _fake_post


def _search(monkeypatch, query, calls=None):
    monkeypatch.setattr(pdc_mod.requests, "post", _fake_post_factory(calls))
    return _tool().run({"operation": "search_studies", "query": query})


def test_search_matches_curated_disease_type(monkeypatch):
    """A curated PDC disease name finds studies whose title never mentions it.

    This is the regression: 'Lung Adenocarcinoma' previously returned zero
    results because only the study title was searched.
    """
    out = _search(monkeypatch, "Lung Adenocarcinoma")

    assert out["status"] == "success"
    data = out["data"]
    found = {s["pdc_study_id"] for s in data["studies"]}
    assert found == {"PDC000153", "PDC000231"}
    assert data["num_results"] == 2
    # PDC000231's title says "Lung Cancer", not "Lung Adenocarcinoma" - it can
    # only be found via the structured field.
    assert data["num_results_by_field"]["disease_type"] == 2
    assert data["num_results_by_field"]["submitter_id_name"] == 0
    for study in data["studies"]:
        assert study["matched_fields"] == ["disease_type"]
        assert study["matched_curated_metadata"] is True
        assert study["disease_type"] == "Lung Adenocarcinoma;Other"


def test_search_still_matches_study_title(monkeypatch):
    """Title matching is preserved, and reported as a title-only match."""
    out = _search(monkeypatch, "LUAD")

    data = out["data"]
    assert {s["pdc_study_id"] for s in data["studies"]} == {
        "PDC000153",
        "PDC000154",
    }
    assert data["num_results_by_field"]["submitter_id_name"] == 2

    by_id = {s["pdc_study_id"]: s for s in data["studies"]}
    # PDC000154 is curated as disease_type "Other"; a caller must be able to
    # tell this apart from a curated disease-type hit.
    assert by_id["PDC000154"]["matched_fields"] == ["submitter_id_name"]
    assert by_id["PDC000154"]["matched_curated_metadata"] is False


def test_search_matches_case_insensitively(monkeypatch):
    """Matching does not depend on the caller's capitalisation."""
    lower = _search(monkeypatch, "lung adenocarcinoma")["data"]
    upper = _search(monkeypatch, "LUNG ADENOCARCINOMA")["data"]
    assert lower["num_results"] == upper["num_results"] == 2


def test_search_matches_analytical_fraction(monkeypatch):
    """The documented analytical-fraction search hits the structured field."""
    data = _search(monkeypatch, "Proteome")["data"]
    assert data["num_results"] == len(CATALOG)
    assert data["num_results_by_field"]["analytical_fraction"] == len(CATALOG)


def test_search_resolves_program_acronym(monkeypatch):
    """Program acronyms resolve via PDC's controlled program vocabulary.

    PDC000315's program is spelled "Clinical Proteomic Tumor Analysis
    Consortium" and none of its fields contain the string "CPTAC", so text
    matching alone would drop it from a CPTAC search.
    """
    calls = []
    data = _search(monkeypatch, "CPTAC", calls=calls)["data"]

    assert "PDC000315" in {s["pdc_study_id"] for s in data["studies"]}
    by_id = {s["pdc_study_id"]: s for s in data["studies"]}
    assert by_id["PDC000315"]["matched_fields"] == ["program_name"]
    assert by_id["PDC000315"]["matched_curated_metadata"] is True

    # The program filter must be its own request: PDC returns results for the
    # wrong filter when several filtered selections share one document.
    filtered = [c for c in calls if "program_name:" in c]
    assert len(filtered) == 1


def test_empty_result_explains_which_fields_were_searched(monkeypatch):
    """A genuine miss is an honest empty success, not a crash or a bare zero."""
    out = _search(monkeypatch, "Amyotrophic Lateral Sclerosis")

    assert out["status"] == "success"
    data = out["data"]
    assert data["studies"] == []
    assert data["num_results"] == 0
    assert data["num_studies_searched"] == len(CATALOG)
    # The caller can see exactly what was compared.
    for field in (
        "disease_type",
        "primary_site",
        "analytical_fraction",
        "experiment_type",
        "program_name",
        "project_name",
        "submitter_id_name",
    ):
        assert field in data["fields_searched"]
    assert "disease_type" in data["note"]
    assert "Amyotrophic Lateral Sclerosis" in data["note"]


def test_fields_searched_present_on_non_empty_results(monkeypatch):
    """fields_searched is always reported, not only on empty results."""
    data = _search(monkeypatch, "LUAD")["data"]
    assert data["fields_searched"][0] == "disease_type"
    assert "note" not in data


def test_missing_query_is_an_error():
    """A blank query is a caller error, distinct from an empty result."""
    out = _tool().run({"operation": "search_studies", "query": "   "})
    assert out["status"] == "error"
    assert "query" in out["error"]


def test_graphql_error_surfaces_as_error(monkeypatch):
    """Upstream failures are errors, never a silently empty study list."""
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"errors": [{"message": "boom"}]}
    monkeypatch.setattr(pdc_mod.requests, "post", lambda *a, **k: resp)

    out = _tool().run({"operation": "search_studies", "query": "Lung"})
    assert out["status"] == "error"
    assert "boom" in out["error"]


def test_program_lookup_failure_degrades_with_warning(monkeypatch):
    """If only the program vocabulary lookup fails, say so instead of lying."""

    def _post(url, json=None, headers=None, timeout=None):
        document = (json or {}).get("query", "")
        resp = MagicMock()
        resp.status_code = 200
        if "program_name:" in document:
            resp.json.return_value = {"errors": [{"message": "vocab down"}]}
        else:
            resp.json.return_value = {
                "data": {
                    "getPaginatedUIStudy": {
                        "total": len(CATALOG),
                        "uiStudies": CATALOG,
                    }
                }
            }
        return resp

    monkeypatch.setattr(pdc_mod.requests, "post", _post)
    out = _tool().run({"operation": "search_studies", "query": "CPTAC"})

    assert out["status"] == "success"
    data = out["data"]
    # Text matching still finds the studies that spell out CPTAC ...
    assert {s["pdc_study_id"] for s in data["studies"]} == {
        "PDC000153",
        "PDC000154",
    }
    # ... and the response admits the program lookup was skipped.
    assert data["warnings"]
    assert "vocab down" in data["warnings"][0]


def test_catalog_is_paginated(monkeypatch):
    """More studies than one page still get searched."""
    page_size = pdc_mod.STUDY_CATALOG_PAGE_SIZE
    big = []
    for i in range(page_size + 3):
        entry = dict(CATALOG[0])
        entry["pdc_study_id"] = "PDCX%05d" % i
        entry["disease_type"] = "Lung Adenocarcinoma"
        big.append(entry)

    def _post(url, json=None, headers=None, timeout=None):
        document = (json or {}).get("query", "")
        resp = MagicMock()
        resp.status_code = 200
        if "program_name:" in document:
            resp.json.return_value = {
                "data": {"getPaginatedUIStudy": {"uiStudies": []}}
            }
        else:
            offset = 0 if "offset: 0" in document else page_size
            resp.json.return_value = {
                "data": {
                    "getPaginatedUIStudy": {
                        "total": len(big),
                        "uiStudies": big[offset : offset + page_size],
                    }
                }
            }
        return resp

    monkeypatch.setattr(pdc_mod.requests, "post", _post)
    out = _tool().run(
        {"operation": "search_studies", "query": "Lung Adenocarcinoma"}
    )
    assert out["data"]["num_studies_searched"] == page_size + 3
    assert out["data"]["num_results"] == page_size + 3


def test_query_with_quotes_does_not_break_the_graphql_document(monkeypatch):
    """A quote in the query is escaped, not injected into the GraphQL text."""
    calls = []
    out = _search(monkeypatch, 'Lung" Adenocarcinoma', calls=calls)

    assert out["status"] == "success"
    assert out["data"]["num_results"] == 0
    filtered = [c for c in calls if "program_name:" in c]
    assert filtered and '\\"' in filtered[0]
