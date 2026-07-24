"""Unit test: UniProt compact summary must keep the COFACTOR comment.

Regression: _compact_entry included a comment only if it had a top-level `texts`
array, but COFACTOR comments store their data under `cofactors[].name` (+ an
optional `note.texts`). So the cofactor was silently dropped from the default
compact summary -- confirmed live that PAH (P00439)'s Fe(2+) cofactor, a
clinically relevant field for a pediatric metabolic geneticist, vanished.
"""
import pytest

from tooluniverse.uniprot_tool import UniProtRESTTool


def _tool():
    return UniProtRESTTool(
        {
            "name": "UniProt_get_entry_by_accession",
            "type": "UniProtRESTTool",
            "fields": {"endpoint": "https://rest.uniprot.org/uniprotkb/{accession}.json"},
            "parameter": {"type": "object", "properties": {}},
        }
    )


@pytest.mark.unit
def test_cofactor_comment_is_retained_with_names():
    data = {
        "comments": [
            {"commentType": "FUNCTION", "texts": [{"value": "does a thing"}]},
            {
                "commentType": "COFACTOR",
                "cofactors": [{"name": "Fe(2+)"}],
                "note": {"texts": [{"value": "Binds 1 Fe cation per subunit."}]},
            },
        ]
    }
    out = _tool()._compact_entry(data)["data"]
    by_type = {c["commentType"]: c for c in out["comments"]}
    assert "COFACTOR" in by_type
    assert "Fe(2+)" in by_type["COFACTOR"]["texts"]


@pytest.mark.unit
def test_cofactor_without_note_still_kept():
    data = {"comments": [{"commentType": "COFACTOR", "cofactors": [{"name": "Zn(2+)"}]}]}
    out = _tool()._compact_entry(data)["data"]
    by_type = {c["commentType"]: c for c in out["comments"]}
    assert by_type["COFACTOR"]["texts"] == ["Zn(2+)"]


@pytest.mark.unit
def test_texts_bearing_comments_unchanged():
    data = {"comments": [{"commentType": "FUNCTION", "texts": [{"value": "x"}]}]}
    out = _tool()._compact_entry(data)["data"]
    assert out["comments"][0]["commentType"] == "FUNCTION"
    assert out["comments"][0]["texts"] == ["x"]
