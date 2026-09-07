"""Contract tests for NCBI Datasets endpoints, errors, and request handling."""

import json
from pathlib import Path

import pytest
import requests
from jsonschema import ValidationError, validate

from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool

pytestmark = pytest.mark.unit


class _FakeResponse:
    def __init__(self, payload, *, status_code=200, headers=None):
        self._payload = payload
        self.status_code = status_code
        self.headers = headers or {}
        self.closed = False

    def raise_for_status(self):
        if self.status_code >= 400:
            error = requests.exceptions.HTTPError(f"HTTP {self.status_code}")
            error.response = self
            raise error

    def json(self):
        return self._payload

    def close(self):
        self.closed = True


@pytest.mark.parametrize(
    ("endpoint_type", "arguments", "expected_suffix", "payload"),
    [
        (
            "gene_by_id",
            {"gene_id": "7157"},
            "/gene/id/7157/dataset_report",
            {
                "reports": [
                    {
                        "gene": {
                            "gene_id": "7157",
                            "symbol": "TP53",
                            "annotations": [],
                        }
                    }
                ]
            },
        ),
        (
            "gene_by_symbol",
            {"symbol": "TP53", "taxon": "human"},
            "/gene/symbol/TP53/taxon/human/dataset_report",
            {
                "reports": [
                    {
                        "gene": {
                            "gene_id": "7157",
                            "symbol": "TP53",
                        }
                    }
                ]
            },
        ),
    ],
)
def test_gene_tools_use_active_dataset_report_endpoints(
    monkeypatch, endpoint_type, arguments, expected_suffix, payload
):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse(payload)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": f"test_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
        }
    )

    result = tool.run(arguments)

    assert result["status"] == "success"
    symbols = (
        [result["data"]["symbol"]]
        if endpoint_type == "gene_by_id"
        else [item["symbol"] for item in result["data"]]
    )
    assert symbols == ["TP53"]
    assert calls[0][0].endswith(expected_suffix)


def test_transient_throttle_retries_and_honors_retry_after(monkeypatch):
    throttled = _FakeResponse(
        {"error": "rate limited"},
        status_code=429,
        headers={"Retry-After": "0"},
    )
    success = _FakeResponse(
        {
            "reports": [
                {
                    "gene": {
                        "gene_id": "7157",
                        "symbol": "TP53",
                        "annotations": [],
                    }
                }
            ]
        }
    )
    responses = iter([throttled, success])
    sleeps = []

    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: next(responses),
    )
    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.time.sleep", sleeps.append)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result["status"] == "success"
    assert result["data"]["symbol"] == "TP53"
    assert throttled.closed is True
    assert sleeps == [0.0]


def test_transient_timeout_is_retried_with_bounded_backoff(monkeypatch):
    responses = iter(
        [
            requests.exceptions.Timeout("temporary timeout"),
            _FakeResponse({"reports": []}),
        ]
    )
    sleeps = []

    def fake_get(url, **kwargs):
        response = next(responses)
        if isinstance(response, Exception):
            raise response
        return response

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.time.sleep", sleeps.append)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result["status"] == "success"
    assert sleeps == [0.5]


def test_transient_http_failure_stops_after_three_attempts(monkeypatch):
    calls = []
    sleeps = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse(
            {"message": "Service temporarily unavailable."}, status_code=503
        )

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.time.sleep", sleeps.append)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert len(calls) == 3
    assert sleeps == [0.5, 1.0]
    assert result == {
        "status": "error",
        "error": ("NCBI Datasets API HTTP 503: Service temporarily unavailable."),
    }


def test_ortholog_page_size_is_enforced_when_ncbi_returns_full_set(monkeypatch):
    calls = []
    payload = {
        "reports": [
            {"gene": {"gene_id": str(index), "symbol": f"GENE{index}"}}
            for index in range(5)
        ],
        "total_count": 5,
    }

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse(payload)

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_orthologs",
            "fields": {"endpoint_type": "gene_orthologs"},
        }
    )

    result = tool.run({"gene_id": "7157", "page_size": 2})

    assert [item["gene_id"] for item in result["data"]] == ["0", "1"]
    assert result["metadata"]["total_available"] == 5
    assert result["metadata"]["returned"] == 2
    assert calls[0][1]["params"]["page_size"] == 2


@pytest.mark.parametrize(
    "payload",
    [
        {
            "messages": [
                {"error": {"message": "The provided taxonomy token is unrecognized."}}
            ]
        },
        {
            "reports": [
                {
                    "query": ["99999999"],
                    "errors": [
                        {
                            "reason": "The taxonomy name is not recognized.",
                            "invalid_identifiers": ["99999999"],
                        }
                    ],
                }
            ]
        },
    ],
)
def test_http_200_embedded_ncbi_errors_are_not_reported_as_success(
    monkeypatch, payload
):
    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: _FakeResponse(payload),
    )
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_taxonomy",
            "fields": {"endpoint_type": "taxonomy"},
        }
    )

    result = tool.run({"tax_id": "99999999"})

    assert result["status"] == "error"
    assert "taxonomy" in result["error"].lower()


