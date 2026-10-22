"""MAGICapp guideline list with search.

``GET /api/v1/guidelines`` returns the 15 most recently published public
guidelines unless ``limit`` and ``offset`` are given: 15 of 464 on 2026-10-22,
so ``MAGICapp_list_guidelines`` could never show most of the catalogue and an
agent had no way to find a guideline on its topic. The API has no search
endpoint (``/guidelines/search`` answers 400), so this tool reads the whole
public list (``limit=500`` per page) and filters it here by words in the
guideline's name, organization and description, and by language.

Each guideline carries two ids. ``publishedId`` is the published version, the
one MAGICapp_get_guideline / _get_recommendations / _get_sections take;
``guidelineId`` is the current draft, which answers 401 when the draft is not
public and otherwise returns unpublished content (1336: 413 draft
recommendations against 314 published under 578).
"""

import re
import threading
import time
from typing import Any, Dict, List, Optional

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

PAGE_SIZE = 500
MAX_PAGES = 20  # 10,000 guidelines: far above the catalogue, guards a looping API
CATALOGUE_TTL_S = 3600
DEFAULT_LIMIT = 20
MAX_LIMIT = 100
GUIDELINE_URL = "https://app.magicapp.org/#/guideline/{short_code}"
# Fields a guideline is searched by, and the fields each returned row keeps.
SEARCH_FIELDS = ("name", "byName", "owner", "institutionName", "description")
ROW_FIELDS = (
    "publishedId",
    "guidelineId",
    "name",
    "byName",
    "owner",
    "language",
    "publishDate",
    "publishedRecommendationCount",
    "shortCode",
)

_cache: Dict[str, Any] = {"rows": None, "fetched": 0.0}
_cache_lock = threading.Lock()


def _words(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", str(text or "").lower())


def _holds(tokens: List[str], word: str) -> bool:
    """A query word is held when a token begins with it ('pregnan' -> pregnancy)."""
    return any(token.startswith(word) for token in tokens)


def match(rows: List[dict], query: Optional[str]) -> tuple:
    """(matching rows, how): guidelines whose searched fields hold every query
    word, those holding them all in the name first; else the guidelines holding
    the most query words. Catalogue order (newest first) breaks ties."""
    wanted = list(dict.fromkeys(_words(query)))
    if not wanted:
        return rows, "all"
    scored = []
    for i, row in enumerate(rows):
        tokens = _words(" ".join(str(row.get(f) or "") for f in SEARCH_FIELDS))
        held = sum(_holds(tokens, w) for w in wanted)
        if held:
            title = _words(" ".join(str(row.get(f) or "") for f in ("name", "byName")))
            in_title = all(_holds(title, w) for w in wanted)
            scored.append((held, in_title, i))
    every = [s for s in scored if s[0] == len(wanted)]
    if every:
        every.sort(key=lambda s: (not s[1], s[2]))
        return [rows[i] for _, _, i in every], "every word"
    scored.sort(key=lambda s: (-s[0], s[2]))
    return [rows[i] for _, _, i in scored], "any word"


def compact(row: dict) -> dict:
    out = {key: row.get(key) for key in ROW_FIELDS}
    if row.get("shortCode"):
        out["url"] = GUIDELINE_URL.format(short_code=row["shortCode"])
    return out


@register_tool("MAGICappGuidelineListTool")
class MAGICappGuidelineListTool(BaseRESTTool):
    """Search MAGICapp's public guidelines by topic, organization and language."""

    def catalogue(self) -> List[dict]:
        """Every public guideline, newest first as MAGICapp lists them; kept for
        an hour. A failed fetch raises and is not kept."""
        with _cache_lock:
            if (
                _cache["rows"] is not None
                and time.time() - _cache["fetched"] < CATALOGUE_TTL_S
            ):
                return _cache["rows"]
        url = self.tool_config["fields"]["endpoint"]
        rows: List[dict] = []
        for page in range(MAX_PAGES):
            response = request_with_retry(
                self.session,
                "GET",
                url,
                params={"limit": PAGE_SIZE, "offset": page * PAGE_SIZE},
                timeout=self.timeout,
                max_attempts=3,
            )
            response.raise_for_status()
            batch = response.json()
            if not isinstance(batch, list):
                raise ValueError(
                    "MAGICapp returned %s, not a guideline list" % type(batch).__name__
                )
            rows += batch
            if len(batch) < PAGE_SIZE:
                break
        with _cache_lock:
            _cache.update(rows=rows, fetched=time.time())
        return rows

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        try:
            limit = int(arguments.get("limit") or DEFAULT_LIMIT)
            offset = int(arguments.get("offset") or 0)
        except (TypeError, ValueError):
            return {"status": "error", "error": "limit and offset must be integers"}
        limit, offset = min(max(limit, 1), MAX_LIMIT), max(offset, 0)
        try:
            rows = self.catalogue()
        except Exception as e:  # never raise out of run()
            return {
                "status": "error",
                "error": f"MAGICapp guideline list unavailable: {e}",
            }
        language = str(arguments.get("language") or "").strip().lower()
        pool = (
            [
                r
                for r in rows
                if str(r.get("language") or "").lower().startswith(language)
            ]
            if language
            else rows
        )
        found, how = match(pool, arguments.get("query"))
        page = found[offset : offset + limit]
        metadata = {
            "public_guidelines": len(rows),
            "matching": len(found),
            "returned": len(page),
            "offset": offset,
            "matched_by": how,
            "id_to_use": "publishedId: pass it as guideline_id to MAGICapp_get_recommendations, "
            "MAGICapp_get_sections or MAGICapp_get_guideline (guidelineId is the unpublished draft)",
        }
        if how == "any word":
            metadata["matching_note"] = (
                "No guideline has every query word in its name, organization or description; "
                "these hold some of them, the most first. Check each is on the topic."
            )
        if offset + len(page) < len(found):
            metadata["next_offset"] = offset + len(page)
        return {
            "status": "success",
            "data": [compact(r) for r in page],
            "metadata": metadata,
        }
