"""Complex Portal species filter (round 82).

Complex Portal's `species_f` search facet is indexed by full organism name
strings (e.g. "Homo sapiens"), not NCBI taxonomy IDs -- confirmed live
against the API's own `facets` response. The tool's documented default
("9606") never matched anything, silently no-opping the species filter for
every caller. These tests cover the taxid/alias -> facet-name resolution
and the properly-quoted filter string, with mocks (no live calls).
"""

import unittest
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.unit


def _make_tool():
    from tooluniverse.complex_portal_tool import ComplexPortalTool

    return ComplexPortalTool(
        {
            "name": "ComplexPortal_search_complexes",
            "type": "ComplexPortalTool",
            "fields": {"operation": "search_complexes"},
        }
    )


def _resp(json_body):
    r = MagicMock()
    r.json.return_value = json_body
    r.raise_for_status.return_value = None
    return r


class TestResolveSpeciesFacetName(unittest.TestCase):
    def test_common_taxid_resolves_to_facet_name(self):
        from tooluniverse.complex_portal_tool import _resolve_species_facet_name

        self.assertEqual(_resolve_species_facet_name("9606"), "Homo sapiens")
        self.assertEqual(_resolve_species_facet_name("10090"), "Mus musculus")
        self.assertEqual(_resolve_species_facet_name("10116"), "Rattus norvegicus")

    def test_common_name_alias_resolves_to_facet_name(self):
        from tooluniverse.complex_portal_tool import _resolve_species_facet_name

        self.assertEqual(_resolve_species_facet_name("human"), "Homo sapiens")
        self.assertEqual(_resolve_species_facet_name("Human"), "Homo sapiens")
        self.assertEqual(
            _resolve_species_facet_name("yeast"),
            "Saccharomyces cerevisiae (strain ATCC 204508 / S288c)",
        )

    def test_unmapped_value_passes_through_unchanged(self):
        from tooluniverse.complex_portal_tool import _resolve_species_facet_name

        self.assertEqual(
            _resolve_species_facet_name("Mus musculus"), "Mus musculus"
        )
        self.assertEqual(_resolve_species_facet_name("Some Rare Organism"), "Some Rare Organism")


class TestSearchComplexesSpeciesFilter(unittest.TestCase):
    def test_default_species_filters_by_homo_sapiens_quoted(self):
        tool = _make_tool()
        with patch("tooluniverse.complex_portal_tool.requests.get") as get:
            get.return_value = _resp({"elements": [], "totalNumberOfResults": 0})
            result = tool.run({"query": "proteasome"})

        filters = get.call_args.kwargs["params"]["filters"]
        self.assertEqual(filters, 'species_f:("Homo sapiens")')
        self.assertEqual(result["data"]["species_filter"], "Homo sapiens")

    def test_taxid_9606_resolves_and_quotes(self):
        tool = _make_tool()
        with patch("tooluniverse.complex_portal_tool.requests.get") as get:
            get.return_value = _resp({"elements": [], "totalNumberOfResults": 0})
            tool.run({"query": "proteasome", "species": "9606"})

        filters = get.call_args.kwargs["params"]["filters"]
        self.assertEqual(filters, 'species_f:("Homo sapiens")')

    def test_mouse_taxid_resolves_and_quotes(self):
        tool = _make_tool()
        with patch("tooluniverse.complex_portal_tool.requests.get") as get:
            get.return_value = _resp({"elements": [], "totalNumberOfResults": 0})
            tool.run({"query": "kinase", "species": "10090"})

        filters = get.call_args.kwargs["params"]["filters"]
        self.assertEqual(filters, 'species_f:("Mus musculus")')

    def test_empty_species_disables_filter(self):
        tool = _make_tool()
        with patch("tooluniverse.complex_portal_tool.requests.get") as get:
            get.return_value = _resp({"elements": [], "totalNumberOfResults": 0})
            tool.run({"query": "TP53", "species": ""})

        params = get.call_args.kwargs["params"]
        self.assertNotIn("filters", params)

    def test_unmapped_species_name_is_quoted_verbatim(self):
        tool = _make_tool()
        with patch("tooluniverse.complex_portal_tool.requests.get") as get:
            get.return_value = _resp({"elements": [], "totalNumberOfResults": 0})
            tool.run({"query": "TP53", "species": "Gallus gallus"})

        filters = get.call_args.kwargs["params"]["filters"]
        self.assertEqual(filters, 'species_f:("Gallus gallus")')


if __name__ == "__main__":
    unittest.main()
