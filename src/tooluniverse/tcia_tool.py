"""
TCIA (The Cancer Imaging Archive) NBIA REST API tool.

The NBIA v1 REST services answer *every* zero-result query the same way: HTTP
200 with a completely empty body and no ``Content-Type`` header.  Verified live
against ``services.cancerimagingarchive.net``::

    getModalityValues?Collection=NSCLC-Radiogenomics  -> 200, body ''
    getModalityValues?Collection=NSCLC Radiogenomics  -> 200, [{"Modality":"CT"},...]
    getSeries?Collection=NSCLC Radiogenomics&Modality=MR -> 200, body ''
    getSeries?Collection=NSCLC Radiogenomics&Modality=CT -> 200, [ ...series... ]

``BaseRESTTool._process_response`` cannot decode an empty body as JSON, so it
falls through to its plain-text branch and reports ``{"status": "success",
"data": ""}`` -- an empty *string* where every non-empty response is a *list*,
with no ``count`` key at all.  Three failures compound in that one payload:

1. A misspelled / nonexistent collection is reported as a success.  Collection
   names are exact-match and are not consistently punctuated (the real
   ``NSCLC Radiogenomics`` sits next to ``NSCLC-Radiomics`` and
   ``NSCLC-Radiomics-Genomics``), so hyphenating it is a natural mistake that
   the API silently swallows.
2. ``data`` changes type between the hit and the miss, so ``len(data)`` is 0
   either way and iteration yields nothing without raising.
3. A genuine filter miss on a *valid* collection is byte-identical to (1), so a
   caller cannot tell "this collection has no MR series" from "you typed the
   collection name wrong".

This subclass fixes all three at the point where the archive goes quiet:

* An empty body always becomes ``data: []`` with ``count: 0`` -- a list, like
  every non-empty response, never ``""``.
* If a ``Collection`` argument was supplied and it is not one of the names the
  archive publishes, the result is ``status: "error"`` naming the closest real
  collection names instead of a silent success.
* Otherwise the empty list carries a ``note`` stating that the collection is
  real and that the remaining filters are what matched nothing.

Cost: validation needs the collection list (~155 names).  It is fetched **only
on the empty-result path** -- the request is paid for exactly when the tool is
about to return nothing, never on the overwhelmingly common success path -- and
then memoized for the life of the process, so a session that mistypes several
collection names still makes at most one extra request.
"""

import threading
from difflib import get_close_matches
from typing import Any

from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool

COLLECTION_VALUES_URL = (
    "https://services.cancerimagingarchive.net/nbia-api/services/v1/getCollectionValues"
)

# Process-wide memo of the published collection names. The archive's collection
# list changes on the order of months, so caching for the process lifetime is
# safe and keeps the validation cost at one request per session.
_COLLECTIONS_LOCK = threading.Lock()
_COLLECTIONS_CACHE: dict[str, Any] = {"names": None, "error": None}


def _reset_collection_cache() -> None:
    """Clear the memoized collection list (used by tests)."""
    with _COLLECTIONS_LOCK:
        _COLLECTIONS_CACHE["names"] = None
        _COLLECTIONS_CACHE["error"] = None


def _normalize(name: str) -> str:
    """Fold case and separator punctuation so 'NSCLC-Radiogenomics' == 'NSCLC Radiogenomics'."""
    return "".join(ch for ch in name.lower() if ch.isalnum())


