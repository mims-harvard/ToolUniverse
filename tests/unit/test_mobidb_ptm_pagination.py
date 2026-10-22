from tooluniverse.mobidb_tool import MobiDBTool


def test_mobidb_ptms_keep_name_position_pairs_and_paginate(monkeypatch) -> None:
    payload = {
        "acc": "P04637",
        "ptms": {
            "names": [f"mod-{index}" for index in range(12)],
            "positions": [[index, index] for index in range(12)],
        },
    }
    tool = MobiDBTool({"fields": {"endpoint": "get_protein"}})
    monkeypatch.setattr(tool, "_fetch_protein_json", lambda accession: payload)

    first = tool.run({"accession": "P04637", "ptm_limit": 3})
    last = tool.run({"accession": "P04637", "ptm_offset": 10, "ptm_limit": 3})

    first_summary = first["data"]["ptm_summary"]
    assert first_summary["count"] == 12
    assert first_summary["returned"] == 3
    assert first_summary["truncated"] is True
    assert first_summary["next_offset"] == 3
    assert first_summary["entries"] == [
        {"type": "mod-0", "position": [0, 0]},
        {"type": "mod-1", "position": [1, 1]},
        {"type": "mod-2", "position": [2, 2]},
    ]
    assert first_summary["types"] == ["mod-0", "mod-1", "mod-2"]
    assert first_summary["positions"] == [[0, 0], [1, 1], [2, 2]]

    last_summary = last["data"]["ptm_summary"]
    assert last_summary["entries"] == [
        {"type": "mod-10", "position": [10, 10]},
        {"type": "mod-11", "position": [11, 11]},
    ]
    assert last_summary["returned"] == 2
    assert last_summary["truncated"] is False
    assert last_summary["next_offset"] is None

