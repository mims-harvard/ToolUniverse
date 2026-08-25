"""Regression guard for chebi_tool.py: ChEBI_get_compound silently answered
about a *different* compound than the one requested, with status "success"
and nothing marking the substitution.

ChEBI merges obsolete/duplicate accessions into one primary entry and then
serves that primary entry for every accession merged into it. Verified live
against the exact URL the tool builds
(``{CHEBI_BASE_URL}/compound/{chebi_id}/``)::

    curl https://www.ebi.ac.uk/chebi/backend/api/public/compound/1/
    -> id                = 18357
       chebi_accession   = 'CHEBI:18357'
       ascii_name        = '(R)-noradrenaline'
       secondary_ids     = ['CHEBI:1', 'CHEBI:14668', 'CHEBI:25592',
                            'CHEBI:43725', 'CHEBI:258884']

So ``{"chebi_id": 1}`` returned a full, confident record for
(R)-noradrenaline. Cross-checked independently against EBI OLS4, where
``CHEBI_1`` carries ``"is_obsolete": true`` and
``"term_replaced_by": "CHEBI_18357"`` -- i.e. the substitution is real and
upstream-correct; what was wrong was ToolUniverse presenting the substituted
entity as if it were the requested one. A researcher pasting a legacy
accession out of an old paper or dataset got the wrong molecule, labelled
success.

The evidence needed to disclose it was already in the fetched payload
(``secondary_ids``) and was simply dropped. The same silent-substitution
shape exists on ``/ontology/children/`` and ``/ontology/parents/``, which
redirect identically but do NOT return ``secondary_ids`` -- covered below.

All HTTP is mocked; these tests never touch the network.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.chebi_tool import ChEBITool, _redirect_disclosure

pytestmark = pytest.mark.unit


# Trimmed shape of the real GET /compound/1/ response (see docstring).
_MERGED_COMPOUND = {
    "id": 18357,
    "chebi_accession": "CHEBI:18357",
    "name": "(R)-noradrenaline",
    "ascii_name": "(R)-noradrenaline",
    "definition": "The R-enantiomer of noradrenaline.",
    "stars": 3,
    "secondary_ids": [
        "CHEBI:1",
        "CHEBI:14668",
        "CHEBI:25592",
        "CHEBI:43725",
        "CHEBI:258884",
    ],
    "chemical_data": {"formula": "C8H11NO3", "mass": "169.18", "charge": 0},
    "default_structure": {
        "smiles": "NC[C@H](O)c1ccc(O)c(O)c1",
        "standard_inchi_key": "SFLSHLFXELFNJZ-QMMMGPOBSA-N",
    },
    "names": {"SYNONYM": [{"name": "norepinephrine"}]},
}

# Trimmed shape of the real GET /compound/15377/ response: a direct hit.
_PRIMARY_COMPOUND = {
    "id": 15377,
    "chebi_accession": "CHEBI:15377",
    "name": "water",
    "ascii_name": "water",
    "definition": "An oxygen hydride consisting of an oxygen atom.",
    "stars": 3,
    "secondary_ids": ["CHEBI:5585", "CHEBI:13352", "CHEBI:42043"],
    "chemical_data": {"formula": "H2O", "mass": "18.01530", "charge": 0},
    "default_structure": {
        "smiles": "[H]O[H]",
        "standard_inchi_key": "XLYOFNOQVPJJNP-UHFFFAOYSA-N",
    },
    "names": {"SYNONYM": [{"name": "dihydrogen oxide"}]},
}

# GET /ontology/parents/1/ -- redirects the same way but carries no
# secondary_ids field at all, so the relationship cannot be asserted.
_MERGED_ONTOLOGY = {
    "id": 18357,
    "chebi_accession": "CHEBI:18357",
    "ontology_relations": {
        "outgoing_relations": [
            {"relation_type": "is a", "final_id": 33569, "final_name": "noradrenaline"}
        ],
        "incoming_relations": [
            {
                "init_id": 72587,
                "init_name": "(R)-noradrenaline(1+)",
                "relation_type": "is conjugate acid of",
                "final_id": 18357,
                "final_name": "(R)-noradrenaline",
            }
        ],
    },
}

_DISCLOSURE_KEYS = {
    "requested_chebi_id",
    "requested_chebi_accession",
    "redirect_note",
    "secondary_ids",
}


def _tool(endpoint_type):
    return ChEBITool(
        {
            "name": f"ChEBI_{endpoint_type}",
            "fields": {"endpoint_type": endpoint_type},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


def _run(endpoint_type, payload, arguments):
    with patch(
        "tooluniverse.chebi_tool.requests.get", return_value=_resp(payload)
    ) as get:
        result = _tool(endpoint_type).run(arguments)
    return result, get


class TestSecondaryIdRedirectIsDisclosed:
    def test_requesting_merged_id_names_both_accessions(self):
        result, _ = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": 1})

        assert result["status"] == "success"
        data = result["data"]

        # The returned entry is still the primary one ChEBI served...
        assert data["chebi_id"] == 18357
        assert data["chebi_accession"] == "CHEBI:18357"
        assert data["name"] == "(R)-noradrenaline"

        # ...but the substitution is now on the record, naming BOTH accessions.
        assert data["requested_chebi_id"] == 1
        assert data["requested_chebi_accession"] == "CHEBI:1"
        note = data["redirect_note"]
        assert "CHEBI:1" in note
        assert "CHEBI:18357" in note
        assert "secondary" in note.lower()

    def test_secondary_ids_provenance_is_surfaced_on_redirect(self):
        result, _ = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": 1})
        # The evidence for the claim travels with the claim.
        assert result["data"]["secondary_ids"] == _MERGED_COMPOUND["secondary_ids"]

    def test_url_still_uses_the_requested_id(self):
        _, get = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": 1})
        assert get.call_args[0][0].endswith("/compound/1/")


class TestDirectHitIsUnchanged:
    def test_no_disclosure_keys_on_direct_hit(self):
        result, _ = _run("get_compound", _PRIMARY_COMPOUND, {"chebi_id": 15377})

        data = result["data"]
        assert data["chebi_id"] == 15377
        assert data["name"] == "water"
        # Byte-identical to the pre-fix payload: not one extra key, including
        # secondary_ids, which is provenance only for a substitution.
        assert _DISCLOSURE_KEYS & set(data) == set()

    def test_direct_hit_key_order_is_unchanged(self):
        result, _ = _run("get_compound", _PRIMARY_COMPOUND, {"chebi_id": 15377})
        assert list(result["data"]) == [
            "chebi_id",
            "chebi_accession",
            "name",
            "definition",
            "stars",
            "formula",
            "mass",
            "monoisotopic_mass",
            "charge",
            "smiles",
            "inchikey",
            "synonyms",
        ]

    def test_curie_form_of_a_primary_id_adds_nothing(self):
        result, _ = _run("get_compound", _PRIMARY_COMPOUND, {"chebi_id": "CHEBI:15377"})
        assert _DISCLOSURE_KEYS & set(result["data"]) == set()


class TestCurieInputFormMatchesBareInteger:
    def test_curie_string_discloses_the_same_redirect(self):
        bare, _ = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": 1})
        curie, get = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": "CHEBI:1"})

        assert curie["data"] == bare["data"]
        assert curie["data"]["requested_chebi_id"] == 1
        assert get.call_args[0][0].endswith("/compound/1/")

    def test_lowercase_and_padded_curie_behave_identically(self):
        bare, _ = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": 1})
        for form in ("chebi:1", " CHEBI: 1 ", "1"):
            result, _ = _run("get_compound", _MERGED_COMPOUND, {"chebi_id": form})
            assert result["data"] == bare["data"], form


class TestOntologyEndpointsShareTheFix:
    """/ontology/parents/1/ and /ontology/children/1/ redirect to 18357 too,
    but their payloads have no secondary_ids -- the note must say only what
    the response proves."""

    @pytest.mark.parametrize("endpoint_type", ["ontology_parents", "ontology_children"])
    def test_redirect_disclosed_without_asserting_unproven_relationship(
        self, endpoint_type
    ):
        result, _ = _run(endpoint_type, _MERGED_ONTOLOGY, {"chebi_id": "CHEBI:1"})

        data = result["data"]
        assert data["chebi_id"] == 18357
        assert data["requested_chebi_id"] == 1
        assert data["requested_chebi_accession"] == "CHEBI:1"
        assert "CHEBI:18357" in data["redirect_note"]
        # No secondary_ids in the payload => none invented in the output.
        assert "secondary_ids" not in data

    @pytest.mark.parametrize("endpoint_type", ["ontology_parents", "ontology_children"])
    def test_ontology_direct_hit_unchanged(self, endpoint_type):
        payload = dict(_MERGED_ONTOLOGY)
        result, _ = _run(endpoint_type, payload, {"chebi_id": 18357})
        assert _DISCLOSURE_KEYS & set(result["data"]) == set()


class TestDisclosureHelperEdgeCases:
    def test_requested_id_absent_from_secondary_ids_is_flagged_differently(self):
        payload = dict(_MERGED_COMPOUND, secondary_ids=["CHEBI:14668"])
        disclosure = _redirect_disclosure(1, payload)
        # Surprising case: a substitution we cannot explain must not be
        # papered over with the reassuring "merged accession" wording.
        assert "NOT listed" in disclosure["redirect_note"]
        assert "secondary" in disclosure["redirect_note"].lower()

    def test_no_disclosure_when_id_unparseable(self):
        assert _redirect_disclosure(1, {"id": None}) == {}
        assert _redirect_disclosure("not-an-id", _MERGED_COMPOUND) == {}
        assert _redirect_disclosure(1, "not-a-dict") == {}
