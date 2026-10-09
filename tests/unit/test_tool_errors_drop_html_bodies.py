"""HTTP errors quote the service's reason, never its HTML error page.

Found live on 2026-10-09: rest.ensembl.org answered HTTP 500 with an EBI HTML
page, and ensembl_lookup_gene reported "Ensembl API returned HTTP 500:
<!doctype html> <html lang=\"en\" class=\"vf-no-js\"> ... <script> ...". These
tools pasted the first 200 characters of any error body into their one-line
error. They now use ``upstream_reason``: a JSON message/error/detail string (or
a one-line plain-text body) is kept, an HTML page is dropped.
"""

import importlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest
import requests

from tooluniverse._lazy_registry_static import STATIC_LAZY_REGISTRY
from tooluniverse.http_utils import upstream_reason, upstream_reason_suffix
from tooluniverse.tool_registry import get_tool_registry

pytestmark = pytest.mark.unit

DATA = Path(__file__).parents[2] / "src" / "tooluniverse" / "data"

# (data file, tool name): one tool per class whose error path changed.
TOOLS = [
    ("clingen_dosage_api_tools.json", "ClinGen_dosage_by_gene"),
    ("clingen_tools.json", "ClinGen_search_gene_validity"),
    ("dailymed_tools.json", "DailyMed_parse_adverse_reactions"),
    ("ensembl_compara_tools.json", "EnsemblCompara_get_orthologues"),
    ("ensembl_map_tools.json", "EnsemblMap_convert_coordinates"),
    ("ensembl_tools.json", "Ensembl_get_transcript_haplotypes"),
    ("ensembl_vep_tools.json", "EnsemblVEP_annotate_hgvs"),
    ("ensembl_variation_ext_tools.json", "EnsemblVar_get_population_frequencies"),
    ("epigraphdb_tools.json", "EpiGraphDB_get_mendelian_randomization"),
    ("evo2_variant_effect_tools.json", "Evo2_score_variant"),
    ("fooddata_central_tools.json", "FoodDataCentral_search_foods"),
    ("idr_searchengine_tools.json", "IDR_search_images"),
    ("modomics_tools.json", "MODOMICS_list_modifications"),
    ("ncbi_variation_tools.json", "NCBIVariation_spdi_to_hgvs"),
    ("opengwas_tools.json", "OpenGWAS_get_mr_instruments"),
    ("sabiork_tools.json", "SABIO_RK_search_reactions"),
    ("spliceai_tools.json", "SpliceAI_predict_splice"),
]

HTML_PAGE = (
    '<!doctype html>\n<html lang="en" class="vf-no-js">\n  <head>\n    <script>\n'
    "(function(H){H.className=H.className.replace(/\\bvf-no-js\\b/,'vf-js')})"
    "(document.documentElement);\n</script></head><body>Error</body></html>"
)


def _config(data_file, name):
    tools = json.loads((DATA / data_file).read_text())
    return next(t for t in tools if t["name"] == name)


def _answer(status, body, content_type):
    def request(self, method, url, *args, **kwargs):
        response = requests.Response()
        response.status_code = status
        response._content = body.encode()
        response.headers["Content-Type"] = content_type
        response.url = url
        response.request = requests.Request(method, url).prepare()
        return response

    return request


def _run(data_file, name, status, body, content_type, monkeypatch):
    # Key-gated tools stop before the request without a credential.
    monkeypatch.setenv("NVIDIA_API_KEY", "test")
    monkeypatch.setenv("OPENGWAS_JWT", "test")
    config = _config(data_file, name)
    importlib.import_module(f"tooluniverse.{STATIC_LAZY_REGISTRY[config['type']]}")
    tool = get_tool_registry()[config["type"]](config)
    with (
        patch(
            "requests.sessions.Session.request",
            _answer(status, body, content_type),
        ),
        patch("time.sleep"),
    ):
        return tool.run(dict(config["test_examples"][0]))


@pytest.mark.parametrize("data_file, name", TOOLS)
def test_an_html_error_page_is_not_quoted(data_file, name, monkeypatch):
    result = _run(data_file, name, 500, HTML_PAGE, "text/html", monkeypatch)

    assert result["status"] == "error"
    assert "500" in result["error"]
    assert "<" not in result["error"]
    assert "script" not in result["error"]


@pytest.mark.parametrize("data_file, name", TOOLS)
def test_a_json_reason_is_still_quoted(data_file, name, monkeypatch):
    body = json.dumps({"error": "No valid lookup found for symbol NOTAGENE"})
    result = _run(data_file, name, 400, body, "application/json", monkeypatch)

    assert result["status"] == "error"
    assert "No valid lookup found for symbol NOTAGENE" in result["error"]


def _response(body, text=""):
    response = requests.Response()
    response.status_code = 400
    response._content = (json.dumps(body) if body is not None else text).encode()
    return response


def test_nested_ncbi_style_message_is_read():
    body = {"error": {"code": 400, "message": "Invalid SPDI: 'NC_000001.11:x'"}}
    assert upstream_reason(_response(body)) == "Invalid SPDI: 'NC_000001.11:x'"


@pytest.mark.parametrize(
    "response, suffix",
    [
        (None, ""),
        (_response(None, HTML_PAGE), ""),
        (_response({"message": "bad id"}), ": bad id"),
    ],
)
def test_suffix(response, suffix):
    assert upstream_reason_suffix(response) == suffix
