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
from typing import Any, Dict

from .base_rest_tool import BaseRESTTool
from .tool_registry import register_tool

PANELS_URL = "https://panelapp.genomicsengland.co.uk/api/v1/panels/"
_MAX_PAGES = 10  # safety cap; ~434 panels / 100 per page = 5 pages today

# Thresholds for the inflection heuristic in _word_matches(). English
# plural/adjectival suffixes (e.g. "y"->"ies", "-opathy"->"-opathies") are
# usually 1-3 characters, so a shared prefix within 3 characters of the
# shorter word's length is treated as the same term. _MIN_WORD_LEN and
# _MAX_LEN_DIFF guard against short/dissimilar-length words matching by
# coincidence (e.g. "cardiac" vs "cardiomyopathy" must NOT match).
_MIN_WORD_LEN = 6
_MAX_LEN_DIFF = 4
_MAX_SUFFIX_DROP = 3


def _word_matches(query_word: str, haystack_word: str) -> bool:
    """True if two words are the same disease term modulo simple English
    inflection (singular/plural, e.g. "haemoglobinopathy" vs
    "haemoglobinopathies"). Deliberately NOT a general substring match --
    e.g. "myopathy" is a literal substring of "cardiomyopathy" but they are
    different, unrelated panel topics, so containment alone is too loose.
    Only an exact match, or a shared prefix between two words of similar
    length (inflectional suffixes differ by a couple of characters, not by
    a whole extra word), counts as the same term.
    """
    if not query_word or not haystack_word:
        return False
    if query_word == haystack_word:
        return True
    if (
        len(query_word) >= _MIN_WORD_LEN
        and len(haystack_word) >= _MIN_WORD_LEN
        and abs(len(query_word) - len(haystack_word)) <= _MAX_LEN_DIFF
    ):
        shorter = min(len(query_word), len(haystack_word))
        common_prefix = len(os.path.commonprefix([query_word, haystack_word]))
        return common_prefix >= shorter - _MAX_SUFFIX_DROP
    return False


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
        query_words = search.split()

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
            haystack_words = haystack.split()
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
