from unittest.mock import MagicMock, patch

from tooluniverse.sra_tool import SRATool


def test_search_forwards_retstart_and_exposes_next_start():
    search = MagicMock()
    search.json.return_value = {"esearchresult": {"count": "100", "idlist": ["4", "5"]}}
    summary = MagicMock()
    summary.json.return_value = {"result": {"uids": ["4", "5"], "4": {}, "5": {}}}
    tool = SRATool(
        {"name": "SRA_search_experiments", "fields": {"operation": "search"}}
    )

    with (
        patch.object(tool, "_get_with_retry", side_effect=[search, summary]) as get,
        patch("tooluniverse.sra_tool.time.sleep"),
    ):
        result = tool.run({"query": "BRCA1", "limit": 2, "start": 2})

    assert get.call_args_list[0].args[1]["retstart"] == 2
    assert result["data"]["total"] == 100
    assert result["data"]["next_start"] == 4


def test_summary_parser_keeps_more_than_ten_runs():
    runs = "".join(
        f'<Run acc="SRR{i}" total_spots="1" total_bases="2" is_public="true" />'
        for i in range(12)
    )
    exp = '<Summary><Statistics total_runs="12" /></Summary>'

    result = SRATool._parse_sra_summary(None, {"expxml": exp, "runs": runs}, "1")

    assert len(result["runs"]) == 12
    assert result["runs_returned"] == 12
    assert result["runs_complete"] is True
