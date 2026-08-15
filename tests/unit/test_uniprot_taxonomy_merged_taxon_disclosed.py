"""Regression tests: a merged UniProt taxon must not be answered silently.

``UniProtTaxonomy_get_taxon`` fetched ``rest.uniprot.org/taxonomy/{id}`` and
read ``taxonId`` straight out of the body. UniProt answers a *merged* (retired)
taxon with an HTTP 303 to the node it was merged into, so ``requests`` followed
the redirect and the tool returned a different taxon than the caller asked for,
with the requested id appearing nowhere in the response.

Confirmed live: NCBI taxon 46170 is *Staphylococcus aureus* subsp. *aureus*,
the subspecies node most older BioSample/BioProject MRSA records are filed
under. ``{"taxon_id": "46170"}`` returned ``taxon_id: 1280`` /
*Staphylococcus aureus* -- the species node, with a larger protein-count
denominator -- and no indication a substitution had happened. UniProt itself
publishes the merge two ways::

    $ curl -sD- -o/dev/null https://rest.uniprot.org/taxonomy/46170
    HTTP/2 303
    location: /taxonomy/1280?from=46170

    $ curl -s --max-redirs 0 https://rest.uniprot.org/taxonomy/46170
    {"taxonId":46170,"inactiveReason":{"inactiveReasonType":"MERGED","mergedTo":1280}}

This mirrors the obsolete-identifier disclosure already shipped for Mondo,
Monarch and HPO: answer with the current record, but say so.
"""

import pytest

from tooluniverse.uniprot_taxonomy_tool import UniProtTaxonomyTool

pytestmark = pytest.mark.unit

CONFIG = {
    "type": "UniProtTaxonomyTool",
    "name": "UniProtTaxonomy_get_taxon",
    "description": "Get taxonomy details",
    "parameter": {"type": "object", "properties": {}},
    "fields": {"endpoint": "get_taxon"},
}


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload

    def raise_for_status(self):
        return None


def _tool():
    return UniProtTaxonomyTool(dict(CONFIG))


def _body(taxon_id, name, **extra):
    body = {
        "taxonId": taxon_id,
        "scientificName": name,
        "mnemonic": "STAAU",
        "rank": "species",
        "lineage": [{"taxonId": 2, "scientificName": "Bacteria", "rank": "domain"}],
        "statistics": {"reviewedProteinCount": 10262, "unreviewedProteinCount": 8368},
    }
    body.update(extra)
    return body


def _run(monkeypatch, arguments, payload):
    monkeypatch.setattr(
        "tooluniverse.uniprot_taxonomy_tool.requests.get",
        lambda *a, **k: _FakeResponse(payload),
    )
    return _tool().run(arguments)


# ---------------------------------------------------------------------------
# The merged case
# ---------------------------------------------------------------------------


def test_merged_taxon_is_disclosed(monkeypatch):
    result = _run(
        monkeypatch,
        {"taxon_id": "46170"},
        _body(1280, "Staphylococcus aureus"),
    )
    data = result["data"]
    assert result["status"] == "success"
    assert data["taxon_id"] == 1280, "the current record is still what is returned"
    assert data["merged_from"] == 46170, "the requested id must survive in the response"
    note = result["metadata"]["note"]
    assert "46170" in note and "1280" in note
    assert "merged" in note.lower()


def test_requested_id_is_always_echoed(monkeypatch):
    """Even on the happy path the caller can join request to response."""
    result = _run(monkeypatch, {"taxon_id": 1280}, _body(1280, "Staphylococcus aureus"))
    assert result["data"]["query_taxon_id"] == 1280


def test_active_taxon_gets_no_merge_note(monkeypatch):
    result = _run(monkeypatch, {"taxon_id": "9606"}, _body(9606, "Homo sapiens"))
    assert "merged_from" not in result["data"]
    assert "note" not in result["metadata"]


def test_integer_and_string_taxon_ids_compare_equal(monkeypatch):
    """'9606' and 9606 are the same taxon -- never report that as a merge."""
    for taxon_id in ("9606", 9606, " 9606 "):
        result = _run(monkeypatch, {"taxon_id": taxon_id}, _body(9606, "Homo sapiens"))
        assert "merged_from" not in result["data"], f"false merge for {taxon_id!r}"


def test_non_numeric_taxon_id_does_not_crash(monkeypatch):
    """A junk id must not raise; it simply cannot be compared."""
    result = _run(monkeypatch, {"taxon_id": "not-a-taxon"}, _body(1280, "S. aureus"))
    assert result["status"] == "success"
    assert result["data"]["query_taxon_id"] == "not-a-taxon"


def test_inactive_reason_is_surfaced_when_upstream_sends_it(monkeypatch):
    """If UniProt returns the inactive stub itself, say why rather than 404."""
    result = _run(
        monkeypatch,
        {"taxon_id": "46170"},
        _body(
            1280,
            "Staphylococcus aureus",
            inactiveReason={"inactiveReasonType": "MERGED", "mergedTo": 1280},
        ),
    )
    assert result["data"]["merged_from"] == 46170
    assert "merged" in result["metadata"]["note"].lower()


# ---------------------------------------------------------------------------
# Nothing else about the payload moves
# ---------------------------------------------------------------------------


def test_existing_fields_are_untouched(monkeypatch):
    result = _run(monkeypatch, {"taxon_id": "46170"}, _body(1280, "Staphylococcus aureus"))
    data = result["data"]
    assert data["scientific_name"] == "Staphylococcus aureus"
    assert data["mnemonic"] == "STAAU"
    assert data["rank"] == "species"
    assert data["statistics"] == {
        "reviewed_protein_count": 10262,
        "unreviewed_protein_count": 8368,
    }
    assert data["lineage"] == [
        {
            "taxon_id": 2,
            "scientific_name": "Bacteria",
            "rank": "domain",
            "hidden": False,
        }
    ]
    assert result["metadata"]["source"] == "UniProt Taxonomy (rest.uniprot.org)"


def test_missing_taxon_id_still_errors():
    assert _tool().run({})["status"] == "error"
