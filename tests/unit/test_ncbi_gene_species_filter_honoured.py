"""Fix-47-3: NCBIDatasets_get_gene_by_symbol ignored the species the caller
asked for, then echoed the default back as if it had been applied.

The parameter is named `taxon`, but the tool's own description asks the caller
to "look up gene information by gene symbol and ORGANISM", and the sibling
species-scoped tool in the library (UniProt_search) calls it `organism`. A
caller who followed either had the value dropped -- the schema declared no
`organism`/`species`, and an unknown key alongside a recognized one is
deliberately passed through rather than rejected -- and the lookup fell back to
"human". Confirmed live: `{"symbol":"NR2F2","organism":"mouse"}` returned human
NR2F2 (gene_id 7026, tax_id 9606) under `metadata.query_taxon: "human"`, and
`organism: "Vulcan"` returned that same human gene just as confidently.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.ncbi_datasets_tool import NCBIDatasetsTool

pytestmark = pytest.mark.unit

_MOUSE = {
    "reports": [
        {
            "gene": {
                "gene_id": "11819",
                "symbol": "Nr2f2",
                "tax_id": "10090",
                "taxname": "Mus musculus",
                "chromosomes": ["7"],
            }
        }
    ]
}


def _tool():
    return NCBIDatasetsTool(
        {
            "name": "NCBIDatasets_get_gene_by_symbol",
            "fields": {"endpoint_type": "gene_by_symbol"},
            "parameter": {},
        }
    )


def _run(arguments):
    """Run the tool, capturing the URL actually requested."""
    tool = _tool()
    seen = {}

    def fake_get(url, **kwargs):
        seen["url"] = url
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = _MOUSE
        return resp

    with patch.object(tool, "_get", side_effect=fake_get):
        return tool.run(arguments), seen


class TestSpeciesSynonymsAreHonoured:
    @pytest.mark.parametrize("key", ["taxon", "organism", "species"])
    def test_species_reaches_the_request_url(self, key):
        """The value must be sent, not dropped in favour of the human default."""
        _, seen = _run({"symbol": "NR2F2", key: "mouse"})
        assert "/taxon/mouse/" in seen["url"]
        assert "/taxon/human/" not in seen["url"]

    @pytest.mark.parametrize("key", ["taxon", "organism", "species"])
    def test_echoed_taxon_is_what_the_caller_asked_for(self, key):
        result, _ = _run({"symbol": "NR2F2", key: "mouse"})
        assert result["metadata"]["query_taxon"] == "mouse"

    @pytest.mark.parametrize("key", ["taxon", "organism", "species"])
    def test_supplied_species_is_not_reported_as_defaulted(self, key):
        result, _ = _run({"symbol": "NR2F2", key: "mouse"})
        assert result["metadata"]["query_taxon_defaulted"] is False

    def test_taxon_wins_when_both_spellings_are_supplied(self):
        _, seen = _run({"symbol": "NR2F2", "taxon": "rat", "organism": "mouse"})
        assert "/taxon/rat/" in seen["url"]


class TestDefaultIsDisclosed:
    def test_default_is_still_human(self):
        """The documented default must not have changed."""
        _, seen = _run({"symbol": "NR2F2"})
        assert "/taxon/human/" in seen["url"]

    def test_defaulted_species_is_flagged_as_defaulted(self):
        """Otherwise 'human' is indistinguishable from a filter the caller set."""
        result, _ = _run({"symbol": "NR2F2"})
        assert result["metadata"]["query_taxon"] == "human"
        assert result["metadata"]["query_taxon_defaulted"] is True


class TestSchemaAndWrapperAgree:
    def test_json_schema_declares_the_synonyms(self):
        import json

        cfg_path = (
            Path(__file__).parent.parent.parent
            / "src/tooluniverse/data/ncbi_datasets_tools.json"
        )
        tools = json.loads(cfg_path.read_text())
        tool = next(
            t for t in tools if t["name"] == "NCBIDatasets_get_gene_by_symbol"
        )
        props = tool["parameter"]["properties"]
        assert {"taxon", "organism", "species"} <= set(props)

    def test_generated_wrapper_accepts_the_synonyms(self):
        """A parameter the schema declares but the wrapper drops is unreachable."""
        import inspect

        from tooluniverse.tools.NCBIDatasets_get_gene_by_symbol import (
            NCBIDatasets_get_gene_by_symbol,
        )

        params = inspect.signature(NCBIDatasets_get_gene_by_symbol).parameters
        assert {"taxon", "organism", "species"} <= set(params)
