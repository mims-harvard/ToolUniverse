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
# the same term when the longer one is the shorter one plus no more than
# _MAX_SUFFIX_LEFT trailing characters -- the length of an English
# inflectional ending. _MIN_WORD_LEN keeps short words from colliding by
# coincidence ("renal"/"renin" share "ren" and are otherwise the same shape).
#
# There used to be a second threshold here bounding how much was trimmed off
# the SHORTER word to reach the shared prefix. It is gone because at equal
# values it is dead code, not policy: `longer - prefix <= N` and
# `prefix <= shorter <= longer` together give `prefix >= longer - N >=
# shorter - N`, so the trim bound can never reject a pair the suffix bound
# accepts. Verified as well as argued -- 298,378 pairs over the live panel
# vocabulary and 400,000 synthetic pairs, zero disagreements.
_MIN_WORD_LEN = 6
_MAX_SUFFIX_LEFT = 3

# Panel names are prose, so a term is routinely followed by a comma or closing
# parenthesis ("...cerebellar anomalies, childhood onset", "(Lynch syndrome)")
# and is hyphenated as often as spaced ("non-syndromic"). Splitting on
# whitespace alone leaves the punctuation glued to the word, where it defeats
# any exact or suffix-sensitive comparison. Known cost of splitting hyphens:
# "non-syndromic" yields "syndromic", so search="syndrome" matches the three
# panels that are explicitly NON-syndromic. Word-level matching has no notion
# of negation; the alternative is losing every hyphenated compound, which is
# worse.
_WORD_RE = re.compile(r"[a-z0-9]+")


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

    Bounding what dangles off the LONGER word is the fix: a true inflection is
    a short ending, while every one of these collisions is lopsided. The
    inflection classes that matter are kept -- singulars/plurals
    ("anomaly"/"anomalies", "dystrophy"/"dystrophies"), the medical adjectival
    forms ("diabetes"/"diabetic", "syndrome"/"syndromic", "tumour"/"tumoral")
    and the "-osis"/"-otic" alternation ("thrombosis"/"thrombotic").

    It is NOT free, and the cost is concentrated where PanelApp's own
    `disease_group` vocabulary uses a derived form four or more characters
    longer than the query. Measured over 214 queries against the live
    433-panel list: ~198 wrong panel-hits removed, but ~51 real ones lost too,
    mostly "cardiac"/"cardiology" (15 panels, including Brugada, ARVC and the
    long/short-QT panels) and "immune"/"immunology" (11), plus
    "muscle"/"muscular" (12), "arrhythmia"/"arrhythmogenic" (6),
    "pigmentation"/"pigmentary" (3) and "retinopathy"/"retinal" (1). No
    threshold separates these from the collisions above -- "cardiac"/
    "cardiology" needs five dangling characters and "sarcoma"/"sarcoidosis"
    has six -- so widening the bound just restores the false positives. The
    trade is deliberate: a loss shows up as an honest empty result carrying
    the "try PanelApp_search_genes" note, whereas the old behaviour returned
    another disease's panels under a confident `count`. Callers who hit an
    empty result should retry with the other word form.
    """
    if not query_word or not haystack_word:
        return False
    if query_word == haystack_word:
        return True
    if len(query_word) < _MIN_WORD_LEN or len(haystack_word) < _MIN_WORD_LEN:
        return False
    shorter = min(len(query_word), len(haystack_word))
    longer = max(len(query_word), len(haystack_word))
    # Exact O(1) prefilter, not an approximation: the bound below needs
    # `longer - common_prefix <= _MAX_SUFFIX_LEFT`, and `common_prefix` can
    # never exceed `shorter`, so any pair further apart in length than
    # _MAX_SUFFIX_LEFT is already rejected. Checking it first keeps the
    # allocating character scan off the great majority of word pairs (this
    # runs over every word of every one of ~433 panels, per query word).
    if longer - shorter > _MAX_SUFFIX_LEFT:
        return False
    common_prefix = len(os.path.commonprefix([query_word, haystack_word]))
    return longer - common_prefix <= _MAX_SUFFIX_LEFT


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
            # Fix-47-2: word matching only tolerates a short inflectional
            # ending, so a query whose PanelApp counterpart is a longer
            # derived form ("cardiac" vs the "Cardiology" disease_group,
            # "retinopathy" vs "Retinal disorders") lands here rather than
            # matching. Naming that explicitly is what turns this empty
            # result into something the caller can act on.
            note += (
                " No panel matched this term in its name/disease_group/"
                "disease_sub_group metadata. Matching tolerates only a short "
                "word ending, so if PanelApp files your topic under a longer "
                "related word, retry with that form (e.g. 'cardiology' rather "
                "than 'cardiac', 'retinal' rather than 'retinopathy', "
                "'muscular' rather than 'muscle'). If you're looking for a "
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
