# panelapp_tool.py
"""PanelApp panel search tool for ToolUniverse.

PanelApp's `/panels/` endpoint silently ignores substring search params --
confirmed live: `search=`, `q=`, and `name__icontains=` all return the
unfiltered, unranked list of all 434 panels regardless of value; only an
exact full-string `name=` match filters anything (its OpenAPI schema
documents no search param at all, only `type` and `page`). Since the API
can't filter server-side, this fetches every panel (paginating the
API's fixed page_size=100) and filters client-side by substring match
against name/disease_group/disease_sub_group.
"""

import os
import re
from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

PANELS_URL = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"
_MAX_PAGES = 10  # safety cap; ~434 panels / 100 per page = 5 pages today

# Thresholds for the inflection heuristic in _word_matches(). Two words are
# the same term when what they DON'T share is, on both sides, no bigger than
# an English inflectional ending: at most _MAX_STEM_DROP characters trimmed
# off the shorter word to reach the shared stem, and at most
# _MAX_SUFFIX_LEFT characters hanging off the end of the longer one.
# _MAX_SUFFIX_LEFT is the bound that does the work: every collision this
# heuristic used to admit is lopsided and fails on it alone. _MAX_STEM_DROP
# stays at 3, the value it always had -- tightening it to 2 was tried and
# reverted, because 3 is exactly the length of the "-osis"/"-otic" alternation
# that runs through clinical vocabulary, and dropping to 2 silently cost seven
# real pairs (fibrosis/fibrotic, sclerosis/sclerotic, necrosis/necrotic,
# thrombosis/thrombotic, stenosis/stenotic, psoriasis/psoriatic,
# cirrhosis/cirrhotic) while rejecting no collision that _MAX_SUFFIX_LEFT
# had not already rejected on its own.
# _MIN_WORD_LEN keeps short words from colliding by coincidence.
_MIN_WORD_LEN = 6
_MAX_STEM_DROP = 3
_MAX_SUFFIX_LEFT = 3

# Panel names are prose, so a term is routinely followed by a comma or closing
# parenthesis ("...cerebellar anomalies, childhood onset", "(Lynch syndrome)")
# and is hyphenated as often as spaced ("non-syndromic"). Splitting on
# whitespace alone leaves the punctuation glued to the word, where it defeats
# any exact or suffix-sensitive comparison.
_WORD_RE = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def _words(text: str) -> list:
    """Split lowercase text into comparable words, dropping punctuation."""
    return _WORD_RE.findall(text)


def _word_matches(query_word: str, haystack_word: str) -> bool:
    """True if two words are the same disease term modulo simple English
    inflection ("haemoglobinopathy"/"haemoglobinopathies",
    "diabetes"/"diabetic"). Deliberately NOT a general substring match --
    e.g. "myopathy" is a literal substring of "cardiomyopathy" but they are
    different, unrelated panel topics, so containment alone is too loose.

    Fix-47-2: this used to bound only how much was trimmed off the SHORTER
    word to reach the shared prefix, and never bounded what was left dangling
    off the LONGER one. That made every short-ish query a prefix search with
    three characters of slack, and the extra characters on the other side
    could be a whole different word:

        "hernia"    vs "hereditary"  -> shared "her",   "editary" dangling
        "sarcoma"   vs "sarcoidosis" -> shared "sarco", "idosis"  dangling
        "myopia"    vs "myopathy"    -> shared "myop",  "athy"    dangling
        "anaemia"   vs "anaesthesia" -> shared "anae",  "sthesia" dangling
        "disease"   vs "distal"      -> shared "dis",   "tal"     dangling
        "neuropathy" vs "neuronal"/"neural"/"neuron"

    all returned True. Measured against the live 433-panel PanelApp list,
    `search="hernia"` returned 15 panels, every one of them a "Hereditary ..."
    panel with no hernia content, presented under a `count` of 15 and a note
    describing the match as being against name/disease_group/disease_sub_group
    -- wrong data, legitimised by a count. `search="myopia"` returned 3
    myopathy panels (an eye disorder answered with muscle-disease panels).

    Adding the second bound is the whole fix, and it is what separates
    inflection from coincidence: a true inflection is small on BOTH sides,
    while every one of these collisions is lopsided. The pre-existing bound on
    the shorter word is left at the value it always had -- tightening it was
    tried and reverted for costing real matches (see the constants above).
    Verified against the same live 433-panel list, the surviving matches are
    unchanged: singulars/plurals ("anomaly"/"anomalies",
    "dystrophy"/"dystrophies"), the medical adjectival forms
    ("diabetes"/"diabetic", "syndrome"/"syndromic", "tumour"/"tumoral") and
    the "-osis"/"-otic" alternation ("thrombosis"/"thrombotic").
    """
    if not query_word or not haystack_word:
        return False
    if query_word == haystack_word:
        return True
    if len(query_word) < _MIN_WORD_LEN or len(haystack_word) < _MIN_WORD_LEN:
        return False
    shorter = min(len(query_word), len(haystack_word))
    longer = max(len(query_word), len(haystack_word))
    # Exact O(1) prefilter, not an approximation: the suffix bound below needs
    # `longer - common_prefix <= _MAX_SUFFIX_LEFT`, and `common_prefix` can
    # never exceed `shorter`, so any pair further apart in length than
    # _MAX_SUFFIX_LEFT is already rejected. Checking it first keeps the
    # allocating character scan off the great majority of word pairs (this
    # runs over every word of every one of ~433 panels, per query word).
    if longer - shorter > _MAX_SUFFIX_LEFT:
        return False
    common_prefix = len(os.path.commonprefix([query_word, haystack_word]))
    return (
        common_prefix >= shorter - _MAX_STEM_DROP
        and longer - common_prefix <= _MAX_SUFFIX_LEFT
    )


