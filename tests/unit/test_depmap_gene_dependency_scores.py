"""DepMap_get_gene_dependencies returned the gene record and no score.

It said "Full dependency profiles at depmap.org" with status success, and
it ignored model_id. The Sanger API it already used serves the scores at
/genes/{id}/datasets/crispr_ko. HTTP is faked with responses recorded on
2026-11-25 (tests/fixtures/depmap/README.md).
"""

import json
from pathlib import Path

import pytest
import requests

from tooluniverse import depmap_tool as D

pytestmark = pytest.mark.unit

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "depmap"
CONFIG = next(
    c
    for c in json.loads(
        (ROOT / "src" / "tooluniverse" / "data" / "depmap_tools.json").read_text()
    )
    if c["name"] == "DepMap_get_gene_dependencies"
)
KRAS = {
    "gene_id": "SIDG13960",
    "symbol": "KRAS",
    "hgnc_id": "HGNC:6407",
    "ensembl_id": "ENSG00000133703",
    "exact_match": True,
}
KRAS_SCORES = "genes/SIDG13960/datasets/crispr_ko"


def _load(name):
    return json.loads((FIXTURES / name).read_text())


class _Response:
    def __init__(self, body, status=200):
        self.body, self.status_code = body, status

    def json(self):
        return self.body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(
                f"{self.status_code} Client Error", response=self
            )


@pytest.fixture
def api(monkeypatch):
    """Serve recorded bodies by URL path, resolve KRAS, record every call."""
    routes = {}
    calls = []

    def get(url, params=None, timeout=None):
        path = url.replace(D.DEPMAP_BASE_URL + "/", "")
        calls.append((path, dict(params or {})))
        if path not in routes:
            raise AssertionError(f"unexpected GET {path}")
        body, status = routes[path]
        if isinstance(body, Exception):
            raise body
        return _Response(body, status)

    monkeypatch.setattr(D.requests, "get", get)
    monkeypatch.setattr(
        D.DepMapTool,
        "_search_genes",
        lambda self, arguments: {
            "status": "success",
            "data": {"genes": [dict(KRAS, symbol=arguments["query"].upper())]},
        },
    )

    def route(path, body, status=200):
        routes[path] = (body, status)

    route.calls = calls
    return route


def _run(arguments):
    return D.DepMapTool(CONFIG).run(arguments)


