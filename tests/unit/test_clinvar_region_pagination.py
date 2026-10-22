from unittest.mock import Mock

from tooluniverse.clinvar_tool import clinvar_variants_overlapping


def _reply(payload):
    response = Mock()
    response.json.return_value = payload
    return response


def test_region_search_exposes_candidate_and_result_continuations():
    session = Mock()
    esearch = {
        "esearchresult": {"count": "8", "idlist": ["1", "2", "3", "4"]}
    }
    summaries = {
        "result": {
            str(i): {
                "title": f"variant {i}",
                "variation_set": [
                    {"variation_loc": [{"assembly_name": "GRCh37", "chr": "7", "start": 90 - i, "stop": 110 + i}]}
                ],
            }
            for i in range(1, 5)
        }
    }
    session.get.side_effect = [_reply(esearch), _reply(summaries)]

    result = clinvar_variants_overlapping(
        session,
        "7",
        100,
        101,
        candidate_limit=4,
        candidate_offset=0,
        max_results=2,
        result_offset=0,
    )

    assert result["candidate_total"] == 8
    assert result["candidate_returned"] == 4
    assert result["candidate_has_more"] is True
    assert result["next_candidate_offset"] == 4
    assert result["matched_in_candidate_page"] == 4
    assert result["returned"] == 2
    assert result["result_has_more"] is True
    assert result["next_result_offset"] == 2
    assert session.get.call_args_list[0].kwargs["params"]["retstart"] == 0


def test_region_search_passes_candidate_offset_to_entrez():
    session = Mock()
    session.get.return_value = _reply(
        {"esearchresult": {"count": "8", "idlist": []}}
    )
    result = clinvar_variants_overlapping(
        session, "7", 100, 101, candidate_limit=4, candidate_offset=8
    )

    assert result["candidate_total"] == 8
    assert result["candidate_has_more"] is False
    assert session.get.call_args.kwargs["params"]["retstart"] == 8
