"""MyVariant must name the assembly its coordinates live in, and offer hg38.

Regression for Fix-R33. MyVariantTool never sent MyVariant.info's `assembly`
query parameter and never named the frame it got back, so every coordinate came
out in an unlabelled reference. MyVariant's default is GRCh37/hg19: for
rs4244285 it answers `chr10:g.96541616G>C`, roughly 1.76 Mb from the
`chr10:g.94781859G>C` that EnsemblVar_get_population_frequencies reports for the
same variant on GRCh38 -- and only the Ensembl tool said which frame it meant.

Verified live before the fix:

    curl 'https://myvariant.info/v1/query?q=rs4244285&fields=_id'
      -> chr10:g.96541616G>C
    curl 'https://myvariant.info/v1/query?q=rs4244285&fields=_id&assembly=hg38'
      -> chr10:g.94781859G>C
    curl 'https://myvariant.info/v1/variant/chr10:g.96541616G>C?assembly=hg38'
      -> 404

The last probe is why the descriptions and the 404 message insist an HGVS id
must already be written in the assembly you ask for: /variant/ is a verbatim key
lookup, not a liftover.

The fix is additive: `assembly` defaults to "hg19", and for hg19 the upstream
request omits the parameter entirely, so the default response is exactly what it
was. The new `coordinate_assembly` key sits beside `status`/`data` rather than
inside `data`, because `data` is MyVariant's own payload -- and for an rsID it is
sometimes a list, which has nowhere to put a key.

All assertions run against synthetic MyVariant payloads -- no network.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

import tooluniverse  # noqa: E402
from tooluniverse.mygene_tool import MyVariantTool  # noqa: E402

pytestmark = pytest.mark.unit

DATA_DIR = Path(tooluniverse.__file__).parent / "data"

HG19_ID = "chr10:g.96541616G>C"
HG38_ID = "chr10:g.94781859G>C"
HG19_RECORD = {"_id": HG19_ID, "cadd": {"phred": 22.1}}
HG38_RECORD = {"_id": HG38_ID, "cadd": {"phred": 22.1}}

ANNOTATION_CONFIG = {
    "name": "MyVariant_get_variant_annotation",
    "type": "MyVariantTool",
    "fields": {"operation": "get_variant"},
    "parameter": {
        "properties": {"fields": {"default": "dbsnp,clinvar,cadd,gnomad_genome,dbnsfp"}}
    },
}
QUERY_CONFIG = {
    "name": "MyVariant_query_variants",
    "type": "MyVariantTool",
    "fields": {"operation": "query"},
    "parameter": {"properties": {}},
}


def _response(payload):
    response = MagicMock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def _not_found():
    """A 404 response whose HTTPError carries it, as requests builds it."""
    response = _response({})
    response.status_code = 404
    error = requests.HTTPError("404 Client Error: Not Found.")
    error.response = response
    response.raise_for_status.side_effect = error
    return response


def _run(config, arguments, payload):
    """Run the tool against one canned payload; returns (result, request calls)."""
    tool = MyVariantTool(config)
    with patch(
        "tooluniverse.mygene_tool.requests.get", return_value=_response(payload)
    ) as get:
        result = tool.run(arguments)
    return result, get.call_args_list


def test_default_request_omits_assembly_so_upstream_call_is_unchanged():
    """hg19 is MyVariant's own default; sending it would be a new request."""
    _, calls = _run(ANNOTATION_CONFIG, {"variant_id": "rs4244285"}, HG19_RECORD)

    assert len(calls) == 1
    assert "assembly" not in calls[0].kwargs["params"]


def test_default_response_labels_hg19_with_both_nomenclatures():
    result, _ = _run(ANNOTATION_CONFIG, {"variant_id": "rs4244285"}, HG19_RECORD)

    assert result["status"] == "success"
    assert result["coordinate_assembly"] == "hg19 (GRCh37)"


def test_default_data_payload_is_untouched():
    """Additive: a caller reading `data` sees exactly the old bytes."""
    payload = {
        "_id": HG19_ID,
        "_version": 1,
        "dbsnp": {"rsid": "rs4244285"},
        "cadd": {"phred": 22.1},
    }
    result, _ = _run(ANNOTATION_CONFIG, {"variant_id": "rs4244285"}, dict(payload))

    assert result["data"] == payload