def test_scores_come_back_one_row_per_screen_most_dependent_first(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    result = _run({"gene_symbol": "KRAS"})
    assert result["status"] == "success"
    data = result["data"]
    assert data["matched_gene"]["gene_id"] == "SIDG13960"

    scores = data["scores"]
    assert len(scores) == 7 == data["total_scores"] == data["returned"]
    values = [row["bf_scaled"] for row in scores]
    assert values == sorted(values)
    top = scores[0]
    assert top == {
        "model_id": "SIDM01595",
        "model_name": "HCC461",
        "model_type": "Cell Line",
        "tissue": "Lung",
        "cancer_type": top["cancer_type"],
        "source": "Broad",
        "bf_scaled": -31.26252,
        "bf": top["bf"],
        "fc_clean_qn": -3.94293,
        "qc_pass": True,
        "loss_of_fitness": True,
    }
    assert top["cancer_type"]
    # HT-29 is KRAS wild type: the Sanger screen shows no loss of fitness.
    ht29 = [r for r in scores if r["model_name"] == "HT-29" and r["source"] == "Sanger"]
    assert ht29[0]["bf_scaled"] == 1.84273 and ht29[0]["loss_of_fitness"] is False
    assert "below 0" in data["note"] and "Chronos" in data["note"]
    assert "depmap.org." not in data["note"].split("Chronos")[0]


def test_summary_counts_every_screen_and_each_source(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    summary = _run({"gene_symbol": "KRAS", "limit": 2})["data"]["summary"]
    assert summary == {
        "screens": 7,
        "loss_of_fitness_screens": 6,
        "loss_of_fitness_fraction": 0.857,
        "models": 5,
        "by_source": {
            "Broad": {
                "screens": 3,
                "loss_of_fitness_screens": 3,
                "loss_of_fitness_fraction": 1.0,
            },
            "Sanger": {
                "screens": 4,
                "loss_of_fitness_screens": 3,
                "loss_of_fitness_fraction": 0.75,
            },
        },
    }


def test_one_request_asks_for_the_models_with_tissue_and_cancer_type(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    _run({"gene_symbol": "KRAS"})
    assert [path for path, _ in api.calls] == [KRAS_SCORES]
    params = api.calls[0][1]
    assert params["page[size]"] == 2000
    assert params["include"] == "model,model.sample.tissue,model.sample.cancer_type"


def test_paging_walks_the_sorted_scores(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    first = _run({"gene_symbol": "KRAS", "limit": 3})["data"]
    assert (first["returned"], first["has_more"], first["next_offset"]) == (3, True, 3)
    rest = _run({"gene_symbol": "KRAS", "limit": 500, "offset": 3})["data"]
    assert (rest["returned"], rest["has_more"], rest["next_offset"]) == (4, False, None)
    both = first["scores"] + rest["scores"]
    assert both == _run({"gene_symbol": "KRAS"})["data"]["scores"]


@pytest.mark.parametrize(
    "model", ["SIDM00903", "sidm00903", "A549", "nci-a549", "NCIA549", " a 549 "]
)
def test_model_id_is_applied_by_id_or_by_any_model_name(api, model):
    """model_id was read and dropped: every call returned the same answer."""
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    data = _run({"gene_symbol": "KRAS", "model_id": model})["data"]
    assert [(r["model_id"], r["source"]) for r in data["scores"]] == [
        ("SIDM00903", "Broad"),
        ("SIDM00903", "Sanger"),
    ]
    assert all(r["tissue"] == "Lung" and r["loss_of_fitness"] for r in data["scores"])
    assert data["total_scores"] == 2
    assert data["summary"]["screens"] == 7  # the summary is not filtered


def test_a_gene_with_no_knockout_record_is_an_explained_empty_list(api):
    api(KRAS_SCORES, _load("crispr_ko_OR4F5_none.json"))
    result = _run({"gene_symbol": "OR4F5"})
    assert result["status"] == "success"
    data = result["data"]
    assert data["scores"] == [] and data["total_scores"] == 0
    assert data["summary"]["screens"] == 0
    assert data["summary"]["loss_of_fitness_fraction"] is None
    assert "has no CRISPR knockout record" in data["note"]
    assert "does not show" in data["note"]


def test_an_unknown_model_id_is_an_error_though_the_api_answers_200(api):
    """/models/SIDM99999 answers HTTP 200 with data null, not 404."""
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    api("models/SIDM99999", _load("model_unknown.json"))
    result = _run({"gene_symbol": "KRAS", "model_id": "SIDM99999"})
    assert result["status"] == "error"
    assert "no model with the id SIDM99999" in result["error"]
    assert "DepMap_search_cell_lines" in result["error"]


def test_a_real_model_without_a_screen_is_an_explained_empty_list(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    api("models/SIDM01774", _load("model_SIDM01774.json"))
    result = _run({"gene_symbol": "KRAS", "model_id": "SIDM01774"})
    assert result["status"] == "success"
    data = result["data"]
    assert data["scores"] == []
    assert "SIDM01774 (PK-59) has no CRISPR knockout record for KRAS" in data["note"]
    assert "crispr_ko_available for this model is False" in data["note"]


def test_an_unknown_model_name_is_an_error(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    result = _run({"gene_symbol": "KRAS", "model_id": "NOT-A-LINE"})
    assert result["status"] == "error"
    assert "model named 'NOT-A-LINE'" in result["error"]
    assert [path for path, _ in api.calls] == [KRAS_SCORES]


def test_a_short_read_is_reported(api, monkeypatch):
    """The API says how many records exist; fewer rows must not pass as all."""
    body = _load("crispr_ko_KRAS_5_models.json")
    body["meta"]["count"] = 1269
    pages = {1: body["data"]}

    def get(url, params=None, timeout=None):
        api.calls.append(("paged", dict(params)))
        return _Response(dict(body, data=pages.get(params["page[number]"], [])))

    monkeypatch.setattr(D.requests, "get", get)
    data = _run({"gene_symbol": "KRAS"})["data"]
    assert [p["page[number]"] for _, p in api.calls] == [1, 2]
    assert "reported 1269" in data["warning"] and "returned 7" in data["warning"]


def test_further_pages_are_read_when_one_page_is_not_all(api, monkeypatch):
    """Also when the server sends a shorter page than the tool asked for."""
    body = _load("crispr_ko_KRAS_5_models.json")
    pages = {1: body["data"][:4], 2: body["data"][4:]}

    def get(url, params=None, timeout=None):
        api.calls.append(("paged", dict(params)))
        return _Response(dict(body, data=pages[params["page[number]"]]))

    monkeypatch.setattr(D.requests, "get", get)
    data = _run({"gene_symbol": "KRAS"})["data"]
    assert [p["page[number]"] for _, p in api.calls] == [1, 2]
    assert data["total_scores"] == 7 and "warning" not in data


def test_api_failures_are_errors(api):
    api(KRAS_SCORES, _load("crispr_ko_gene_404.json"), 404)
    result = _run({"gene_symbol": "KRAS"})
    assert result["status"] == "error" and "404" in result["error"]

    api(KRAS_SCORES, requests.exceptions.Timeout("slow"))
    assert "timeout" in _run({"gene_symbol": "KRAS"})["error"]


@pytest.mark.parametrize(
    "arguments, text",
    [
        ({}, "gene_symbol parameter is required"),
        ({"gene_symbol": "KRAS", "limit": 0}, "limit must be between 1 and 500"),
        ({"gene_symbol": "KRAS", "limit": 501}, "limit must be between 1 and 500"),
        ({"gene_symbol": "KRAS", "limit": "x"}, "must be integers"),
        ({"gene_symbol": "KRAS", "offset": -1}, "offset must be 0 or more"),
    ],
)
def test_bad_arguments_make_no_request(api, arguments, text):
    result = _run(arguments)
    assert result["status"] == "error" and text in result["error"]
    assert api.calls == []


def test_null_limit_and_offset_use_the_defaults(api):
    api(KRAS_SCORES, _load("crispr_ko_KRAS_5_models.json"))
    data = _run({"gene_symbol": "KRAS", "limit": None, "offset": None})["data"]
    assert (data["limit"], data["offset"], data["returned"]) == (50, 0, 7)


def test_no_exact_gene_match_still_reports_the_candidates(monkeypatch):
    monkeypatch.setattr(
        D.DepMapTool,
        "_search_genes",
        lambda self, arguments: {
            "status": "success",
            "data": {"genes": [dict(KRAS, symbol="KRASP1", exact_match=False)]},
        },
    )
    data = _run({"gene_symbol": "KRASP"})["data"]
    assert data["exact_match"] is None
    assert data["candidates"][0]["symbol"] == "KRASP1"
