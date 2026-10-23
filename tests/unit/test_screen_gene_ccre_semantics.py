"""Round 223: SCREEN gene lookup must return cCREs, never ENCODE experiments."""

import inspect
import json
from unittest.mock import MagicMock, patch

import pytest
from jsonschema import validate

from tooluniverse.screen_tool import SCREENRESTTool

pytestmark = pytest.mark.unit


def _config():
    with open("src/tooluniverse/data/screen_tools.json") as handle:
        return json.load(handle)[0]


def _gene_response(display_name="TP53"):
    response = MagicMock()
    response.status_code = 200
    response.url = "https://rest.ensembl.org/lookup/symbol/homo_sapiens/TP53"
    response.json.return_value = {
        "id": "ENSG00000141510",
        "display_name": display_name,
        "assembly_name": "GRCh38",
        "seq_region_name": "17",
        "start": 7661779,
        "end": 7687546,
        "strand": -1,
    }
    response.raise_for_status.return_value = None
    return response


def _ccres():
    return [
        {"accession": "E1", "element_type": "pELS", "chrom": "chr17", "start": 1},
        {"accession": "E2", "element_type": "PLS", "chrom": "chr17", "start": 2},
        {"accession": "E3", "element_type": "dELS", "chrom": "chr17", "start": 3},
        {"accession": "E4", "element_type": "CTCF-only", "chrom": "chr17", "start": 4},
        {"accession": "E5", "element_type": "pELS", "chrom": "chr17", "start": 5},
    ]


def test_gene_is_resolved_to_region_and_real_ccre_classes_are_filtered():
    """Enhancer results must be pELS/dELS cCREs with exact local pagination."""
    tool = SCREENRESTTool(_config())
    with (
        patch(
            "tooluniverse.screen_tool.request_with_retry",
            return_value=_gene_response(),
        ) as lookup,
        patch(
            "tooluniverse.screen_tool.ScreenCcreTool.run",
            return_value={"status": "success", "data": _ccres()},
        ) as screen,
    ):
        result = tool.run(
            {
                "gene_name": "TP53",
                "element_type": "enhancer",
                "limit": 2,
                "offset": 1,
                "flank_bp": 10000,
            }
        )

    assert result["status"] == "success"
    assert [row["accession"] for row in result["data"]["regulatory_elements"]] == [
        "E3",
        "E5",
    ]
    assert result["data"]["total_results"] == 3
    assert result["data"]["functional_association_claimed"] is False
    assert result["metadata"]["element_classes_applied"] == ["dELS", "pELS"]
    assert result["metadata"]["result_set_complete"] is False
    assert lookup.call_args.kwargs["max_attempts"] == 3
    call = screen.call_args.args[0]
    assert call == {
        "chrom": "17",
        "start": 7651779,
        "end": 7697546,
        "assembly": "GRCh38",
    }
    validate(result["data"], _config()["return_schema"])


def test_promoter_and_enhancer_no_longer_return_identical_experiments():
    """The element_type parameter must select actual cCRE classifications."""

    def run(element_type):
        tool = SCREENRESTTool(_config())
        with (
            patch(
                "tooluniverse.screen_tool.request_with_retry",
                return_value=_gene_response(),
            ),
            patch(
                "tooluniverse.screen_tool.ScreenCcreTool.run",
                return_value={"status": "success", "data": _ccres()},
            ),
        ):
            return tool.run({"gene_name": "TP53", "element_type": element_type})

    promoter = run("promoter")
    enhancer = run("enhancer")
    assert [x["accession"] for x in promoter["data"]["regulatory_elements"]] == ["E2"]
    assert [x["accession"] for x in enhancer["data"]["regulatory_elements"]] == [
        "E1",
        "E3",
        "E5",
    ]
    assert all("assay_title" not in x for x in enhancer["data"]["regulatory_elements"])


@pytest.mark.parametrize(
    "arguments,fragment",
    [
        ({}, "gene_name"),
        ({"gene_name": "TP53", "query": "BRCA1"}, "Conflicting"),
        ({"gene_name": "TP53", "element_type": "banana"}, "element_type"),
        ({"gene_name": "TP53", "limit": True}, "limit"),
        ({"gene_name": "TP53", "offset": -1}, "offset"),
        ({"gene_name": "TP53", "flank_bp": 1000001}, "flank_bp"),
        ({"gene_name": "TP53", "assembly": "GRCh37"}, "GRCh38"),
        ({"gene_name": "TP53", "offest": 2}, "offest"),
    ],
)
def test_invalid_or_ignored_arguments_fail_before_network(arguments, fragment):
    """Typos and unsupported semantics cannot degrade into a plausible broad result."""
    tool = SCREENRESTTool(_config())
    with patch("tooluniverse.screen_tool.request_with_retry") as lookup:
        result = tool.run(arguments)
    assert result["status"] == "error"
    assert fragment.lower() in result["error"].lower()
    lookup.assert_not_called()


def test_ensembl_identity_mismatch_is_rejected():
    """A different resolved symbol cannot silently substitute for the requested gene."""
    tool = SCREENRESTTool(_config())
    with (
        patch(
            "tooluniverse.screen_tool.request_with_retry",
            return_value=_gene_response(display_name="TP53AIP1"),
        ),
        patch("tooluniverse.screen_tool.ScreenCcreTool.run") as screen,
    ):
        result = tool.run({"gene_name": "TP53"})
    assert result["status"] == "error"
    assert "different official gene symbol" in result["error"]
    screen.assert_not_called()


def test_screen_failure_is_propagated_without_fabricated_empty_success():
    """An unavailable SCREEN backend must remain an error, not an empty cCRE set."""
    tool = SCREENRESTTool(_config())
    with (
        patch(
            "tooluniverse.screen_tool.request_with_retry",
            return_value=_gene_response(),
        ),
        patch(
            "tooluniverse.screen_tool.ScreenCcreTool.run",
            return_value={"status": "error", "error": "SCREEN unavailable"},
        ),
    ):
        result = tool.run({"gene_name": "TP53"})
    assert result == {"status": "error", "error": "SCREEN unavailable"}


def test_repeated_gene_queries_reuse_validated_ensembl_coordinates():
    """One agent workflow must not repeatedly hit Ensembl for the same symbol."""
    tool = SCREENRESTTool(_config())
    with (
        patch(
            "tooluniverse.screen_tool.request_with_retry",
            return_value=_gene_response(),
        ) as lookup,
        patch(
            "tooluniverse.screen_tool.ScreenCcreTool.run",
            return_value={"status": "success", "data": _ccres()},
        ),
    ):
        assert (
            tool.run({"gene_name": "TP53", "element_type": "enhancer"})["status"]
            == "success"
        )
        assert (
            tool.run({"gene_name": "tp53", "element_type": "promoter"})["status"]
            == "success"
        )

    lookup.assert_called_once()


def test_config_and_wrapper_expose_real_gene_window_controls():
    """Configuration must no longer claim ENCODE experiments are SCREEN cCREs."""
    config = _config()
    assert "encodeproject.org/search" not in json.dumps(config)
    assert config["fields"]["screen_endpoint"].endswith("/graphql")
    assert {"offset", "flank_bp", "assembly"} <= set(config["parameter"]["properties"])

    from tooluniverse.tools.SCREEN_get_regulatory_elements import (
        SCREEN_get_regulatory_elements,
    )

    parameters = inspect.signature(SCREEN_get_regulatory_elements).parameters
    assert {"offset", "flank_bp", "assembly"} <= set(parameters)