def test_hg38_is_forwarded_upstream_and_labelled():
    result, calls = _run(
        ANNOTATION_CONFIG,
        {"variant_id": "rs4244285", "assembly": "hg38"},
        HG38_RECORD,
    )

    assert calls[0].kwargs["params"]["assembly"] == "hg38"
    assert result["coordinate_assembly"] == "hg38 (GRCh38)"
    assert result["data"]["_id"] == HG38_ID


def test_query_operation_forwards_and_labels_the_assembly_too():
    hits = {"took": 3, "total": 3, "hits": [{"_id": HG38_ID}]}
    result, calls = _run(QUERY_CONFIG, {"query": "rs4244285", "assembly": "hg38"}, hits)

    assert calls[0].kwargs["params"]["assembly"] == "hg38"
    assert result["coordinate_assembly"] == "hg38 (GRCh38)"
    assert result["data"] == hits


def test_query_operation_default_omits_assembly_and_labels_hg19():
    hits = {"took": 3, "total": 3, "hits": [HG19_RECORD]}
    result, calls = _run(QUERY_CONFIG, {"query": "rs4244285"}, hits)

    assert "assembly" not in calls[0].kwargs["params"]
    assert result["coordinate_assembly"] == "hg19 (GRCh37)"


def test_unknown_assembly_is_rejected_before_any_request():
    tool = MyVariantTool(ANNOTATION_CONFIG)
    with patch("tooluniverse.mygene_tool.requests.get") as get:
        result = tool.run({"variant_id": "rs4244285", "assembly": "grch38"})

    assert result["status"] == "error"
    assert "grch38" in result["error"]
    assert "hg19, hg38" in result["error"]
    get.assert_not_called()


def test_404_on_an_hgvs_id_names_the_assembly_mismatch():
    """The hazard is silent: /variant/ looks ids up verbatim, it never lifts over."""
    tool = MyVariantTool(ANNOTATION_CONFIG)
    with patch("tooluniverse.mygene_tool.requests.get", return_value=_not_found()):
        result = tool.run({"variant_id": HG19_ID, "assembly": "hg38"})

    assert result["status"] == "error"
    assert result["coordinate_assembly"] == "hg38 (GRCh38)"
    assert HG19_ID in result["error"]
    assert "hg38 (GRCh38)" in result["error"]
    assert "rsID" in result["error"]


def test_404_on_an_rsid_does_not_blame_the_assembly():
    """An rsID resolves in either assembly, so the mismatch advice would mislead."""
    tool = MyVariantTool(ANNOTATION_CONFIG)
    with patch("tooluniverse.mygene_tool.requests.get", return_value=_not_found()):
        result = tool.run({"variant_id": "rs99999999999", "assembly": "hg38"})

    assert "never lifts coordinates over" not in result["error"]


@pytest.mark.parametrize(
    "tool_name",
    [
        "MyVariant_query_variants",
        "MyVariant_get_variant_annotation",
        "MyVariant_get_pathogenicity_scores",
    ],
)
def test_config_declares_assembly_and_documents_the_default_frame(tool_name):
    configs = json.loads((DATA_DIR / "biothings_tools.json").read_text())
    cfg = next(c for c in configs if c["name"] == tool_name)

    assembly = cfg["parameter"]["properties"]["assembly"]
    assert assembly["enum"] == ["hg19", "hg38"]
    assert assembly["default"] == "hg19"
    assert "assembly" not in cfg["parameter"].get("required", [])

    description = cfg["description"]
    assert "hg19/GRCh37" in description
    assert "hg38/GRCh38" in description
    assert "coordinate_assembly" in description


@pytest.mark.parametrize(
    "tool_name",
    ["MyVariant_get_variant_annotation", "MyVariant_get_pathogenicity_scores"],
)
def test_hgvs_tool_descriptions_warn_that_the_id_is_not_lifted_over(tool_name):
    configs = json.loads((DATA_DIR / "biothings_tools.json").read_text())
    description = next(c for c in configs if c["name"] == tool_name)["description"]

    assert "SAME assembly" in description
    assert "404" in description
    assert "rsID works in either" in description
