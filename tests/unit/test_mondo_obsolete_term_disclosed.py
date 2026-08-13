"""Regression guard for Fix-R56-2: an obsolete Mondo term returned a
successful, fully empty record with no way to tell it was obsolete.

``Mondo_get_disease {"disease_id": "MONDO:0014978"}`` returned
``status: success`` with ``description: null, synonyms: null, xrefs:
null, mappings: [], parent_diseases: [], causal_genes: [],
association_counts: {}`` -- indistinguishable from a live disease with no
annotations yet. The only signal was the word "obsolete" inside the name
string. This is a reachable dead end, not a hypothetical: GenCC hands
back ``disease_curie: MONDO:0014978`` for PADI6, which feeds straight
into this tool.

Root cause is that the Monarch payload already answers the question and
the tool discarded it. Confirmed live against
``api-v3.monarchinitiative.org/v3/api/entity/MONDO:0014978``:
``deprecated: True``; the live replacement MONDO:1010200 returns
``deprecated: None``. The same field is present, and was equally
discarded, on the /search items.

The replacement pointer is not in Monarch's payload; EBI OLS4 records it
as ``term_replaced_by: MONDO_1010200`` for this term. Disclosing an
obsolete identifier rather than answering as if it were live follows
``chebi_tool.py`` and ``hpo_tool.py``, though neither resolves a
replacement -- both detect a silent upstream redirect by comparing the
requested ID against the one in the returned record.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.monarch_v3_tool import MonarchV3Tool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return MonarchV3Tool(
        {
            "name": f"mondo_{endpoint}",
            "type": "MonarchV3Tool",
            "fields": {"endpoint": endpoint},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.json.return_value = payload
    r.raise_for_status.return_value = None
    return r


OBSOLETE_ENTITY = {
    "id": "MONDO:0014978",
    "name": "obsolete preimplantation embryonic lethality 2",
    "category": "biolink:Disease",
    "deprecated": True,
    "description": None,
    "synonym": None,
    "xref": None,
    "mappings": [],
    "association_counts": [],
    "causal_gene": [],
    "has_descendant": [],
    "node_hierarchy": {"super_classes": [], "sub_classes": []},
}

LIVE_ENTITY = {
    "id": "MONDO:1010200",
    "name": "oocyte/zygote/embryo maturation arrest 16",
    "category": "biolink:Disease",
    "deprecated": None,
    "description": "Any inherited oocyte maturation defect...",
    "synonym": [],
    "xref": ["OMIM:617234"],
    "mappings": [],
    "association_counts": [],
    "causal_gene": [{"id": "HGNC:20449", "name": "PADI6"}],
    "has_descendant": [],
    "node_hierarchy": {"super_classes": [], "sub_classes": []},
}

OLS4_REPLACEMENT = {
    "_embedded": {
        "terms": [
            {
                "label": "obsolete preimplantation embryonic lethality 2",
                "is_obsolete": True,
                "term_replaced_by": "http://purl.obolibrary.org/obo/MONDO_1010200",
            }
        ]
    }
}


class TestObsoleteDisclosure:
    def test_obsolete_term_is_flagged_and_points_at_its_replacement(self):
        tool = _tool("mondo_disease")

        def fake_get(url, **kwargs):
            if "ols4" in url:
                return _resp(OLS4_REPLACEMENT)
            return _resp(OBSOLETE_ENTITY)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = tool.run({"disease_id": "MONDO:0014978"})

        assert result["status"] == "success"
        assert result["data"]["deprecated"] is True
        assert result["data"]["replaced_by"] == "MONDO:1010200"
        note = result["metadata"]["deprecation_note"]
        assert "obsolete" in note
        assert "MONDO:1010200" in note

    def test_live_term_is_not_flagged_and_costs_no_extra_request(self):
        """Monarch reports live terms as deprecated: None, not False."""
        tool = _tool("mondo_disease")
        calls = []

        def fake_get(url, **kwargs):
            calls.append(url)
            return _resp(LIVE_ENTITY)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = tool.run({"disease_id": "MONDO:1010200"})

        assert result["data"]["deprecated"] is False
        assert "replaced_by" not in result["data"]
        assert "deprecation_note" not in result["metadata"]
        assert not any("ols4" in u for u in calls), (
            f"OLS4 consulted for a live term: {calls}"
        )

    def test_obsolete_term_still_discloses_when_no_replacement_is_recorded(self):
        tool = _tool("mondo_disease")

        def fake_get(url, **kwargs):
            if "ols4" in url:
                return _resp({"_embedded": {"terms": [{"is_obsolete": True}]}})
            return _resp(OBSOLETE_ENTITY)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = tool.run({"disease_id": "MONDO:0014978"})

        assert result["data"]["deprecated"] is True
        assert result["data"]["replaced_by"] is None
        assert (
            "No replacement term is recorded" in result["metadata"]["deprecation_note"]
        )

    def test_ols4_failure_does_not_lose_the_obsolescence_flag(self):
        tool = _tool("mondo_disease")

        def fake_get(url, **kwargs):
            if "ols4" in url:
                raise OSError("network down")
            return _resp(OBSOLETE_ENTITY)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = tool.run({"disease_id": "MONDO:0014978"})

        assert result["data"]["deprecated"] is True
        assert result["data"]["replaced_by"] is None

    def test_search_rows_say_which_hits_are_obsolete(self):
        """A search listing an obsolete term beside its replacement, with
        nothing to tell them apart, sends the caller to the dead one."""
        tool = _tool("mondo_search")
        payload = {
            "total": 2,
            "items": [
                {
                    "id": "MONDO:1010200",
                    "name": "oocyte/zygote/embryo maturation arrest 16",
                },
                {
                    "id": "MONDO:0014978",
                    "name": "obsolete preimplantation embryonic lethality 2",
                    "deprecated": True,
                },
            ],
        }
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get", return_value=_resp(payload)
        ):
            result = tool.run({"query": "preimplantation embryonic lethality 2"})

        assert [row["deprecated"] for row in result["data"]] == [False, True]

    def test_generic_entity_lookup_also_says_so(self):
        tool = _tool("entity")
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            return_value=_resp(OBSOLETE_ENTITY),
        ):
            result = tool.run({"id": "MONDO:0014978"})

        assert result["data"]["deprecated"] is True
