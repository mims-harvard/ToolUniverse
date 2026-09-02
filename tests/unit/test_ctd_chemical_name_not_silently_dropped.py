"""Regression guard for CTD_get_chemical_diseases silently discarding every
row it just fetched.

WHY: `tu run CTD_get_chemical_diseases '{"input_terms":"chromium, hexavalent"}'`
returned `{"status":"success","data":[],"total_results":0}` for hexavalent
chromium -- a core occupational carcinogen whose CTD curation plainly exists.
The data was fetched and then thrown away:

1. `_chemical_to_diseases` builds the Elasticsearch phrase query
   `ctd.chemical_related_to_disease.chemical_name:"chromium, hexavalent"`.
   That query matches upstream -- 55 documents, confirmed live:

       curl -G https://mydisease.info/v1/query \
         --data-urlencode 'q=ctd.chemical_related_to_disease.chemical_name:"Chromium, Hexavalent"' \
         --data-urlencode 'fields=_id' --data-urlencode 'size=1'
       -> {"took":1,"total":55,"max_score":12.278343,
           "hits":[{"_id":"UMLS:C0039058",...}]}

2. The value actually stored upstream is "chromium hexavalent ion" (ES
   tokenises the caller's phrase and matches it as a sub-phrase). Confirmed
   live: UMLS:C0039058 -> chemical_name ['chromium hexavalent ion'];
   MONDO:0000387 -> ['chromium hexavalent ion', 'sodium bichromate'].

3. `_entry_matches` then post-filtered every nested entry with strict
   full-string equality, and "chromium, hexavalent" != "chromium hexavalent
   ion", so all 55 documents' rows were dropped and the tool reported a
   confident empty success -- indistinguishable to the caller from "CTD
   curates nothing for this chemical".

The fix keeps strict equality as the preferred match (so "chromium" still
means the CTD chemical `Chromium` and never silently widens) but, when the
strict filter yields zero rows against a non-empty hit set, reconstructs the
sub-phrase rule ES itself used to find which stored values were reached:
one candidate -> resolve and DISCLOSE via metadata.resolved_chemical_name /
normalization_note; several candidates -> error naming them rather than
guessing. `status: "success"` with zero rows can no longer stand unexplained.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.ctd_tool import CTDTool

pytestmark = pytest.mark.unit


def _tool():
    return CTDTool(
        {
            "name": "CTD_get_chemical_diseases",
            "fields": {"input_type": "chem", "report_type": "diseases_curated"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


def _entry(chemical_name, mesh_id, evidence="marker/mechanism", pmid="25342458"):
    return {
        "chemical_name": chemical_name,
        "mesh_chemical_id": mesh_id,
        "direct_evidence": evidence,
        "pubmed": pmid,
    }


def _hit(disease_id, label, entries):
    return {
        "_id": disease_id,
        "mondo": {"label": label},
        "ctd": {"chemical_related_to_disease": entries},
    }


def _resp(payload):
    r = MagicMock()
    r.status_code = 200
    r.raise_for_status = MagicMock()
    r.json.return_value = payload
    return r


# Shaped after the real mydisease.info response for the 55-document
# "chromium, hexavalent" phrase query (see module docstring).
_HEXAVALENT_HITS = [
    _hit(
        "UMLS:C0039058",
        None,
        [_entry("chromium hexavalent ion", "C074702")],
    ),
    _hit(
        "MONDO:0000387",
        "hypochromic microcytic anemia",
        [
            _entry("chromium hexavalent ion", "C074702"),
            _entry("sodium bichromate", "C007621"),
        ],
    ),
]


class TestSubPhraseMatchIsNotSilentlyDropped:
    def test_no_bare_empty_success_when_upstream_matched(self):
        tool = _tool()
        with patch(
            "tooluniverse.ctd_tool.requests.get",
            return_value=_resp({"hits": _HEXAVALENT_HITS}),
        ):
            result = tool.run({"input_terms": "chromium, hexavalent"})

        # The exact failure shape this guard exists to prevent.
        assert not (result["status"] == "success" and result["data"] == []), (
            "returned a confident empty success even though the upstream query "
            "matched documents"
        )

    def test_single_candidate_resolves_and_discloses(self):
        tool = _tool()
        with patch(
            "tooluniverse.ctd_tool.requests.get",
            return_value=_resp({"hits": _HEXAVALENT_HITS}),
        ):
            result = tool.run({"input_terms": "chromium, hexavalent"})

        assert result["status"] == "success"
        assert len(result["data"]) == 2
        assert {row["source_name"] for row in result["data"]} == {
            "chromium hexavalent ion"
        }
        # "sodium bichromate" shares a document but not the phrase -- it must
        # not be swept in.
        assert result["metadata"]["total_results"] == 2

        meta = result["metadata"]
        assert meta["resolved_chemical_name"] == "chromium hexavalent ion"
        note = meta["normalization_note"]
        assert "chromium, hexavalent" in note  # what the caller asked for
        assert "chromium hexavalent ion" in note  # what was actually used


class TestExactMatchUnchanged:
    def test_exact_match_returns_only_exact_rows_with_no_disclosure(self):
        """'chromium' must keep meaning `Chromium`, never widen to the ion."""
        tool = _tool()
        hits = [
            _hit(
                "MONDO:0021100",
                "breast neoplasm",
                [
                    _entry("Chromium", "D002857"),
                    _entry("chromium hexavalent ion", "C074702"),
                ],
            )
        ]
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": hits})
        ):
            result = tool.run({"input_terms": "chromium"})

        assert result["status"] == "success"
        assert [row["source_name"] for row in result["data"]] == ["Chromium"]
        assert result["metadata"]["total_results"] == 1
        # No widening happened, so nothing to disclose.
        assert "resolved_chemical_name" not in result["metadata"]
        assert "normalization_note" not in result["metadata"]
        assert "candidates" not in result["metadata"]

    def test_no_upstream_hits_still_errors(self):
        tool = _tool()
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": []})
        ):
            result = tool.run({"input_terms": "hexavalent chromium"})

        assert result["status"] == "error"
        assert "hexavalent chromium" in result["error"]


class TestMultipleCandidatesAreNotGuessed:
    def test_ambiguous_match_names_candidates_instead_of_picking_one(self):
        """Live shape for 'chromate': 19 documents under 4 different names."""
        tool = _tool()
        hits = [
            _hit("MONDO:1", "d1", [_entry("sodium chromate(VI)", "C005748")]),
            _hit("MONDO:2", "d2", [_entry("strontium chromate", "C010167")]),
            _hit("MONDO:3", "d3", [_entry("zinc chromate", "C009923")]),
        ]
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": hits})
        ):
            result = tool.run({"input_terms": "chromate"})

        assert result["status"] == "error"
        assert result["metadata"]["total_results"] == 0
        assert set(result["metadata"]["candidates"]) == {
            "sodium chromate(VI)",
            "strontium chromate",
            "zinc chromate",
        }
        for name in ("sodium chromate(VI)", "strontium chromate", "zinc chromate"):
            assert name in result["error"]
        assert "resolved_chemical_name" not in result["metadata"]


class TestIdFieldsShareTheTreatment:
    """`_entry_matches` is shared, so mesh_chemical_id / cas_registry_number
    were dropped the same way and get the same disclosure."""

    def test_mesh_id_hit_set_never_yields_bare_empty_success(self):
        tool = _tool()
        hits = [_hit("MONDO:9", "d9", [_entry("bisphenol A", "C006780 supplement")])]
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": hits})
        ):
            result = tool.run({"input_terms": "C006780"})

        assert result["metadata"]["matched_field"].endswith("mesh_chemical_id")
        assert not (result["status"] == "success" and result["data"] == [])
        assert result["metadata"]["resolved_match_value"] == "C006780 supplement"

    def test_cas_number_exact_match_unchanged(self):
        tool = _tool()
        entry = _entry("benzene", "D001554")
        entry["cas_registry_number"] = "71-43-2"
        hits = [_hit("MONDO:8", "d8", [entry])]
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": hits})
        ):
            result = tool.run({"input_terms": "71-43-2"})

        assert result["status"] == "success"
        assert result["metadata"]["matched_field"].endswith("cas_registry_number")
        assert result["metadata"]["total_results"] == 1
        assert "normalization_note" not in result["metadata"]


class TestListValuedEntryFields:
    """BioThings sometimes collapses a repeated sub-field into a list; the old
    `str(entry_value)` comparison stringified the list and never matched."""

    def test_list_valued_chemical_name_still_matches_exactly(self):
        tool = _tool()
        hits = [_hit("MONDO:7", "d7", [_entry(["Chromium"], "D002857")])]
        with patch(
            "tooluniverse.ctd_tool.requests.get", return_value=_resp({"hits": hits})
        ):
            result = tool.run({"input_terms": "chromium"})

        assert result["status"] == "success"
        assert result["metadata"]["total_results"] == 1
