from unittest.mock import MagicMock, patch

from tooluniverse.pombase_tool import PomBaseTool


def _tool(endpoint):
    return PomBaseTool(
        {"name": f"PomBase_{endpoint}", "fields": {"endpoint_type": endpoint}}
    )


def _response(payload):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    return response


def _annotations(prefix, count):
    return [{"term": f"{prefix}:{i:07d}"} for i in range(count)]


@patch("tooluniverse.pombase_tool.requests.get")
def test_all_single_and_multi_locus_phenotypes_are_returned(mock_get):
    single = _annotations("FYPO", 67)
    multi = _annotations("FYPO", 58)
    mock_get.return_value = _response(
        {
            "uniquename": "SPBC11B10.09",
            "cv_annotations": {
                "single_locus_phenotype": single,
                "multi_locus_phenotype": multi,
            },
            "terms_by_termid": {},
        }
    )

    data = _tool("gene_phenotypes").run({"gene_id": "SPBC11B10.09"})["data"]

    assert data["phenotype_count"] == len(data["phenotypes"]) == 125
    assert sum(p["cv_name"] == "single_locus_phenotype" for p in data["phenotypes"]) == 67
    assert sum(p["cv_name"] == "multi_locus_phenotype" for p in data["phenotypes"]) == 58


@patch("tooluniverse.pombase_tool.requests.get")
def test_all_go_annotations_are_returned(mock_get):
    mock_get.return_value = _response(
        {
            "uniquename": "SPBC11B10.09",
            "cv_annotations": {
                "biological_process": _annotations("GO", 40),
                "molecular_function": _annotations("GO", 5),
                "cellular_component": _annotations("GO", 14),
            },
            "terms_by_termid": {},
        }
    )

    data = _tool("gene_go_annotations").run({"gene_id": "SPBC11B10.09"})["data"]

    assert data["aspect_counts"] == {
        "biological_process": 40,
        "molecular_function": 5,
        "cellular_component": 14,
    }
    assert data["go_term_count"] == len(data["go_terms"]) == 59


@patch("tooluniverse.pombase_tool.requests.get")
def test_gene_detail_preserves_all_domain_matches(mock_get):
    interpro = [
        {"id": f"IPR{i}", "dbname": "InterPro", "match_start": i, "match_end": i + 1}
        for i in range(29)
    ]
    tm_domains = [{"start": i, "end": i + 10} for i in range(12)]
    mock_get.return_value = _response(
        {
            "uniquename": "SPAC1093.06c",
            "interpro_matches": interpro,
            "tm_domain_coords": tm_domains,
        }
    )

    data = _tool("gene_detail").run({"gene_id": "SPAC1093.06c"})["data"]

    assert data["interpro_domain_count"] == len(data["interpro_domains"]) == 29
    assert data["tm_domain_count"] == len(data["tm_domains"]) == 12
