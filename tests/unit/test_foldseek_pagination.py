from tooluniverse.foldseek_tool import FoldseekTool


def _tool():
    return FoldseekTool({"fields": {"operation": "search"}})


def _payload():
    return {
        "results": [
            {
                "db": "pdb100",
                "alignments": [
                    [
                        {"target": "weak", "eval": 0.2},
                        {"target": "exact-zero", "eval": 0.0},
                        {"target": "strong", "eval": 1e-20},
                        {"target": "missing", "eval": None},
                        {"target": "middle", "eval": 1e-5},
                    ]
                ],
            }
        ]
    }


def test_parse_results_returns_recoverable_later_page_and_ticket():
    result = _tool()._parse_results(
        _payload(), "4HHB", "pdb100", max_results=2, offset=2, ticket_id="abc"
    )

    data = result["data"]
    assert [row["target"] for row in data["alignments"]] == ["middle", "weak"]
    assert data["ticket_id"] == "abc"
    assert data["total_hits"] == 5
    assert data["has_more"] is True
    assert data["next_offset"] == 4


def test_parse_results_tail_terminates_and_zero_evalue_sorts_first():
    first = _tool()._parse_results(_payload(), "4HHB", "pdb100", 1)
    tail = _tool()._parse_results(_payload(), "4HHB", "pdb100", 2, offset=4)

    assert first["data"]["alignments"][0]["target"] == "exact-zero"
    assert [row["target"] for row in tail["data"]["alignments"]] == ["missing"]
    assert tail["data"]["has_more"] is False
    assert tail["data"]["next_offset"] is None


def test_search_validates_page_controls_before_network():
    assert "1 to 50" in _tool().run({"pdb_id": "4HHB", "max_results": 51})[
        "error"
    ]
    assert "non-negative" in _tool().run({"pdb_id": "4HHB", "offset": -1})[
        "error"
    ]
