"""Regression guards for Fix-R4B-2/3/4: undocumented result caps with no escape.

Three tools truncated their result list to a hard-coded page and gave the
caller no way to reach the rest -- and in two cases no way to even tell that
truncation had happened:

* RCSBAdvSearch_search_structures clamped `rows` to 50 and hard-coded the
  paginate window to start=0. A search matching 6,705 entries could only ever
  expose its first 50, and rows=200 silently returned 50.
* PDBeSIFTS_get_best_structures / _get_all_structures sliced to entries[:50]
  with no limit/offset parameter at all (P04637 has 676 entries), and
  PDBeSIFTS_get_pdb_to_uniprot cut chain mappings at 20 with no count.
* CPIC_get_alleles defaulted to limit=50 and reported only `count` -- the size
  of the returned page -- so CYP2D6 looked like it had 50 alleles when CPIC
  curates 208.
"""

from unittest.mock import MagicMock, patch

import pytest

from tooluniverse.cpic_search_pairs_tool import CPICGetAllelesTool
from tooluniverse.pdbe_sifts_tool import PDBeSIFTSTool
from tooluniverse.rcsb_advanced_search_tool import (
    MAX_ROWS_PER_PAGE,
    RCSBAdvancedSearchTool,
)

pytestmark = pytest.mark.unit


# --------------------------------------------------------------------------
# RCSB advanced search
# --------------------------------------------------------------------------


def _rcsb_tool(endpoint="advanced_search"):
    return RCSBAdvancedSearchTool(
        {"name": "RCSBAdvSearch_search_structures", "fields": {"endpoint": endpoint}}
    )


def _rcsb_response(n_hits, total):
    resp = MagicMock()
    resp.status_code = 200
    resp.content = b"{}"
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "result_set": [{"identifier": f"{i:04d}", "score": 1.0} for i in range(n_hits)],
        "total_count": total,
    }
    return resp


def _run_rcsb(arguments, n_hits=50, total=6705, endpoint="advanced_search"):
    with patch("requests.post", return_value=_rcsb_response(n_hits, total)) as post:
        result = _rcsb_tool(endpoint).run(arguments)
    return result, post.call_args.kwargs["json"]


def test_rcsb_start_reaches_beyond_the_first_page():
    _, body = _run_rcsb({"organism": "Homo sapiens", "rows": 50, "start": 50})
    assert body["request_options"]["paginate"] == {"start": 50, "rows": 50}


def test_rcsb_offset_is_accepted_as_an_alias_for_start():
    _, body = _run_rcsb({"organism": "Homo sapiens", "offset": 120})
    assert body["request_options"]["paginate"]["start"] == 120


def test_rcsb_start_defaults_to_zero():
    _, body = _run_rcsb({"organism": "Homo sapiens"})
    assert body["request_options"]["paginate"]["start"] == 0


def test_rcsb_rows_over_the_cap_is_reported_not_silently_reduced():
    result, body = _run_rcsb({"organism": "Homo sapiens", "rows": 200})
    assert body["request_options"]["paginate"]["rows"] == MAX_ROWS_PER_PAGE
    note = result["metadata"]["note"]
    assert "200" in note and str(MAX_ROWS_PER_PAGE) in note
    assert result["metadata"]["max_rows_per_page"] == MAX_ROWS_PER_PAGE


def test_rcsb_metadata_points_at_the_next_page():
    result, _ = _run_rcsb({"organism": "Homo sapiens", "rows": 50}, n_hits=50)
    assert result["metadata"]["total_count"] == 6705
    assert result["metadata"]["returned"] == 50
    assert "start=50" in result["metadata"]["note"]


def test_rcsb_no_next_page_note_when_everything_was_returned():
    result, _ = _run_rcsb({"organism": "rare"}, n_hits=3, total=3)
    assert "note" not in result["metadata"]


def test_rcsb_motif_search_pages_too():
    _, body = _run_rcsb(
        {"pattern": "C-x(2,4)-C", "rows": 200, "start": 50}, endpoint="motif_search"
    )
    assert body["request_options"]["paginate"] == {
        "start": 50,
        "rows": MAX_ROWS_PER_PAGE,
    }


# --------------------------------------------------------------------------
# PDBe SIFTS
# --------------------------------------------------------------------------


