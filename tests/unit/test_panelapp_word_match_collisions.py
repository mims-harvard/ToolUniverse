"""Fix-47-2: PanelApp_search_panels matched unrelated disease terms.

`_word_matches` bounded only how much was trimmed off the SHORTER word to
reach the shared prefix, and never bounded what was left dangling off the
LONGER one -- so any short-ish query became a prefix search with three
characters of slack, and the extra characters on the other side could be a
whole different word. Measured against the live 433-panel PanelApp list,
`search="hernia"` returned 15 panels, every one a "Hereditary ..." panel with
no hernia content, presented under `count: 15` and a note describing the match
as being against name/disease_group/disease_sub_group. `search="myopia"`
returned 3 myopathy panels -- an eye disorder answered with muscle-disease
panels.

Bounding BOTH ends separates inflection from coincidence: a true inflection is
small on both sides, while every one of these collisions is lopsided.
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from tooluniverse.panelapp_tool import (
    _MAX_SUFFIX_LEFT,
    _MIN_WORD_LEN,
    PanelAppSearchTool,
    _word_matches,
)

pytestmark = pytest.mark.unit


class TestCollisionsAreRejected:
    """Each pair returned True before the fix. All are different conditions."""

    @pytest.mark.parametrize(
        "query,haystack",
        [
            ("hernia", "hereditary"),
            ("sarcoma", "sarcoidosis"),
            ("anaemia", "anaesthesia"),
            ("myopia", "myopathy"),
            ("disease", "distal"),
            ("neuropathy", "neuronal"),
            ("neuropathy", "neuron"),
            ("neuropathy", "neural"),
        ],
    )
    def test_unrelated_terms_do_not_match(self, query, haystack):
        assert not _word_matches(query, haystack)
        assert not _word_matches(haystack, query)


class TestRealInflectionStillMatches:
    """Recall the fix must not cost: plurals and medical adjectival forms."""

    @pytest.mark.parametrize(
        "query,haystack",
        [
            ("haemoglobinopathy", "haemoglobinopathies"),
            ("myopathy", "myopathies"),
            ("dystrophy", "dystrophies"),
            ("anomaly", "anomalies"),
            ("ataxia", "ataxias"),
            ("disease", "diseases"),
            ("ciliopathy", "ciliopathies"),
            ("epilepsy", "epilepsies"),
            ("diabetes", "diabetic"),
            ("syndrome", "syndromic"),
            ("tumour", "tumoral"),
            # The "-osis"/"-otic" alternation. A 3-character stem drop, so
            # these are the pairs that pin _MAX_STEM_DROP at 3.
            ("fibrosis", "fibrotic"),
            ("sclerosis", "sclerotic"),
            ("necrosis", "necrotic"),
            ("thrombosis", "thrombotic"),
            ("stenosis", "stenotic"),
            ("psoriasis", "psoriatic"),
            ("cirrhosis", "cirrhotic"),
        ],
    )
    def test_inflected_forms_match_both_ways(self, query, haystack):
        assert _word_matches(query, haystack)
        assert _word_matches(haystack, query)

    def test_identical_words_always_match(self):
        assert _word_matches("cardiomyopathy", "cardiomyopathy")

    def test_containment_is_not_enough(self):
        """"cardiac" is not "cardiomyopathy"; a long shared prefix alone must
        not be sufficient."""
        assert not _word_matches("cardiac", "cardiomyopathy")

    @pytest.mark.parametrize("short,other", [("renal", "renin"), ("colon", "colitis")])
    def test_words_below_the_length_floor_never_fuzzy_match(self, short, other):
        """Below _MIN_WORD_LEN only equality counts. These pairs are the right
        SHAPE to match (a short shared prefix, a short ending) and are rejected
        solely because one word is too short to judge -- so this fails if the
        floor is lowered, which a pair of long words could never detect."""
        assert len(short) < _MIN_WORD_LEN
        assert not _word_matches(short, other)
        assert not _word_matches(other, short)

    def test_the_length_floor_is_what_rejects_them(self):
        """Pin the reason: with the floor removed these WOULD match, so the
        assertion above is not passing for some unrelated reason."""
        assert _MAX_SUFFIX_LEFT >= len("renin") - len(os.path.commonprefix(
            ["renal", "renin"]
        ))


_PANELS = [
    # The three shapes that made `search="hernia"` return 15 wrong panels.
    {"id": 1, "name": "Hereditary ataxia", "disease_group": "Neurology", "disease_sub_group": ""},
    {"id": 2, "name": "Hereditary angioedema types I and II", "disease_group": "Immune", "disease_sub_group": ""},
    {"id": 3, "name": "Hereditary Erythrocytosis", "disease_group": "Haematology", "disease_sub_group": ""},
    # A genuine plural match that must survive.
    {
        "id": 4,
        "name": "Sickle cell, thalassaemia and other haemoglobinopathies",
        "disease_group": "Haematology",
        "disease_sub_group": "",
    },
    # Punctuation-adjacent terms: the word is followed by a comma / paren, and
    # hyphenated compounds. Whitespace splitting leaves the punctuation glued
    # to the word, where it defeats any suffix-sensitive comparison.
    {
        "id": 5,
        "name": "Hereditary ataxia and cerebellar anomalies, childhood onset",
        "disease_group": "Neurology",
        "disease_sub_group": "",
    },
    {
        "id": 6,
        "name": "Non-syndromic hypotrichosis",
        "disease_group": "Dermatological disorders",
        "disease_sub_group": "",
    },
]


def _tool():
    return PanelAppSearchTool({"name": "panelapp_test", "fields": {}, "parameter": {}})


def _resp(results):
    r = MagicMock()
    r.raise_for_status = MagicMock()
    r.json.return_value = {"count": len(results), "next": None, "results": results}
    return r


def _search(term):
    tool = _tool()
    with patch.object(tool.session, "get", return_value=_resp(_PANELS)):
        return tool.run({"search": term})


class TestEndToEndSearch:
    def test_hernia_returns_no_hereditary_panels(self):
        result = _search("hernia")
        assert result["data"]["count"] == 0
        assert result["data"]["results"] == []

    def test_hernia_zero_result_names_the_gene_level_fallback(self):
        """A zero must stay self-explaining, not become a bare dead end."""
        assert "PanelApp_search_genes" in _search("hernia")["metadata"]["note"]

    def test_singular_query_still_finds_the_plural_panel(self):
        result = _search("haemoglobinopathy")
        names = [p["name"] for p in result["data"]["results"]]
        assert names == ["Sickle cell, thalassaemia and other haemoglobinopathies"]

    def test_term_followed_by_a_comma_is_still_matched(self):
        """'anomalies,' must tokenize to 'anomalies'."""
        names = [p["name"] for p in _search("anomaly")["data"]["results"]]
        assert "Hereditary ataxia and cerebellar anomalies, childhood onset" in names

    def test_hyphenated_compound_is_split_into_words(self):
        """'non-syndromic' must tokenize to 'non' + 'syndromic'; as one token
        it shares no prefix with 'syndrome' and the panel is unreachable."""
        names = [p["name"] for p in _search("syndrome")["data"]["results"]]
        assert "Non-syndromic hypotrichosis" in names

    def test_count_matches_the_rows_returned(self):
        result = _search("hereditary")
        assert result["data"]["count"] == len(result["data"]["results"])
