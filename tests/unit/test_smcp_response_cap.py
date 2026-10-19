"""The 100 KB response cap is a cap, and what it returns is still JSON.

`_truncate_response` exists so a tool's answer cannot overflow an LLM's
context, and the MCP tools it guards declare a JSON return. It did neither on
four of the seven shapes measured:

* a list whose FIRST item is oversized came back in full under a
  `"_truncated": true` label -- 5,000,126 chars against a 100,000 cap, fifty
  times the limit the function exists to impose, because the binary search
  starts at `lo = 1` and never tested it;
* every shape with no list to trim fell through to `serialized[:max_chars] +
  suffix`, which cuts a JSON document at an arbitrary character and appends
  to it, so the answer was 100,039 chars AND unparseable -- a caller holding
  the tool to its declared return got nothing at all out of a response that
  had been truncated precisely so it could get something.

The tests that existed covered only the two shapes that already worked, and
asserted neither property. So these assert the two properties over every shape
rather than adding a case per bug, because the next shape is the one nobody
listed.
"""

import json

import pytest

from tooluniverse.smcp import MAX_RESPONSE_CHARS, _truncate_response

# Every shape a tool has been seen to return, oversized. The point is the
# sweep: a cap asserted on one shape is a cap asserted on nothing.
SHAPES = {
    "list_of_many_small_items": [{"i": i, "pad": "x" * 200} for i in range(2000)],
    "list_of_one_oversized_item": [{"blob": "x" * 5_000_000}],
    "list_of_two_oversized_items": [
        {"blob": "x" * 5_000_000},
        {"blob": "y" * 5_000_000},
    ],
    "dict_whose_bulk_is_one_string": {"text": "x" * 5_000_000},
    "dict_with_a_big_list": {"rows": [{"pad": "x" * 200} for _ in range(2000)]},
    "dict_with_a_huge_sibling_string": {
        "text": "x" * 5_000_000,
        "rows": [{"p": "x" * 200} for _ in range(2000)],
    },
    "a_bare_huge_string": "x" * 5_000_000,
    # ensure_ascii=False keeps the characters, but escaping still changes how
    # many of them fit, so the budget cannot be a subtraction.
    "cjk_in_one_string": {"text": "测" * 2_000_000},
    "quotes_and_backslashes": {"text": '"\\' * 2_000_000},
}


def _truncated(shape, max_chars=MAX_RESPONSE_CHARS):
    serialized = json.dumps(shape, ensure_ascii=False)
    assert len(serialized) > max_chars, "the fixture must actually be oversized"
    return _truncate_response(
        shape, serialized, max_chars, persist_full_result=False
    ), serialized


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_the_cap_is_a_cap(name):
    out, _ = _truncated(SHAPES[name])
    assert len(out) <= MAX_RESPONSE_CHARS, (
        f"{name}: {len(out):,} chars returned against a {MAX_RESPONSE_CHARS:,} cap"
    )


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_what_comes_back_is_still_json(name):
    out, _ = _truncated(SHAPES[name])
    parsed = json.loads(out)  # the assertion is that this does not raise
    assert parsed["_truncated"] is True, "and it says it was truncated"


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_something_of_the_answer_survives(name):
    """Truncating to metadata alone would satisfy both properties above and
    be useless, so the head of the response has to come back with it."""
    out, serialized = _truncated(SHAPES[name])
    parsed = json.loads(out)
    kept = parsed.get("_preview")
    if kept is None:  # the list/dict paths keep items instead of a preview
        # the list path reports `_showing`, the dict path `_<key>_showing`
        shown = [v for k, v in parsed.items() if k.endswith("_showing")]
        assert shown and min(shown) >= 1
        return
    assert kept and serialized.startswith(kept)
    # and it fills the budget rather than cutting conservatively short
    assert len(out) > MAX_RESPONSE_CHARS * 0.9


def test_a_shape_that_can_be_trimmed_is_trimmed_rather_than_previewed():
    """The preview is the fallback, not the first answer: where whole items
    fit, the caller gets whole items."""
    out, _ = _truncated(SHAPES["list_of_many_small_items"])
    parsed = json.loads(out)
    assert parsed["_showing"] >= 1 and parsed["_total"] == 2000
    assert len(parsed["data"]) == parsed["_showing"]
    assert "_preview" not in parsed


def test_both_call_sites_read_the_one_constant():
    """It was a bare `100_000` written twice. One number governing one
    contract drifts the moment the two copies disagree, and nothing would
    notice."""
    from pathlib import Path

    src = (Path(__file__).resolve().parents[2] / "src/tooluniverse/smcp.py").read_text()
    assert src.count("max_chars = MAX_RESPONSE_CHARS") == 2
    assert src.count("max_chars = 100_000") == 0


def test_the_full_result_file_still_holds_everything():
    """Truncation is only acceptable because nothing is lost; that is what
    `persist_full_result` is for."""
    import os

    shape = SHAPES["list_of_many_small_items"]
    serialized = json.dumps(shape, ensure_ascii=False)
    out = _truncate_response(shape, serialized, MAX_RESPONSE_CHARS)
    parsed = json.loads(out)
    path = parsed["_full_result_file"]
    try:
        with open(path, encoding="utf-8") as f:
            assert len(json.load(f)) == 2000
        # saving the full copy must not push the reply over the cap
        assert len(out) <= MAX_RESPONSE_CHARS
    finally:
        if os.path.isfile(path):
            os.unlink(path)
