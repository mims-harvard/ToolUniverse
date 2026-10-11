"""MedlinePlus genetics lookups take names, not only page slugs.

The genetics endpoints are keyed by page slug: "Alport syndrome" answered 404
(with MedlinePlus's HTML error page pasted into the error) although
https://medlineplus.gov/genetics/condition/alport-syndrome exists. An agent
passes names, so 7 of 7 condition lookups in one clinical run failed this way.
Names are now resolved through MedlinePlus's own index (TopicIndex.xml: every
condition and gene page with its title and other names); a name with no page
is an error listing the closest pages, and the slug form is used when the
index cannot be read.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse import medlineplus_tool as M

pytestmark = pytest.mark.unit

# A slice of the real index (2026-10-11), same structure.
INDEX = b"""<?xml version="1.0" encoding="utf-8"?>
<genetics_home_reference_topic_list version="3.0">
<topic id="Conditions"><topics>
<topic><url>https://medlineplus.gov/genetics/condition/alport-syndrome</url><title>Alport syndrome</title>
<other_names><other_name>Hematuric hereditary nephritis</other_name></other_names></topic>
<topic><url>https://medlineplus.gov/genetics/condition/marfan-syndrome</url><title>Marfan syndrome</title></topic>
<topic><url>https://medlineplus.gov/genetics/condition/renal-tubular-acidosis-with-deafness</url>
<title>Renal tubular acidosis with deafness</title>
<other_names><other_name>Renal tubular acidosis type 1b</other_name></other_names></topic>
</topics></topic>
<topic id="Genes"><topics>
<topic><url>https://medlineplus.gov/genetics/gene/fbn1</url><title>FBN1: fibrillin 1</title></topic>
<topic><url>https://medlineplus.gov/genetics/gene/col4a5</url><title>COL4A5: collagen type IV alpha 5 chain</title></topic>
</topics></topic>
<topic id="Chromosomes"><topics>
<topic><url>https://medlineplus.gov/genetics/chromosome/1</url><title>Chromosome 1</title></topic>
</topics></topic>
</genetics_home_reference_topic_list>"""

CONDITION = {"name": "Alport syndrome", "text-list": [], "related-gene-list": []}
GENE = {"name": "fibrillin 1", "text-list": []}


def _response(status=200, json_body=None, content=b"", text=""):
    response = MagicMock()
    response.status_code = status
    response.content = content
    response.text = text
    response.json.return_value = json_body
    response.raise_for_status.side_effect = (
        None if status == 200 else M.requests.HTTPError(f"HTTP {status}")
    )
    return response


@pytest.fixture(autouse=True)
def fresh_index():
    M._genetics_pages.cache_clear()
    yield
    M._genetics_pages.cache_clear()


def _tool(name):
    configs = {
        "MedlinePlus_get_genetics_condition_by_name": (
            "https://medlineplus.gov/download/genetics/condition/{condition}.{format}",
            {"condition": {"type": "string"}, "format": {"type": "string", "default": "json"}},
        ),
        "MedlinePlus_get_genetics_gene_by_name": (
            "https://medlineplus.gov/download/genetics/gene/{gene}.{format}",
            {"gene": {"type": "string"}, "format": {"type": "string", "default": "json"}},
        ),
    }
    endpoint, properties = configs[name]
    return M.MedlinePlusRESTTool(
        {"name": name, "fields": {"endpoint": endpoint}, "parameter": {"properties": properties}}
    )


def _run(name, arguments, page_json, index=INDEX, index_status=200):
    def fake_get(url, timeout=None):
        if url == M._GENETICS_INDEX_URL:
            return _response(index_status, content=index)
        return _response(200, json_body=page_json, text="{}")

    with patch.object(M.requests, "get", side_effect=fake_get) as get:
        result = _tool(name).run(arguments)
    return result, [call.args[0] for call in get.call_args_list]


@pytest.mark.parametrize(
    "name, slug",
    [
        ("Alport syndrome", "alport-syndrome"),
        ("ALPORT SYNDROME", "alport-syndrome"),
        ("Hematuric hereditary nephritis", "alport-syndrome"),
        ("alport-syndrome", "alport-syndrome"),
        ("Marfan's syndrome", "marfan-syndrome"),
        ("Renal tubular acidosis type 1b", "renal-tubular-acidosis-with-deafness"),
    ],
)
def test_condition_names_resolve_to_their_page(name, slug):
    result, urls = _run("MedlinePlus_get_genetics_condition_by_name", {"condition": name}, CONDITION)
    assert urls[-1] == f"https://medlineplus.gov/download/genetics/condition/{slug}.json"
    assert result["name"] == "Alport syndrome"
    if name != slug:
        assert result["resolved_name"]["query"] == name


@pytest.mark.parametrize("name", ["FBN1", "fbn1", "fibrillin 1", "Fibrillin-1"])
def test_genes_resolve_by_symbol_or_full_name(name):
    _result, urls = _run("MedlinePlus_get_genetics_gene_by_name", {"gene": name}, GENE)
    assert urls[-1] == "https://medlineplus.gov/download/genetics/gene/fbn1.json"


def test_a_name_without_a_page_lists_the_closest_pages_and_fetches_nothing_else():
    result, urls = _run(
        "MedlinePlus_get_genetics_condition_by_name", {"condition": "renal tubular acidosis"}, CONDITION
    )
    assert result["status"] == "error"
    assert "no condition page named 'renal tubular acidosis'" in result["error"]
    assert result["suggestions"] == ["Renal tubular acidosis with deafness"]
    assert urls == [M._GENETICS_INDEX_URL]


def test_a_gene_without_a_page_says_so():
    result, _urls = _run("MedlinePlus_get_genetics_gene_by_name", {"gene": "APOL1"}, GENE)
    assert result["status"] == "error" and "no gene page named 'APOL1'" in result["error"]
    assert "search_topics_by_keyword" not in result["hint"]


def test_a_common_disease_is_pointed_to_the_health_topics_search():
    # In a clinical agent's run: "chronic kidney disease", "genetic kidney disease".
    result, urls = _run(
        "MedlinePlus_get_genetics_condition_by_name", {"condition": "chronic kidney disease"}, CONDITION
    )
    assert result["status"] == "error" and result["suggestions"] == []
    assert "MedlinePlus_search_topics_by_keyword" in result["hint"]
    assert urls == [M._GENETICS_INDEX_URL]


def test_the_slug_form_is_used_when_the_index_cannot_be_read():
    _result, urls = _run(
        "MedlinePlus_get_genetics_condition_by_name",
        {"condition": "Alport Syndrome"},
        CONDITION,
        index_status=503,
    )
    assert urls[-1] == "https://medlineplus.gov/download/genetics/condition/alport-syndrome.json"


def test_the_index_is_fetched_once_per_process():
    calls = []

    def fake_get(url, timeout=None):
        calls.append(url)
        if url == M._GENETICS_INDEX_URL:
            return _response(200, content=INDEX)
        return _response(200, json_body=CONDITION, text="{}")

    tool = _tool("MedlinePlus_get_genetics_condition_by_name")
    with patch.object(M.requests, "get", side_effect=fake_get):
        tool.run({"condition": "Alport syndrome"})
        tool.run({"condition": "Marfan syndrome"})
    assert calls.count(M._GENETICS_INDEX_URL) == 1


def test_a_404_error_carries_no_html_page():
    def fake_get(url, timeout=None):
        if url == M._GENETICS_INDEX_URL:
            return _response(200, content=INDEX)
        page = _response(404, text="<!DOCTYPE html>\n<html lang='en'>...</html>")
        page.json.side_effect = ValueError("not json")
        return page

    with patch.object(M.requests, "get", side_effect=fake_get):
        result = _tool("MedlinePlus_get_genetics_condition_by_name").run({"condition": "Alport syndrome"})
    assert result["status"] == "error"
    assert result["error"] == "MedlinePlus returned non-200 status code: 404"
    assert "html" not in str(result).lower()