@register_tool("PanelAppSearchTool")
class PanelAppSearchTool(BaseRESTTool):
    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        search = (arguments.get("search") or "").strip().lower()
        if not search:
            return {"status": "error", "error": "'search' is required"}

        panels = []
        url = PANELS_URL
        params = {"format": "json"}
        for _ in range(_MAX_PAGES):
            try:
                resp = self.session.get(url, params=params, timeout=self.timeout)
                resp.raise_for_status()
                page = resp.json()
            except Exception as e:
                return {"status": "error", "error": f"PanelApp API error: {e}"}
            panels.extend(page.get("results", []))
            url = page.get("next")
            params = None  # `next` already includes all query params
            if not url:
                break

        # Query-derived, so computed once outside the per-panel loop below.
        query_words = _words(search)

        def matches(p: Dict[str, Any]) -> bool:
            haystack = " ".join(
                str(p.get(k) or "")
                for k in ("name", "disease_group", "disease_sub_group")
            ).lower()
            if search in haystack:
                return True
            # Plain substring matching misses simple English inflection --
            # e.g. query "haemoglobinopathy" (singular) against panel name
            # "...haemoglobinopathies" (plural) never matches even though a
            # clinician typing the singular disease name expects a hit.
            # Fall back to a per-word fuzzy-prefix match: every query word
            # must share a long common prefix with some haystack word.
            haystack_words = _words(haystack)
            return all(
                any(_word_matches(qw, hw) for hw in haystack_words)
                for qw in query_words
            )

        results = [p for p in panels if matches(p)]
        note = (
            "PanelApp's API has no server-side search filter, so this "
            "matches client-side against name/disease_group/"
            "disease_sub_group across all panels."
        )
        if not results:
            # This only searches panel-level metadata, which doesn't
            # include every gene-level phenotype term (e.g. "haemophilia"
            # doesn't appear in any panel name/disease_group text -- it's
            # only reachable through the genes it curates, F8/F9). Point
            # the caller at the gene-level fallback instead of a dead end.
            note += (
                " No panel matched this term in its name/disease_group/"
                "disease_sub_group metadata. If you're looking for a "
                "condition by its causal gene(s) instead, try "
                "PanelApp_search_genes with the gene symbol."
            )
        return {
            "status": "success",
            "data": {
                "count": len(results),
                "next": None,
                "previous": None,
                "results": results,
            },
            "metadata": {
                "query": arguments.get("search"),
                "total_panels_searched": len(panels),
                "note": note,
            },
        }