def _sifts_tool(endpoint):
    return PDBeSIFTSTool({"name": "PDBeSIFTS", "fields": {"endpoint": endpoint}})


def _sifts_entries(n):
    return [
        {
            "pdb_id": f"e{i:03d}",
            "chain_id": "A",
            "resolution": 1.0 + i,
            "experimental_method": "X-ray diffraction",
            "coverage": 0.9,
        }
        for i in range(n)
    ]


def _run_sifts(endpoint, payload, arguments):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = payload
    with patch("requests.get", return_value=resp):
        return _sifts_tool(endpoint).run(arguments)


def test_sifts_best_structures_default_page_is_unchanged():
    result = _run_sifts(
        "best_structures", {"P04637": _sifts_entries(676)}, {"uniprot_accession": "P04637"}
    )
    assert len(result["data"]["structures"]) == 50
    assert result["data"]["total_structures"] == 676
    assert result["data"]["returned_structures"] == 50


def test_sifts_best_structures_offset_returns_a_different_slice():
    payload = {"P04637": _sifts_entries(676)}
    first = _run_sifts(
        "best_structures", payload, {"uniprot_accession": "P04637", "limit": 5}
    )
    second = _run_sifts(
        "best_structures",
        payload,
        {"uniprot_accession": "P04637", "limit": 5, "offset": 50},
    )
    assert [s["pdb_id"] for s in first["data"]["structures"]] != [
        s["pdb_id"] for s in second["data"]["structures"]
    ]
    assert second["data"]["structures"][0]["pdb_id"] == "e050"
    assert second["data"]["offset"] == 50


def test_sifts_best_structures_limit_reaches_past_the_old_cap():
    result = _run_sifts(
        "best_structures",
        {"P04637": _sifts_entries(676)},
        {"uniprot_accession": "P04637", "limit": 400},
    )
    assert result["data"]["returned_structures"] == 400


def test_sifts_best_structures_notes_the_remaining_entries():
    result = _run_sifts(
        "best_structures", {"P04637": _sifts_entries(676)}, {"uniprot_accession": "P04637"}
    )
    assert "676" in result["data"]["note"]
    assert "offset=50" in result["data"]["note"]


def test_sifts_note_absent_when_the_whole_list_fits():
    result = _run_sifts(
        "best_structures", {"P01308": _sifts_entries(7)}, {"uniprot_accession": "P01308"}
    )
    assert "note" not in result["data"]
    assert result["data"]["returned_structures"] == 7


def test_sifts_all_structures_pages_as_well():
    entries = [
        {"pdb_id": f"e{i:03d}", "chain_id": "A", "resolution": 1.0 + i}
        for i in range(120)
    ]
    result = _run_sifts(
        "uniprot_to_pdb",
        {"P04637": entries},
        {"uniprot_accession": "P04637", "limit": 10, "offset": 100},
    )
    assert result["data"]["returned_pdb_entries"] == 10
    assert result["data"]["offset"] == 100
    assert result["data"]["total_pdb_entries"] == 120


def test_sifts_pdb_to_uniprot_reports_truncated_chain_mappings():
    """The 20-mapping cut was previously invisible: total_proteins counts
    proteins, not mappings."""
    mappings = [
        {
            "chain_id": chr(65 + (i % 26)),
            "start": {"residue_number": 1},
            "end": {"residue_number": 100},
            "unp_start": 1,
            "unp_end": 100,
        }
        for i in range(37)
    ]
    result = _run_sifts(
        "pdb_to_uniprot",
        {"1tup": {"UniProt": {"P04637": {"identifier": "P53_HUMAN", "mappings": mappings}}}},
        {"pdb_id": "1TUP"},
    )
    protein = result["data"]["proteins"][0]
    assert len(protein["chain_mappings"]) == 20
    assert protein["total_chain_mappings"] == 37
    assert protein["chain_mappings_truncated"] is True


def test_sifts_pdb_to_uniprot_not_flagged_when_complete():
    mappings = [
        {"chain_id": "A", "start": {}, "end": {}, "unp_start": 1, "unp_end": 10}
    ]
    result = _run_sifts(
        "pdb_to_uniprot",
        {"1abc": {"UniProt": {"P00000": {"identifier": "X", "mappings": mappings}}}},
        {"pdb_id": "1abc"},
    )
    protein = result["data"]["proteins"][0]
    assert protein["total_chain_mappings"] == 1
    assert protein["chain_mappings_truncated"] is False


