"""
NCBI E-utilities Tool with Rate Limiting

This module provides a base class for NCBI E-utilities API tools with
built-in rate limiting and retry logic to handle 429 errors.
"""

import time
import requests
from typing import Dict, Any, Optional
from .base_tool import BaseTool, request_url


def _as_list(value: Any) -> list:
    """Coerce an esearch warning/error field to a list of non-empty entries."""
    if isinstance(value, str):
        return [value] if value.strip() else []
    if isinstance(value, (list, tuple)):
        return [v for v in value if v]
    return []


def esearch_query_disclosure(
    esearch_result: Any, source: str = "NCBI"
) -> Dict[str, Any]:
    """Normalise NCBI's own report that it did not run the query as asked.

    Every eutils database silently drops search terms it cannot match and then
    answers the *remaining* query, returning a full result set for a question
    the caller never submitted. It discloses this in the response, in two
    different containers, and callers that read neither pass the broadened
    answer on as if it were the requested one.

    Which container is used is the whole point, and it is the opposite of what
    a reader expects:

    * ``warninglist`` is populated when the search ends with **zero** hits --
      i.e. exactly when the caller cannot be misled, because nothing came back.
    * ``errorlist.phrasesnotfound`` is populated when terms were dropped but
      hits **remain** -- i.e. exactly when the caller *is* misled.

    Measured live against eutils on 2026-08-13, one probe per database, each
    compared against the same query with the nonsense terms removed::

        db          term                                       count   count w/o
                                                                       dropped
        pubmed      benzene hematotoxicity <2 nonsense>          328     328
        clinvar     BRCA1 <2 nonsense>                         85195   85195
        gds         breast cancer <2 nonsense>                205972  205972
        snp         CFTR <2 nonsense>                          73734   73734
        medgen      cystic fibrosis <2 nonsense>                  79      79
        pmc         malaria <2 nonsense>                      258906  258906
        nuccore     BRCA1 human <2 nonsense>                    7359    7359
        sra         RNA-seq <2 nonsense>                     7209038 7209038
        gene        TP53 <2 nonsense>                          12703   12703
        protein     insulin <2 nonsense>                      283933  283933
        bioproject  cancer <2 nonsense>                        69134   69134
        biosample   liver <2 nonsense>                        470946  470946
        mesh        aspirin <2 nonsense>                          73      73
        books       pharmacology <2 nonsense>                  68357   68357

    All fourteen returned ``errorlist.phrasesnotfound`` with both nonsense
    terms and a ``count`` **identical** to the query with those terms deleted,
    confirming the dropped terms constrained nothing. All fourteen returned
    ``errorlist: null`` when nothing was dropped, so this disclosure is silent
    on unaffected queries by construction.

    A fifteenth probe, ``taxonomy`` with "Homo sapiens <2 nonsense>", was the
    only one to end with zero hits, and it populated BOTH containers at once
    (``errorlist.phrasesnotfound`` listing all four words, and ``warninglist``
    with ``outputmessages: ["No items found."]``) -- so the two must not be
    treated as mutually exclusive.

    Reading this costs no extra request: the containers are already present in
    the esearch response every caller here parses.

    ``fieldsnotfound`` is surfaced from the same container for the same reason:
    an unrecognised ``[field]`` tag is dropped, not honoured, so the results are
    not restricted the way the caller asked.

    Returns an empty dict unless NCBI reported an actual alteration -- a
    dropped phrase, an ignored phrase, a dropped term or an unrecognised field
    -- so unaffected responses keep their existing shape. A zero-hit search is
    NOT an alteration, however loudly NCBI announces it; see Fix-54A-2 at the
    guard below.
    """
    if not isinstance(esearch_result, dict):
        return {}

    warning_list = esearch_result.get("warninglist")
    error_list = esearch_result.get("errorlist")
    if not isinstance(warning_list, dict):
        warning_list = {}
    if not isinstance(error_list, dict):
        error_list = {}

    not_found = _as_list(warning_list.get("quotedphrasesnotfound"))
    ignored = _as_list(warning_list.get("phrasesignored"))
    messages = _as_list(warning_list.get("outputmessages"))
    terms_dropped = _as_list(error_list.get("phrasesnotfound"))
    fields_dropped = _as_list(error_list.get("fieldsnotfound"))

    # Fix-54A-2: `outputmessages` must NOT gate this on its own. NCBI emits
    # `warninglist.outputmessages: ["No items found."]` on EVERY zero-hit
    # search, including one it executed exactly as submitted -- measured live:
    #
    #     term "cystic fibrosis AND 1500[dp]"
    #       -> count 0, errorlist null,
    #          warninglist {"phrasesignored": [], "quotedphrasesnotfound": [],
    #                       "outputmessages": ["No items found."]}
    #
    # Gating on it made every empty search claim
    # `query_not_executed_as_submitted: True` with the warning "No items
    # found.", which is the opposite of what that flag means: the query WAS
    # run as asked, it simply matched nothing. Only an actual alteration --
    # a dropped phrase, an ignored phrase, a dropped term or an unrecognised
    # field -- is a disclosure. `outputmessages` is carried alongside one of
    # those when present, but never creates the block by itself, which is what
    # keeps a clean response's shape unchanged.
    if not (not_found or ignored or terms_dropped or fields_dropped):
        return {}

    metadata: Dict[str, Any] = {}
    if not_found:
        metadata["quoted_phrases_not_found"] = not_found
    if ignored:
        metadata["phrases_ignored"] = ignored
    if messages:
        metadata["ncbi_messages"] = messages
    if terms_dropped:
        metadata["terms_not_found"] = terms_dropped
    if fields_dropped:
        metadata["search_fields_not_found"] = fields_dropped

    translation = esearch_result.get("querytranslation")
    if isinstance(translation, str) and translation.strip():
        metadata["executed_query"] = translation.strip()

    # Top-level, unmissable statement of the mismatch for any caller that reads
    # metadata but not the individual warning keys.
    notes = []
    if not_found:
        notes.append(
            f"{source} could not match the quoted phrase(s) {not_found}; they "
            "were dropped and these results answer a BROADER query than the "
            "one submitted."
        )
    if ignored:
        notes.append(f"{source} ignored the phrase(s) {ignored}.")
    if terms_dropped:
        notes.append(
            f"{source} found no match for the term(s) {terms_dropped} and "
            "dropped them; the records returned were retrieved by the "
            "REMAINING terms and need not mention the dropped ones at all."
        )
    if fields_dropped:
        notes.append(
            f"{source} did not recognise the search field(s) {fields_dropped} "
            "and ignored the restriction, so the results are NOT limited to "
            "that field."
        )
    if messages:
        notes.append("; ".join(str(m) for m in messages))
    if notes:
        metadata["query_not_executed_as_submitted"] = True
        metadata["warning"] = " ".join(notes)

    return metadata


