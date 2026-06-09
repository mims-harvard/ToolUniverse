"""Alliance gene-expression uses POST /api/expression (per-annotation records).

Regression: the old GET /gene/{id}/expression-summary ribbon endpoint was
retired (now 404), so FlyBase_get_gene_expression / ZFIN_get_gene_expression
always failed. Expression now comes from POST /api/expression with a bare JSON
array of gene curies, returning per-annotation stage + location records.
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _tool():
    from tooluniverse.alliance_genome_tool import AllianceGenomeTool

    return AllianceGenomeTool(
        {
            "name": "FlyBase_get_gene_expression",
            "type": "AllianceGenomeTool",
            "fields": {"endpoint_type": "gene_expression_summary"},
        }
    )


_BODY = {
    "total": 317,
    "returnedRecords": 2,
    "results": [
        {
            "geneExpressionAnnotation": {
                "whenExpressedStageName": "embryonic stage 14",
                "whereExpressedStatement": "abdominal 1 transverse muscle cell",
                "dataProvider": {"abbreviation": "FB"},
                "evidenceItem": {"curie": "AGRKB:101000000075834"},
            }
        },
        {
            "geneExpressionAnnotation": {
                "whenExpressedStageName": "embryonic stage 15",
                "whereExpressedStatement": "dorsal vessel",
                "dataProvider": {"abbreviation": "FB"},
                "evidenceItem": {"curie": "AGRKB:101000000075835"},
            }
        },
    ],
}


class TestAllianceExpressionEndpoint(unittest.TestCase):
    def test_posts_to_expression_endpoint_with_gene_array(self):
        with patch(
            "tooluniverse.alliance_genome_tool.requests.post"
        ) as post:
            resp = MagicMock()
            resp.json.return_value = _BODY
            resp.raise_for_status.return_value = None
            post.return_value = resp
            out = _tool().run({"gene_id": "FB:FBgn0000490", "limit": 5})

        # Hit POST /expression with a bare array body of the gene curie.
        args, kwargs = post.call_args
        assert args[0].endswith("/expression")
        assert kwargs["json"] == ["FB:FBgn0000490"]
        assert kwargs["params"]["limit"] == 5

        assert out["status"] == "success"
        data = out["data"]
        assert data["total_annotations"] == 317
        assert data["returned"] == 2
        first = data["annotations"][0]
        assert first["stage"] == "embryonic stage 14"
        assert first["location"] == "abdominal 1 transverse muscle cell"
        assert first["data_provider"] == "FB"
        assert first["reference"] == "AGRKB:101000000075834"

    def test_limit_is_clamped(self):
        with patch(
            "tooluniverse.alliance_genome_tool.requests.post"
        ) as post:
            resp = MagicMock()
            resp.json.return_value = {"total": 0, "results": []}
            resp.raise_for_status.return_value = None
            post.return_value = resp
            _tool().run({"gene_id": "FB:FBgn0000490", "limit": 9999})
            assert post.call_args.kwargs["params"]["limit"] == 100

    def test_missing_gene_id_is_error(self):
        out = _tool().run({})
        assert out["status"] == "error"
        assert "gene_id" in out["error"]


if __name__ == "__main__":
    unittest.main()