# --------------------------------------------------------------------------
# CPIC alleles
# --------------------------------------------------------------------------


def _cpic_response(n_rows, content_range):
    resp = MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = [{"name": f"*{i}"} for i in range(n_rows)]
    resp.headers = {"Content-Range": content_range} if content_range else {}
    resp.url = "https://api.cpicpgx.org/v1/allele"
    return resp


def _run_cpic(arguments, n_rows=50, content_range="0-49/208"):
    with patch(
        "requests.get", return_value=_cpic_response(n_rows, content_range)
    ) as get:
        result = CPICGetAllelesTool({"name": "CPIC_get_alleles"}).run(arguments)
    return result, get.call_args


def test_cpic_reports_the_true_allele_total_not_the_page_size():
    result, _ = _run_cpic({"genesymbol": "CYP2D6"})
    assert result["count"] == 50
    assert result["total_count"] == 208
    assert "208" in result["note"]


def test_cpic_requests_an_exact_count_from_postgrest():
    _, call = _run_cpic({"genesymbol": "CYP2D6"})
    assert call.kwargs["headers"]["Prefer"] == "count=exact"


def test_cpic_offset_is_sent_upstream():
    _, call = _run_cpic({"genesymbol": "CYP2D6", "offset": 200}, n_rows=8)
    assert call.kwargs["params"]["offset"] == 200
    assert call.kwargs["params"]["limit"] == 50


def test_cpic_gene_symbol_is_uppercased_for_the_eq_filter():
    _, call = _run_cpic({"genesymbol": "cyp2d6"})
    assert call.kwargs["params"]["genesymbol"] == "eq.CYP2D6"


def test_cpic_limit_is_capped_but_far_above_the_old_default():
    _, call = _run_cpic({"genesymbol": "CYP2D6", "limit": 99999})
    assert call.kwargs["params"]["limit"] == CPICGetAllelesTool._MAX_LIMIT


def test_cpic_no_note_once_the_last_page_is_reached():
    result, _ = _run_cpic(
        {"genesymbol": "CYP2D6", "offset": 200}, n_rows=8, content_range="200-207/208"
    )
    assert result["total_count"] == 208
    assert "note" not in result


def test_cpic_falls_back_when_the_count_header_is_missing():
    result, _ = _run_cpic({"genesymbol": "TPMT"}, n_rows=12, content_range=None)
    assert result["total_count"] == 12


def test_cpic_missing_gene_is_an_error_not_an_exception():
    result = CPICGetAllelesTool({"name": "CPIC_get_alleles"}).run({})
    assert result["status"] == "error"
    assert "genesymbol" in result["error"]


# --------------------------------------------------------------------------
# Expression Atlas
# --------------------------------------------------------------------------


def test_expression_atlas_pages_beyond_the_old_fifty_cap():
    """241 experiments matched 'cancer' but only the first 50 were reachable."""
    from tooluniverse.expression_atlas_tool import ExpressionAtlasTool

    records = [{"experiment_accession": f"E-{i:04d}"} for i in range(241)]

    first, offset, note = ExpressionAtlasTool._page(records, {})
    assert len(first) == 50 and offset == 0
    assert "241" in note and "offset=50" in note

    tail, offset, note = ExpressionAtlasTool._page(records, {"limit": 10, "offset": 200})
    assert [r["experiment_accession"] for r in tail][0] == "E-0200"
    assert offset == 200

    everything, _, note = ExpressionAtlasTool._page(records, {"limit": 300})
    assert len(everything) == 241
    assert note is None, "no next-page note once the list is exhausted"


def test_expression_atlas_limit_is_capped_and_offset_floored():
    from tooluniverse.expression_atlas_tool import ExpressionAtlasTool

    records = [{"i": i} for i in range(600)]
    assert len(ExpressionAtlasTool._page(records, {"limit": 9999})[0]) == 500
    assert ExpressionAtlasTool._page(records, {"offset": -5})[1] == 0
