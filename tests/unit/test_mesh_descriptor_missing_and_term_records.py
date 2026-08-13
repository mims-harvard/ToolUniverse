"""Regression guard for Fix-R50 in mesh_tool.py: MeSH_get_descriptor.

Two defects, both confirmed live against https://id.nlm.nih.gov/mesh/:

1. NLM's linked-data server answers HTTP 200 with a bare `{ }` for any
   well-formed but unassigned identifier -- only malformed ones 404, and that
   path was already handled. `D999999.json` returns `{ }`, and the tool mapped
   it onto the full field layout, publishing `label: ""`, `tree_numbers: []`,
   `active: null` under `status: success`. A descriptor that does not exist was
   therefore indistinguishable from one whose label happens to be blank.

2. Descriptor records carry the name in `label`; Term and Concept records carry
   it in `prefLabel`. The tool read only `label`, so `T010724.json` -- which
   plainly returns `prefLabel: "Dysphagia"` -- was published with `label: ""`
   while simultaneously reporting `type: "Term"`. It knew the record was not a
   descriptor and still reported success with the name discarded.

Together these made an empty `label` from this tool ambiguous across three
different situations: nonexistent id, real record with a blank name, and a
Term whose name was thrown away.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.mesh_tool import MeSHTool

pytestmark = pytest.mark.unit


def _tool():
    return MeSHTool({"fields": {"endpoint": "get_descriptor"}})


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status.return_value = None
    r.json.return_value = payload
    return r


def _run(payload, descriptor_id):
    with patch("tooluniverse.mesh_tool.requests.get", return_value=_resp(payload)):
        return _tool().run({"descriptor_id": descriptor_id})


# Trimmed from the real live bodies.
_TERM_T010724 = {
    "@id": "http://id.nlm.nih.gov/mesh/T010724",
    "@type": "http://id.nlm.nih.gov/mesh/vocab#Term",
    "http://id.nlm.nih.gov/mesh/vocab#active": True,
    "identifier": "T010724",
    "prefLabel": {"@language": "en", "@value": "Dysphagia"},
}

_DESCRIPTOR_D003680 = {
    "@id": "http://id.nlm.nih.gov/mesh/D003680",
    "@type": "http://id.nlm.nih.gov/mesh/vocab#TopicalDescriptor",
    "http://id.nlm.nih.gov/mesh/vocab#active": True,
    "identifier": "D003680",
    "label": {"@language": "en", "@value": "Deglutition Disorders"},
    "treeNumber": [
        "http://id.nlm.nih.gov/mesh/C09.775.174",
        "http://id.nlm.nih.gov/mesh/C06.405.117.119",
    ],
    "dateIntroduced": "1966-01-01",
}


class TestNonexistentIdentifierIsNotASuccess:
    def test_empty_body_is_an_error_not_a_blank_record(self):
        result = _run({}, "D999999")

        assert result["status"] == "error"
        assert "data" not in result

    def test_error_names_the_identifier_and_a_way_forward(self):
        result = _run({}, "D999999")

        assert "D999999" in result["error"]
        assert "MeSH_search_descriptors" in result["error"]


class TestTermRecordsKeepTheirName:
    def test_pref_label_is_read_when_label_is_absent(self):
        """The assertion that bites: upstream supplied "Dysphagia"."""
        result = _run(_TERM_T010724, "T010724")

        assert result["data"]["label"] == "Dysphagia"

    def test_a_non_descriptor_record_says_so(self):
        result = _run(_TERM_T010724, "T010724")

        note = result["data"]["note"]
        assert "Term" in note
        assert "not a topical descriptor" in note

    def test_the_note_names_the_tool_that_resolves_the_owning_descriptor(self):
        """A type warning with no route onward is still a dead end."""
        result = _run(_TERM_T010724, "T010724")

        assert "mesh_get_subjects_by_subject_name" in result["data"]["note"]


class TestDescriptorsAreUnaffected:
    def test_real_descriptor_still_parses(self):
        result = _run(_DESCRIPTOR_D003680, "D003680")

        data = result["data"]
        assert result["status"] == "success"
        assert data["label"] == "Deglutition Disorders"
        assert data["type"] == "TopicalDescriptor"
        assert data["tree_numbers"] == ["C09.775.174", "C06.405.117.119"]

    def test_no_spurious_note_on_a_topical_descriptor(self):
        result = _run(_DESCRIPTOR_D003680, "D003680")

        assert "note" not in result["data"]
