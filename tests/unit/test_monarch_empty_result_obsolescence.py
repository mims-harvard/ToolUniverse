"""Regression guard for Fix-R57-1: an obsolete Mondo CURIE produced an empty
success from every per-entity endpoint except the one round 56 fixed.

``Mondo_get_disease`` was taught to report ``deprecated``/``replaced_by``, but
its siblings were not, and they are the ones a caller chains to after a disease
search. Confirmed live against the host the tools call,
``api.monarchinitiative.org/v3/api``:

    Mondo_get_disease_phenotypes {"disease_id": "MONDO:0014978"} -> data [],
        total_phenotypes 0        (replacement MONDO:1010200 -> 2 phenotypes)
    MonarchV3_get_histopheno     {"entity_id": "MONDO:0002906"} -> data []
        (replacement MONDO:0019340 -> 190 phenotypes)
    MonarchV3_get_mappings       {"entity_id": "MONDO:0001111"} -> data []
        (replacement MONDO:0018896)

Reachable, not hypothetical: ``GenCC_search_gene {"gene_symbol": "PADI6"}``
returns ``disease_curie: MONDO:0014978``, and MONDO:1010200 is the term that
carries PADI6.

These endpoints return rows and nothing else, so unlike ``_mondo_get_disease``
there is no ``deprecated`` field in the response to surface -- obsolescence has
to be asked for separately. Hence a hook on the empty path rather than a
response shaper, and hence the cost: one extra ``/entity`` request (measured
259 ms) only when the result set is empty, plus the OLS4 lookup (355 ms) only
when the term really is obsolete.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.monarch_v3_tool import MonarchV3Tool

pytestmark = pytest.mark.unit


def _tool(endpoint):
    return MonarchV3Tool(
        {
            "name": f"monarch_{endpoint}",
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
}
LIVE_ENTITY = {
    "id": "MONDO:1010200",
    "name": "oocyte/zygote/embryo maturation arrest 16",
    "category": "biolink:Disease",
    "deprecated": None,
}
OLS4_REPLACEMENT = {
    "_embedded": {
        "terms": [{"term_replaced_by": "http://purl.obolibrary.org/obo/MONDO_1010200"}]
    }
}
EMPTY_ROWS = {"total": 0, "items": []}

# (endpoint, arguments, key naming the CURIE in the metadata)
EMPTY_ENDPOINTS = [
    ("mondo_phenotypes", {"disease_id": "MONDO:0014978"}),
    ("histopheno", {"entity_id": "MONDO:0014978"}),
    ("mappings", {"entity_id": "MONDO:0014978"}),
    (
        "associations",
        {
            "subject": "MONDO:0014978",
            "category": "biolink:DiseaseToPhenotypicFeatureAssociation",
        },
    ),
]


def _dispatch(entity_payload, rows=EMPTY_ROWS, calls=None):
    """Route /entity, OLS4 and the row endpoints to their own payloads."""

    def fake_get(url, **kwargs):
        if calls is not None:
            calls.append(url)
        if "ols4" in url:
            return _resp(OLS4_REPLACEMENT)
        if "/entity/" in url:
            return _resp(entity_payload)
        return _resp(rows)

    return fake_get


class TestEmptyResultDisclosesObsolescence:
    @pytest.mark.parametrize("endpoint,arguments", EMPTY_ENDPOINTS)
    def test_empty_result_says_the_curie_is_obsolete(self, endpoint, arguments):
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            side_effect=_dispatch(OBSOLETE_ENTITY),
        ):
            result = _tool(endpoint).run(arguments)

        assert result["status"] == "success"
        assert result["data"] == []
        metadata = result["metadata"]
        assert metadata["deprecated"] is True
        assert metadata["replaced_by"] == "MONDO:1010200"
        assert "MONDO:1010200" in metadata["deprecation_note"]

    @pytest.mark.parametrize("endpoint,arguments", EMPTY_ENDPOINTS)
    def test_empty_result_for_a_live_term_is_not_flagged(self, endpoint, arguments):
        """A live term with no annotations must not be called obsolete."""
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            side_effect=_dispatch(LIVE_ENTITY),
        ):
            result = _tool(endpoint).run(arguments)

        assert result["data"] == []
        assert "deprecated" not in result["metadata"]
        assert "replaced_by" not in result["metadata"]
        assert "deprecation_note" not in result["metadata"]

    def test_non_empty_result_costs_no_extra_request(self):
        """The probe must be free for the overwhelmingly common case."""
        calls = []
        rows = {"total": 1, "items": [{"object": "HP:0000789"}]}
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            side_effect=_dispatch(OBSOLETE_ENTITY, rows=rows, calls=calls),
        ):
            result = _tool("mondo_phenotypes").run({"disease_id": "MONDO:0014978"})

        assert len(result["data"]) == 1
        assert "deprecated" not in result["metadata"]
        assert not any("/entity/" in u for u in calls), calls

    def test_non_mondo_curie_is_not_probed(self):
        """`histopheno`/`mappings` take any CURIE; only MONDO is worth asking."""
        calls = []
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            side_effect=_dispatch(OBSOLETE_ENTITY, calls=calls),
        ):
            result = _tool("mappings").run({"entity_id": "HGNC:20449"})

        assert result["data"] == []
        assert "deprecated" not in result["metadata"]
        assert not any("/entity/" in u for u in calls), calls

    def test_probe_failure_leaves_the_empty_result_intact(self):
        def fake_get(url, **kwargs):
            if "/entity/" in url:
                raise OSError("monarch down")
            return _resp(EMPTY_ROWS)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = _tool("mappings").run({"entity_id": "MONDO:0014978"})

        assert result["status"] == "success"
        assert result["data"] == []
        assert "deprecated" not in result["metadata"]

    def test_obsolete_with_no_recorded_replacement_still_discloses(self):
        def fake_get(url, **kwargs):
            if "ols4" in url:
                return _resp({"_embedded": {"terms": [{"is_obsolete": True}]}})
            if "/entity/" in url:
                return _resp(OBSOLETE_ENTITY)
            return _resp(EMPTY_ROWS)

        with patch("tooluniverse.monarch_v3_tool.requests.get", side_effect=fake_get):
            result = _tool("histopheno").run({"entity_id": "MONDO:0014978"})

        assert result["metadata"]["deprecated"] is True
        assert result["metadata"]["replaced_by"] is None
        assert (
            "No replacement term is recorded"
            in (result["metadata"]["deprecation_note"])
        )

    def test_direction_hint_survives_alongside_the_obsolescence_note(self):
        """`_get_associations` already explains subject/object direction on an
        empty result; the new probe must add to that, not replace it."""
        arguments = {
            "subject": "MONDO:0014978",
            "category": "biolink:CausalGeneToDiseaseAssociation",
        }
        with patch(
            "tooluniverse.monarch_v3_tool.requests.get",
            side_effect=_dispatch(OBSOLETE_ENTITY),
        ):
            result = _tool("associations").run(arguments)

        assert "retry with object=" in result["metadata"]["note"]
        assert result["metadata"]["deprecated"] is True