@register_tool("TCIATool")
class TCIATool(BaseRESTTool):
    """BaseRESTTool for the NBIA v1 API that never reports an empty body as bare success."""

    def _fetch_collection_names(self) -> list[str] | None:
        """
        Return the archive's collection names, memoized per process.

        Returns None (and records the reason) when the list cannot be fetched,
        so a validation outage degrades to "cannot verify" rather than to a
        false "this collection does not exist".  Only successes are memoized: a
        transient outage must not disable validation for the whole process.
        """
        with _COLLECTIONS_LOCK:
            if _COLLECTIONS_CACHE["names"] is not None:
                return _COLLECTIONS_CACHE["names"]

        names: list[str] | None = None
        error: str | None = None
        try:
            response = request_with_retry(
                self.session,
                "GET",
                COLLECTION_VALUES_URL,
                timeout=self.timeout,
                max_attempts=2,
            )
            if 200 <= response.status_code < 300:
                payload = response.json()
                if isinstance(payload, list):
                    names = [
                        row["Collection"]
                        for row in payload
                        if isinstance(row, dict)
                        and isinstance(row.get("Collection"), str)
                    ]
            if not names:
                names = None
                error = f"getCollectionValues returned no usable collection list (HTTP {response.status_code})"
        except Exception as exc:  # network / decode failure
            names = None
            error = str(exc)

        with _COLLECTIONS_LOCK:
            _COLLECTIONS_CACHE["names"] = names
            _COLLECTIONS_CACHE["error"] = error
        return names

    @staticmethod
    def _suggest(collection: str, known: list[str]) -> list[str]:
        """Closest real collection names to a name that does not exist."""
        target = _normalize(collection)
        # An exact match once case and separators are folded is almost always
        # the intended collection (the reported 'NSCLC-Radiogenomics' case), so
        # rank those first.
        suggestions = [name for name in known if _normalize(name) == target]
        for name in get_close_matches(collection, known, n=5, cutoff=0.6):
            if name not in suggestions:
                suggestions.append(name)
        if not suggestions:
            suggestions = [
                name
                for name in known
                if target and (target in _normalize(name) or _normalize(name) in target)
            ]
        return suggestions[:3]

    def _filter_summary(self, arguments: dict[str, Any], skip: str = "") -> str:
        """Render the non-empty filters that were actually sent, for the note text."""
        parts = [
            f"{key}={value!r}"
            for key, value in (arguments or {}).items()
            if key != skip and value is not None and value != ""
        ]
        return ", ".join(parts)

    @staticmethod
    def _requested_url(response: Any, url: str) -> str:
        """
        Echo the fully-resolved request URI rather than the bare endpoint.

        BaseRESTTool keeps the query string in ``params``, so the echoed ``url``
        was just the endpoint -- two very different queries against
        ``/getSeries`` were reported identically and neither could be
        reproduced from the response. ``response.url`` carries the filters that
        were actually sent. Falls back to the endpoint when the attribute is
        absent or is not a real string (stubbed responses in tests).
        """
        resolved = getattr(response, "url", None)
        return resolved if isinstance(resolved, str) and resolved else url

    def _process_response(self, response, url):
        """Attach the resolved request URI to the normal (non-empty) success path."""
        return super()._process_response(response, self._requested_url(response, url))

    def _handle_special_endpoint(self, url, response, arguments):
        """
        Intercept NBIA's empty-body "no results" response.

        Returns None for any response with a body so normal processing (and any
        real error handling) is untouched.
        """
        if (getattr(response, "text", "") or "").strip():
            return None

        url = self._requested_url(response, url)
        endpoint = self.tool_config.get("fields", {}).get("endpoint", "")
        collection = (arguments or {}).get("Collection")
        collection = collection.strip() if isinstance(collection, str) else None

        # getCollectionValues is the validation source itself; never recurse.
        if collection and "getCollectionValues" not in endpoint:
            known = self._fetch_collection_names()
            if known is not None and collection not in known:
                suggestions = self._suggest(collection, known)
                hint = (
                    " Closest existing collection name(s): "
                    + ", ".join(f"'{name}'" for name in suggestions)
                    + "."
                    if suggestions
                    else ""
                )
                return {
                    "status": "error",
                    "error": (
                        f"TCIA: collection '{collection}' does not exist in The Cancer "
                        f"Imaging Archive (checked against the {len(known)} collections "
                        f"published by getCollectionValues).{hint} Collection names are "
                        f"matched exactly, including case, spaces and hyphens; call "
                        f"TCIA_list_collections for the full list."
                    ),
                    "suggestions": suggestions,
                    "invalid_collection": collection,
                    "url": url,
                }

            if known is not None:
                other = self._filter_summary(arguments, skip="Collection")
                narrowed = (
                    f" the other filters ({other}) matched nothing in it"
                    if other
                    else " it currently exposes no records for this endpoint"
                )
                note = (
                    f"No matching records. The collection '{collection}' exists in TCIA, so"
                    f"{narrowed}."
                )
            else:
                note = (
                    f"No matching records. The collection name '{collection}' could not be "
                    f"verified against TCIA_list_collections "
                    f"({_COLLECTIONS_CACHE.get('error')}), so a misspelled collection name "
                    f"cannot be ruled out as the cause."
                )
        else:
            filters = self._filter_summary(arguments)
            note = (
                "No matching records"
                + (f" for {filters}" if filters else "")
                + ". TCIA matches identifiers exactly, so a value that does not exist "
                "returns the same empty result as a filter that genuinely has no data."
            )

        return {
            "status": "success",
            "data": [],
            "count": 0,
            "url": url,
            "note": note,
        }
