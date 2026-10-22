from unittest.mock import MagicMock, patch

from tooluniverse.gxa_tool import GxATool


def _tool():
    return GxATool(
        {
            "name": "GxA_get_experiment_expression",
            "fields": {"endpoint": "get_experiment_expression"},
        }
    )


def _response(row_count=7):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "experiment": {"description": "test"},
        "columnHeaders": [
            {"assayGroupId": "g1", "factorValue": "brain", "assayGroupSummary": {}}
        ],
        "profiles": {
            "rows": [
                {
                    "id": f"ENSG{i:011d}",
                    "name": f"GENE{i}",
                    "expressions": [{"value": float(i + 1)}],
                }
                for i in range(row_count)
            ]
        },
    }
    return response


def _catalog_response(count=7):
    response = MagicMock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "experiments": [
            {
                "experimentAccession": f"E-TEST-{index}",
                "species": "Homo sapiens",
                "rawExperimentType": "RNASEQ_MRNA_BASELINE",
            }
            for index in range(count)
        ]
    }
    return response


@patch("tooluniverse.gxa_tool.requests.get")
def test_expression_profiles_expose_recoverable_pagination(mock_get):
    mock_get.return_value = _response()

    first = _tool().run(
        {"experiment_accession": "E-MTAB-2706", "limit": 3, "offset": 0}
    )["data"]
    second = _tool().run(
        {"experiment_accession": "E-MTAB-2706", "limit": 3, "offset": 3}
    )["data"]

    assert first["total_gene_profiles"] == 7
    assert first["returned"] == first["rows_scanned"] == 3
    assert first["has_more"] is True
    assert first["next_offset"] == 3
    assert [p["gene_name"] for p in first["gene_profiles"]] == [
        "GENE0",
        "GENE1",
        "GENE2",
    ]
    assert [p["gene_name"] for p in second["gene_profiles"]] == [
        "GENE3",
        "GENE4",
        "GENE5",
    ]


@patch("tooluniverse.gxa_tool.requests.get")
def test_expression_pagination_reports_last_page(mock_get):
    mock_get.return_value = _response()

    page = _tool().run(
        {"experiment_accession": "E-MTAB-2706", "limit": 3, "offset": 6}
    )["data"]

    assert page["returned"] == page["rows_scanned"] == 1
    assert page["has_more"] is False
    assert page["next_offset"] is None


@patch("tooluniverse.gxa_tool.requests.get")
def test_experiment_catalog_exposes_recoverable_pagination(mock_get):
    mock_get.return_value = _catalog_response()
    tool = GxATool({"fields": {"endpoint": "list_experiments"}})

    page = tool.run(
        {"species": "Homo sapiens", "limit": 3, "offset": 3}
    )["data"]

    assert [row["accession"] for row in page["experiments"]] == [
        "E-TEST-3",
        "E-TEST-4",
        "E-TEST-5",
    ]
    assert page["total_experiments"] == 7
    assert page["next_offset"] == 6