class NCBIEUtilsTool(BaseTool):
    """Base class for NCBI E-utilities tools with rate limiting."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.last_request_time = 0
        self.min_interval = 0.34  # ~3 requests/second (NCBI limit without API key)
        self.max_retries = 3
        self.initial_retry_delay = 1
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _make_request(
        self, endpoint: str, params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Make request with rate limiting and retry logic."""
        url = f"{self.base_url}{endpoint}"

        for attempt in range(self.max_retries):
            # Rate limiting
            elapsed = time.time() - self.last_request_time
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)

            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
                self.last_request_time = time.time()
                response.raise_for_status()

                # Try to parse JSON response
                try:
                    data = response.json()
                except ValueError:
                    # If not JSON, return text
                    data = response.text

                return {
                    "status": "success",
                    "data": data,
                    "url": request_url(response, url),
                    "content_type": response.headers.get(
                        "content-type", "application/json"
                    ),
                }

            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    # Exponential backoff for rate limiting
                    delay = self.initial_retry_delay * (2**attempt)
                    print(
                        f"Rate limited, retrying in {delay} seconds... (attempt {attempt + 1}/{self.max_retries})"
                    )
                    time.sleep(delay)
                    continue
                else:
                    return {
                        "status": "error",
                        "error": f"NCBI E-utilities API request failed: {str(e)}",
                        "url": request_url(e.response, url),
                        "status_code": (
                            e.response.status_code if hasattr(e, "response") else None
                        ),
                    }
            except requests.exceptions.RequestException as e:
                return {
                    "status": "error",
                    "error": f"NCBI E-utilities API request failed: {str(e)}",
                    "url": request_url(e.request, url),
                }

        return {
            "status": "error",
            "error": f"NCBI E-utilities API request failed after {self.max_retries} attempts",
            "url": url,
        }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with given arguments."""
        return self._make_request(self.endpoint, arguments)