def test_http_error_preserves_ncbi_diagnostic(monkeypatch):
    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: _FakeResponse(
            {
                "error": "Bad Request",
                "code": 400,
                "message": "Invalid argument type for gene_ids.",
            },
            status_code=400,
        ),
    )
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "999999999999"})

    assert result == {
        "status": "error",
        "error": ("NCBI Datasets API HTTP 400: Invalid argument type for gene_ids."),
    }


@pytest.mark.parametrize(
    ("payload", "expected_message"),
    [
        (
            {"error": "Too many requests for this API key."},
            "Too many requests for this API key.",
        ),
        ({"error": {"message": "Invalid page token."}}, "Invalid page token."),
        (
            {"messages": [{"error": "Taxonomy lookup failed."}]},
            "Taxonomy lookup failed.",
        ),
    ],
)
def test_ncbi_error_variants_preserve_the_upstream_diagnostic(
    monkeypatch, payload, expected_message
):
    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: _FakeResponse(payload, status_code=400),
    )
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result["status"] == "error"
    assert expected_message in result["error"]


def test_non_json_success_response_has_a_clear_protocol_error(monkeypatch):
    class _NonJsonResponse(_FakeResponse):
        def json(self):
            raise ValueError("not JSON")

    monkeypatch.setattr(
        "tooluniverse.ncbi_datasets_tool.requests.get",
        lambda url, **kwargs: _NonJsonResponse("<html>proxy error</html>"),
    )
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result == {
        "status": "error",
        "error": "NCBI Datasets API returned invalid JSON",
    }


def test_optional_api_key_is_read_from_environment_and_sent_as_header(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse({"reports": []})

    monkeypatch.setenv("NCBI_API_KEY", "secret-test-key")
    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene",
            "fields": {"endpoint_type": "gene_by_id"},
        }
    )

    result = tool.run({"gene_id": "7157"})

    assert result["status"] == "success"
    assert calls[0][1]["headers"]["api-key"] == "secret-test-key"


def test_user_controlled_path_segments_are_percent_encoded(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append(url)
        return _FakeResponse({"reports": []})

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene_by_symbol",
            "fields": {"endpoint_type": "gene_by_symbol"},
        }
    )

    result = tool.run({"symbol": "A/B", "taxon": "Homo sapiens"})

    assert result["status"] == "success"
    assert "/symbol/A%2FB/taxon/Homo%20sapiens/dataset_report" in calls[0]


def test_sequence_reports_exposes_ncbi_pagination(monkeypatch):
    calls = []

    def fake_get(url, **kwargs):
        calls.append((url, kwargs))
        return _FakeResponse(
            {
                "reports": [
                    {
                        "chr_name": "1",
                        "refseq_accession": "NC_000001.11",
                        "length": 248956422,
                    }
                ],
                "total_count": 25,
                "next_page_token": "next-token",
            }
        )

    monkeypatch.setattr("tooluniverse.ncbi_datasets_tool.requests.get", fake_get)
    tool = NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_sequence_reports",
            "fields": {"endpoint_type": "sequence_reports"},
        }
    )

    result = tool.run(
        {
            "accession": "GCF_000001405.40",
            "page_size": 1,
            "page_token": "previous-token",
        }
    )

    assert result["status"] == "success"
    assert result["metadata"]["total_available"] == 25
    assert result["metadata"]["next_page_token"] == "next-token"
    assert calls[0][1]["params"] == {
        "page_size": 1,
        "page_token": "previous-token",
    }


def test_ncbi_parameter_schemas_reject_invalid_boundary_values():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )
    configs = {item["name"]: item for item in json.loads(config_path.read_text())}
    invalid_cases = [
        ("NCBIDatasets_get_gene", {"gene_id": "TP53"}),
        ("NCBIDatasets_get_orthologs", {"gene_id": "7157", "page_size": 0}),
        ("NCBIDatasets_get_taxonomy", {"tax_id": "human"}),
        ("NCBIDatasets_suggest_taxonomy", {"query": "   "}),
        (
            "NCBIDatasets_get_genome_assembly",
            {"accession": "NC_000913.3"},
        ),
        (
            "NCBIDatasets_list_genomes_by_taxon",
            {"taxon": "human", "limit": 101},
        ),
        (
            "NCBIDatasets_get_sequence_reports",
            {"accession": "GCF_000005845.2", "page_size": 0},
        ),
        (
            "NCBIDatasets_get_sequence_reports",
            {"accession": "GCF_000005845.2", "page_token": "   "},
        ),
    ]

    for name, arguments in invalid_cases:
        with pytest.raises(ValidationError):
            validate(arguments, configs[name]["parameter"])


def test_ncbi_return_schemas_describe_success_data_not_outer_envelope():
    config_path = (
        Path(__file__).parents[2]
        / "src"
        / "tooluniverse"
        / "data"
        / "ncbi_datasets_tools.json"
    )
    configs = json.loads(config_path.read_text())

    for config in configs:
        branches = config["return_schema"].get("oneOf", [])
        assert not any(
            "data" in (branch.get("properties") or {}) for branch in branches
        ), config["name"]
