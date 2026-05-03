import requests
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry
import xml.etree.ElementTree as ET
import re


def _normalize_pmcid(pmcid: str | None) -> tuple[str | None, str | None]:
    """
    Return (pmcid_norm, pmcid_digits).

    pmcid_norm: "PMC123" form (or None)
    pmcid_digits: "123" digits only (or None)
    """
    if not isinstance(pmcid, str):
        return None, None
    s = pmcid.strip()
    if not s:
        return None, None
    upper = s.upper()
    pmcid_norm = upper if upper.startswith("PMC") else f"PMC{upper}"
    digits = pmcid_norm[3:]
    if not digits.isdigit():
        return pmcid_norm, None
    return pmcid_norm, digits


def _build_ncbi_pmc_oai_url(pmcid_digits: str | None) -> str | None:
    if not isinstance(pmcid_digits, str) or not pmcid_digits.isdigit():
        return None
    return (
        "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
        f"?verb=GetRecord&metadataPrefix=pmc&identifier=oai:pubmedcentral.nih.gov:{pmcid_digits}"
    )


def _build_ncbi_pmc_efetch_url(pmcid_digits: str | None) -> str | None:
    if not isinstance(pmcid_digits, str) or not pmcid_digits.isdigit():
        return None
    return (
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
        f"?db=pmc&id={pmcid_digits}&retmode=xml"
    )


def _build_ncbi_pmc_html_url(pmcid_norm: str | None) -> str | None:
    if not isinstance(pmcid_norm, str) or not pmcid_norm.strip():
        return None
    s = pmcid_norm.strip()
    s = s if s.upper().startswith("PMC") else f"PMC{s}"
    return f"https://pmc.ncbi.nlm.nih.gov/articles/{s}/"


def _extract_text_from_html(html_text: str) -> str:
    """
    Best-effort HTML -> text extraction.

    For PMC pages, try to restrict to the main content region to avoid nav/JS/CSS noise.
    """
    html_text = html_text or ""

    # Prefer main article content on PMC pages.
    m = re.search(
        r'(?is)<main[^>]*id=["\\\']maincontent["\\\'][^>]*>(.*?)</main>', html_text
    )
    if not m:
        m = re.search(
            r'(?is)<div[^>]*id=["\\\']maincontent["\\\'][^>]*>(.*?)</div>', html_text
        )
    if m:
        html_text = m.group(1)

    # Parse using stdlib HTMLParser (more robust than regex-only stripping).
    try:
        from html.parser import HTMLParser

        class _TextExtractor(HTMLParser):
            def __init__(self):
                super().__init__(convert_charrefs=True)
                self._parts: list[str] = []
                self._skip_depth = 0

            def handle_starttag(self, tag, attrs):
                t = (tag or "").lower()
                if t in {"script", "style", "noscript"}:
                    self._skip_depth += 1
                    return
                if self._skip_depth:
                    return
                if t in {
                    "p",
                    "br",
                    "div",
                    "section",
                    "li",
                    "tr",
                    "h1",
                    "h2",
                    "h3",
                    "h4",
                    "h5",
                    "h6",
                }:
                    self._parts.append(" ")

            def handle_endtag(self, tag):
                t = (tag or "").lower()
                if t in {"script", "style", "noscript"} and self._skip_depth:
                    self._skip_depth -= 1
                    return
                if self._skip_depth:
                    return
                if t in {"p", "br", "div", "section", "li", "tr"}:
                    self._parts.append(" ")

            def handle_data(self, data):
                if self._skip_depth:
                    return
                if data:
                    self._parts.append(data)

        parser = _TextExtractor()
        parser.feed(html_text)
        text = "".join(parser._parts)
    except Exception:
        # Fallback: regex stripping (kept for safety).
        html_text = re.sub(r"(?is)<(script|style|noscript).*?>.*?</\1>", " ", html_text)
        text = re.sub(r"(?s)<[^>]+>", " ", html_text)

    return " ".join((text or "").split())


def _extract_abstract_from_pmc_html(html_text: str) -> str | None:
    # Try meta tags first (most robust for machines).
    candidates = [
        r'(?is)<meta\\s+name=["\\\']citation_abstract["\\\']\\s+content=["\\\'](.*?)["\\\']',
        r'(?is)<meta\\s+name=["\\\']DC\\.Description["\\\']\\s+content=["\\\'](.*?)["\\\']',
        r'(?is)<meta\\s+name=["\\\']dc\\.description["\\\']\\s+content=["\\\'](.*?)["\\\']',
    ]
    for pat in candidates:
        m = re.search(pat, html_text or "")
        if m:
            abstract = m.group(1)
            abstract = _extract_text_from_html(abstract)
            if abstract:
                return abstract
    return None


def _detect_ncbi_oai_error(xml_text: str) -> dict | None:
    """
    NCBI PMC OAI-PMH often returns HTTP 200 even for logical errors, e.g.:
      <error code="cannotDisseminateFormat">...</error>

    Returns a small structured dict when an error is detected, else None.
    """
    if not isinstance(xml_text, str) or not xml_text.strip():
        return None
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return None
    # Only treat OAI-PMH top-level <error> as a logical error.
    if not (root.tag or "").lower().endswith("oai-pmh"):
        return None
    for el in list(root):
        if (el.tag or "").endswith("error"):
            code = el.attrib.get("code")
            msg = " ".join((el.text or "").split()) or None
            return {"code": code, "message": msg}
    return None


def _fetch_fulltext_with_trace(
    session: requests.Session,
    *,
    europe_fulltext_xml_url: str | None,
    pmcid: str | None,
    timeout: int = 20,
) -> dict:
    """
    Fetch full text content with a trace of attempts.

    Returns:
      {
        ok: bool,
        url: str|None,
        source: str|None,
        format: "xml"|"html"|None,
        content_type: str|None,
        status_code: int|None,
        content: str|None,
        trace: list[dict],
      }
    """
    pmcid_norm, pmcid_digits = _normalize_pmcid(pmcid)
    trace: list[dict] = []

    def _record(
        attempt: str, url: str | None, resp, *, note: str | None = None
    ) -> None:
        headers = getattr(resp, "headers", {}) or {}
        entry = {
            "attempt": attempt,
            "url": url,
            "status_code": getattr(resp, "status_code", None),
            "content_type": headers.get("content-type"),
            "note": note,
        }
        trace.append(entry)

    # 1) Europe PMC fullTextXML
    if isinstance(europe_fulltext_xml_url, str) and europe_fulltext_xml_url.strip():
        url = europe_fulltext_xml_url.strip()
        resp = request_with_retry(session, "GET", url, timeout=timeout, max_attempts=2)
        _record("europe_pmc_fulltextxml", getattr(resp, "url", url), resp)
        if resp.status_code == 200 and (resp.text or "").strip():
            headers = getattr(resp, "headers", {}) or {}
            return {
                "ok": True,
                "url": getattr(resp, "url", url),
                "source": "Europe PMC fullTextXML",
                "format": "xml",
                "content_type": headers.get("content-type"),
                "status_code": resp.status_code,
                "content": resp.text,
                "trace": trace,
            }

    # 2) NCBI PMC OAI-PMH (JATS XML)
    oai_url = _build_ncbi_pmc_oai_url(pmcid_digits)
    if oai_url:
        resp = request_with_retry(
            session, "GET", oai_url, timeout=timeout, max_attempts=2
        )
        oai_err = None
        if resp.status_code == 200 and (resp.text or "").strip():
            oai_err = _detect_ncbi_oai_error(resp.text)
        note = None
        if oai_err:
            code = oai_err.get("code") or "unknown"
            msg = oai_err.get("message")
            note = f"oai_error:{code}" + (f":{msg}" if msg else "")
        _record("ncbi_pmc_oai", getattr(resp, "url", oai_url), resp, note=note)

        if resp.status_code == 200 and (resp.text or "").strip() and not oai_err:
            headers = getattr(resp, "headers", {}) or {}
            return {
                "ok": True,
                "url": getattr(resp, "url", oai_url),
                "source": "NCBI PMC OAI (JATS)",
                "format": "xml",
                "content_type": headers.get("content-type"),
                "status_code": resp.status_code,
                "content": resp.text,
                "trace": trace,
            }

    # 3) NCBI PMC efetch (XML) - may return a restricted stub.
    efetch_url = _build_ncbi_pmc_efetch_url(pmcid_digits)
    if efetch_url:
        resp = request_with_retry(
            session, "GET", efetch_url, timeout=timeout, max_attempts=2
        )
        note = None
        if resp.status_code == 200 and (resp.text or "").strip():
            # Some publishers return a stub like: "does not allow download".
            lowered = (resp.text or "").lower()
            if "does not allow download" not in lowered:
                _record("ncbi_pmc_efetch", getattr(resp, "url", efetch_url), resp)
                headers = getattr(resp, "headers", {}) or {}
                return {
                    "ok": True,
                    "url": getattr(resp, "url", efetch_url),
                    "source": "NCBI PMC efetch (XML)",
                    "format": "xml",
                    "content_type": headers.get("content-type"),
                    "status_code": resp.status_code,
                    "content": resp.text,
                    "trace": trace,
                }
            note = "restricted_stub"
        _record("ncbi_pmc_efetch", getattr(resp, "url", efetch_url), resp, note=note)

    # 4) NCBI PMC HTML (last resort)
    html_url = _build_ncbi_pmc_html_url(pmcid_norm)
    if html_url:
        resp = request_with_retry(
            session, "GET", html_url, timeout=timeout, max_attempts=2
        )
        note = "forbidden" if resp.status_code == 403 else None
        _record("ncbi_pmc_html", getattr(resp, "url", html_url), resp, note=note)
        if resp.status_code == 200 and (resp.text or "").strip():
            headers = getattr(resp, "headers", {}) or {}
            return {
                "ok": True,
                "url": getattr(resp, "url", html_url),
                "source": "NCBI PMC HTML",
                "format": "html",
                "content_type": headers.get("content-type"),
                "status_code": resp.status_code,
                "content": resp.text,
                "trace": trace,
            }

    last = trace[-1] if trace else {}
    return {
        "ok": False,
        "url": last.get("url"),
        "source": None,
        "format": None,
        "content_type": last.get("content_type"),
        "status_code": last.get("status_code"),
        "content": None,
        "trace": trace,
    }


@register_tool("EuropePMCTool")
class EuropePMCTool(BaseTool):
    """
    Tool to search for articles on Europe PMC including abstracts.
    """

    def __init__(
        self,
        tool_config,
        base_url="https://www.ebi.ac.uk/europepmc/webservices/rest/search",
    ):
        super().__init__(tool_config)
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                # Some upstreams (notably NCBI/PMC) return 403 for the default
                # python-requests User-Agent. Set a conservative browser UA.
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

    def run(self, arguments):
        query = arguments.get("query")
        limit = arguments.get("limit") or arguments.get("page_size") or 5
        enrich_missing_abstract = bool(arguments.get("enrich_missing_abstract", False))
        extract_terms_from_fulltext = arguments.get("extract_terms_from_fulltext")
        require_has_ft = bool(arguments.get("require_has_ft", False))
        fulltext_terms = arguments.get("fulltext_terms")
        if not query:
            return {"status": "error", "error": "`query` parameter is required."}
        terms = (
            [t.strip() for t in fulltext_terms if isinstance(t, str) and t.strip()]
            if isinstance(fulltext_terms, list)
            else []
        )
        if terms:
            require_has_ft = True

            def _escape_phrase(s: str) -> str:
                # Europe PMC uses a Lucene-like syntax; keep this conservative.
                return s.replace('"', '\\"')

            clause = " OR ".join([f'BODY:"{_escape_phrase(t)}"' for t in terms])
            query = f"({query}) AND ({clause})"
        if require_has_ft:
            query = f"({query}) AND HAS_FT:Y"
        articles = self._search(
            query,
            limit,
            enrich_missing_abstract=enrich_missing_abstract,
            extract_terms_from_fulltext=extract_terms_from_fulltext,
        )
        return {
            "status": "success",
            "data": articles,
            "metadata": {
                "count": len(articles),
                "query": query,
                "source": "Europe PMC",
            },
        }

    def _local_name(self, tag: str) -> str:
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    def _extract_abstract_from_fulltext_xml(self, xml_text: str) -> str | None:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return None

        for el in root.iter():
            if self._local_name(el.tag).lower() == "abstract":
                text = " ".join("".join(el.itertext()).split())
                if text:
                    return text
        return None

    def _build_fulltext_xml_url(
        self, *, source_db: str | None, article_id: str | None, pmcid: str | None
    ) -> str | None:
        if pmcid:
            return (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            )
        if source_db and article_id:
            return f"https://www.ebi.ac.uk/europepmc/webservices/rest/{source_db}/{article_id}/fullTextXML"
        return None

    def _build_pmc_oai_url(self, pmcid: str | None) -> str | None:
        """
        Build an NCBI PMC OAI-PMH URL to retrieve JATS XML for a PMC article.

        Europe PMC fullTextXML is not always available even when an article is in PMC.
        The OAI endpoint provides a robust fallback for extracting full text/abstract.
        """
        if not isinstance(pmcid, str):
            return None
        s = pmcid.strip()
        if not s:
            return None
        s = s.upper()
        if s.startswith("PMC"):
            s = s[3:]
        if not s.isdigit():
            return None
        return (
            "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
            f"?verb=GetRecord&metadataPrefix=pmc&identifier=oai:pubmedcentral.nih.gov:{s}"
        )

    def _fetch_fulltext_with_trace(
        self, *, fulltext_url: str | None, pmcid: str | None, timeout: int = 20
    ) -> dict:
        return _fetch_fulltext_with_trace(
            self.session,
            europe_fulltext_xml_url=fulltext_url,
            pmcid=pmcid,
            timeout=timeout,
        )

    def _search(
        self,
        query,
        limit,
        *,
        enrich_missing_abstract: bool = False,
        extract_terms_from_fulltext: list | None = None,
    ):
        # First try core mode to get abstracts
        core_params = {
            "query": query,
            "resultType": "core",
            "pageSize": limit,
            "format": "json",
        }
        core_response = request_with_retry(
            self.session,
            "GET",
            self.base_url,
            params=core_params,
            timeout=20,
            max_attempts=3,
        )

        # Then try lite mode to get journal information
        lite_params = {
            "query": query,
            "resultType": "lite",
            "pageSize": limit,
            "format": "json",
        }
        lite_response = request_with_retry(
            self.session,
            "GET",
            self.base_url,
            params=lite_params,
            timeout=20,
            max_attempts=3,
        )

        if core_response.status_code != 200:
            return [
                {
                    "title": "Error",
                    "abstract": None,
                    "authors": [],
                    "journal": None,
                    "year": None,
                    "doi": None,
                    "url": None,
                    "citations": 0,
                    "open_access": False,
                    "keywords": [],
                    "source": "Europe PMC",
                    "error": f"Europe PMC API error {core_response.status_code}",
                    "reason": core_response.reason,
                    "retryable": core_response.status_code
                    in (408, 429, 500, 502, 503, 504),
                }
            ]

        # Get core mode results
        try:
            core_payload = core_response.json()
        except ValueError:
            return [
                {
                    "title": "Error",
                    "abstract": None,
                    "authors": [],
                    "journal": None,
                    "year": None,
                    "doi": None,
                    "url": None,
                    "citations": 0,
                    "open_access": False,
                    "keywords": [],
                    "source": "Europe PMC",
                    "error": "Europe PMC returned invalid JSON",
                    "retryable": True,
                }
            ]

        core_results = core_payload.get("resultList", {}).get("result", [])
        lite_results = []

        # If lite mode also succeeds, get journal information
        if lite_response.status_code == 200:
            try:
                lite_payload = lite_response.json()
            except ValueError:
                lite_payload = {}
            lite_results = lite_payload.get("resultList", {}).get("result", [])

        # Create ID to record mapping
        lite_map = {rec.get("id"): rec for rec in lite_results}

        articles = []
        for rec in core_results:
            # Extract basic information
            title = rec.get("title")
            raw_abstract = rec.get("abstractText") or None
            # Strip HTML tags that sometimes appear in EuropePMC abstracts
            if raw_abstract and "<" in raw_abstract:
                abstract = _extract_text_from_html(raw_abstract) or raw_abstract
            else:
                abstract = raw_abstract
            year = rec.get("pubYear")

            # Extract author information
            authors = []
            author_list = rec.get("authorList", {}).get("author", [])
            if isinstance(author_list, list):
                for author in author_list:
                    if isinstance(author, dict):
                        full_name = author.get("fullName", "")
                        if full_name:
                            authors.append(full_name)
            elif isinstance(author_list, dict):
                full_name = author_list.get("fullName", "")
                if full_name:
                    authors.append(full_name)

            # Get journal information from lite mode
            journal = None
            if rec.get("id") in lite_map:
                lite_rec = lite_map[rec["id"]]
                journal = lite_rec.get("journalTitle")

            # If still no journal information, use source field
            if not journal:
                journal = rec.get("source")

            # Extract DOI
            doi = rec.get("doi") or None
            doi_url = f"https://doi.org/{doi}" if doi else None

            source_db = rec.get("source") or None
            article_id = rec.get("id") or None
            pmid = rec.get("pmid") or None
            pmcid = rec.get("pmcid") or None

            if isinstance(pmcid, str):
                pmcid = pmcid.strip() or None

            # Extract citation count
            citations = rec.get("citedByCount", 0)
            if citations:
                try:
                    citations = int(citations)
                except (ValueError, TypeError):
                    citations = 0

            # Extract open access status
            open_access_raw = rec.get("isOpenAccess", False)
            # Normalize to boolean (API can return 'Y'/'N' or True/False)
            if isinstance(open_access_raw, str):
                open_access = open_access_raw.upper() == "Y"
            else:
                open_access = bool(open_access_raw)

            # Extract keywords from keywordList (author-supplied keywords)
            keywords = []
            kw_list = rec.get("keywordList", {})
            if isinstance(kw_list, dict):
                kw_data = kw_list.get("keyword", [])
                if isinstance(kw_data, list):
                    keywords.extend(kw_data)
                elif isinstance(kw_data, str):
                    keywords.append(kw_data)

            # Build URL
            url = (
                f"https://europepmc.org/article/{source_db}/{article_id}"
                if source_db and article_id
                else None
            )
            # Only generate fulltext XML URL for open-access articles (Feature-125A-004)
            fulltext_xml_url = (
                self._build_fulltext_xml_url(
                    source_db=source_db, article_id=article_id, pmcid=pmcid
                )
                if open_access
                else None
            )

            articles.append(
                {
                    "title": title or "Title not available",
                    "abstract": abstract,
                    "authors": authors,
                    "journal": journal or None,
                    "year": year,
                    "doi": doi,
                    "url": url,
                    "source_db": source_db,
                    "article_id": article_id,
                    "pmid": pmid,
                    "pmcid": pmcid,
                    "doi_url": doi_url,
                    "fulltext_xml_url": fulltext_xml_url,
                    "citations": citations,
                    "open_access": open_access,
                    "keywords": keywords,
                    "source": "Europe PMC",
                    "data_quality": {
                        "has_abstract": bool(abstract),
                        "has_authors": bool(authors),
                        "has_journal": bool(journal),
                        "has_year": bool(year),
                        "has_doi": bool(doi),
                        "has_citations": bool(citations and citations > 0),
                        "has_keywords": bool(keywords),
                        "has_url": bool(url),
                    },
                }
            )

        if enrich_missing_abstract:
            # Keep enrichment bounded to avoid slow calls.
            max_enrich = min(int(limit) if limit else 5, 3)
            enriched = 0
            for a in articles:
                if enriched >= max_enrich:
                    break
                if not isinstance(a, dict):
                    continue
                if a.get("abstract"):
                    continue
                fulltext_url = a.get("fulltext_xml_url")
                if not isinstance(fulltext_url, str) or not fulltext_url:
                    continue
                fetch = self._fetch_fulltext_with_trace(
                    fulltext_url=fulltext_url, pmcid=a.get("pmcid"), timeout=20
                )
                content = fetch.get("content")
                if not isinstance(content, str) or not content.strip():
                    continue

                abstract_from_fulltext = None
                if fetch.get("format") == "xml":
                    abstract_from_fulltext = self._extract_abstract_from_fulltext_xml(
                        content
                    )
                elif fetch.get("format") == "html":
                    abstract_from_fulltext = _extract_abstract_from_pmc_html(content)

                if abstract_from_fulltext:
                    a["abstract"] = abstract_from_fulltext
                    a["abstract_source"] = fetch.get("source") or "fulltext"
                    a["abstract_retrieval_trace"] = fetch.get("trace") or []
                    if isinstance(a.get("data_quality"), dict):
                        a["data_quality"]["has_abstract"] = True
                    enriched += 1

        # Extract fulltext snippets if requested
        if extract_terms_from_fulltext and isinstance(
            extract_terms_from_fulltext, list
        ):
            # Filter valid terms -- accept any number, process in batches of 5
            all_valid_terms = [
                t.strip()
                for t in extract_terms_from_fulltext
                if isinstance(t, str) and t.strip()
            ]

            if all_valid_terms:
                # Chunk terms into batches of 5 to stay within safe limits
                batch_size = 5
                term_batches = [
                    all_valid_terms[i : i + batch_size]
                    for i in range(0, len(all_valid_terms), batch_size)
                ]

                # Process up to 3 OA articles to avoid latency
                max_snippet_articles = 3
                processed = 0

                for a in articles:
                    if processed >= max_snippet_articles:
                        break
                    if not isinstance(a, dict):
                        continue
                    # Only process open access articles with fulltext URLs
                    if not a.get("open_access"):
                        continue
                    fulltext_url = a.get("fulltext_xml_url")
                    if not isinstance(fulltext_url, str) or not fulltext_url:
                        continue

                    # Extract snippets using the existing tool logic
                    try:
                        fetch = self._fetch_fulltext_with_trace(
                            fulltext_url=fulltext_url, pmcid=a.get("pmcid"), timeout=30
                        )
                        content = fetch.get("content")
                        if not isinstance(content, str) or not content.strip():
                            continue

                        if fetch.get("format") == "xml":
                            try:
                                root = ET.fromstring(content or "")
                                text = " ".join("".join(root.itertext()).split())
                            except ET.ParseError:
                                continue
                        else:
                            text = _extract_text_from_html(content)

                        # Extract snippets around terms, processing all batches
                        snippets = []
                        total_chars = 0
                        max_total_chars = 8000
                        window_chars = 220
                        max_snippets_per_term = 3
                        low = text.lower()

                        for batch in term_batches:
                            for term in batch:
                                needle = term.lower()
                                found = 0
                                for m in re.finditer(re.escape(needle), low):
                                    if found >= max_snippets_per_term:
                                        break
                                    start = max(0, m.start() - window_chars)
                                    end = min(len(text), m.end() + window_chars)
                                    snippet = text[start:end].strip()
                                    if total_chars + len(snippet) > max_total_chars:
                                        break
                                    snippets.append({"term": term, "snippet": snippet})
                                    total_chars += len(snippet)
                                    found += 1
                            # Stop processing more batches if char budget exhausted
                            if total_chars >= max_total_chars:
                                break

                        if snippets:
                            a["fulltext_snippets"] = snippets
                            a["fulltext_snippets_count"] = len(snippets)
                            a["fulltext_snippets_source"] = fetch.get("source")
                            a["fulltext_snippets_retrieval_trace"] = (
                                fetch.get("trace") or []
                            )

                        processed += 1
                    except Exception:
                        # Silently skip articles that fail snippet extraction
                        continue

        return articles


@register_tool("EuropePMCFullTextSnippetsTool")
class EuropePMCFullTextSnippetsTool(BaseTool):
    """
    Fetch Europe PMC fullTextXML (open access) and return bounded text snippets
    around user-provided terms. This helps answer questions where the crucial
    detail is present in the full text (e.g., methods/section titles) but not
    necessarily in the abstract.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
                # NCBI/PMC frequently blocks the default python-requests UA.
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

    def _build_pmc_html_url(self, pmcid: str | None) -> str | None:
        if not isinstance(pmcid, str):
            return None
        s = pmcid.strip()
        if not s:
            return None
        s = s if s.upper().startswith("PMC") else f"PMC{s}"
        return f"https://pmc.ncbi.nlm.nih.gov/articles/{s}/"

    def _build_pmc_oai_url(self, pmcid: str | None) -> str | None:
        if not isinstance(pmcid, str):
            return None
        s = pmcid.strip()
        if not s:
            return None
        s = s.upper()
        if s.startswith("PMC"):
            s = s[3:]
        if not s.isdigit():
            return None
        return (
            "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
            f"?verb=GetRecord&metadataPrefix=pmc&identifier=oai:pubmedcentral.nih.gov:{s}"
        )

    def _build_fulltext_xml_url(self, arguments: dict) -> str | None:
        fulltext_xml_url = arguments.get("fulltext_xml_url")
        if isinstance(fulltext_xml_url, str) and fulltext_xml_url.strip():
            return fulltext_xml_url.strip()

        pmcid = arguments.get("pmcid")
        if isinstance(pmcid, str) and pmcid.strip():
            pmcid = pmcid.strip()
            pmcid = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
            return (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            )

        source_db = arguments.get("source_db") or arguments.get("source")
        article_id = arguments.get("article_id")
        if (
            isinstance(source_db, str)
            and source_db.strip()
            and isinstance(article_id, str)
            and article_id.strip()
        ):
            return f"https://www.ebi.ac.uk/europepmc/webservices/rest/{source_db.strip()}/{article_id.strip()}/fullTextXML"

        return None

    def _extract_text(self, xml_text: str) -> str:
        root = ET.fromstring(xml_text)
        # Collapse whitespace to make snippets readable and stable.
        return " ".join("".join(root.itertext()).split())

    def _extract_text_from_html(self, html_text: str) -> str:
        return _extract_text_from_html(html_text or "")

    def run(self, arguments):
        fulltext_url = self._build_fulltext_xml_url(arguments)
        terms = arguments.get("terms")
        if terms is None:
            terms = arguments.get("keywords")

        if not fulltext_url:
            return {
                "status": "error",
                "error": "Provide `fulltext_xml_url`, or `pmcid`, or (`source_db` + `article_id`).",
                "retryable": False,
            }
        if not isinstance(terms, list) or not [
            t for t in terms if isinstance(t, str) and t.strip()
        ]:
            return {
                "status": "error",
                "error": "Provide a non-empty list of search terms via `terms` (preferred) or `keywords` (alias).",
                "retryable": False,
            }

        try:
            window_chars = int(arguments.get("window_chars", 220))
        except (TypeError, ValueError):
            window_chars = 220
        window_chars = max(20, min(window_chars, 2000))

        try:
            max_snippets_per_term = int(arguments.get("max_snippets_per_term", 3))
        except (TypeError, ValueError):
            max_snippets_per_term = 3
        max_snippets_per_term = max(1, min(max_snippets_per_term, 10))

        try:
            max_total_chars = int(arguments.get("max_total_chars", 8000))
        except (TypeError, ValueError):
            max_total_chars = 8000
        max_total_chars = max(1000, min(max_total_chars, 50000))

        fetch = _fetch_fulltext_with_trace(
            self.session,
            europe_fulltext_xml_url=fulltext_url,
            pmcid=arguments.get("pmcid"),
            timeout=30,
        )
        content = fetch.get("content")
        if not isinstance(content, str) or not content.strip():
            return {
                "status": "error",
                "error": "Full text fetch failed",
                "url": fetch.get("url") or fulltext_url,
                "status_code": fetch.get("status_code"),
                "retryable": fetch.get("status_code") in (408, 429, 500, 502, 503, 504),
                "retrieval_trace": fetch.get("trace") or [],
            }

        try:
            if fetch.get("format") == "xml":
                text = self._extract_text(content)
            else:
                text = _extract_text_from_html(content)
        except ET.ParseError:
            return {
                "status": "error",
                "error": "Full text returned invalid XML",
                "url": fetch.get("url") or fulltext_url,
                "retryable": True,
                "retrieval_trace": fetch.get("trace") or [],
            }

        snippets = []
        total_chars = 0
        low = text.lower()

        for raw_term in terms:
            if not isinstance(raw_term, str):
                continue
            term = raw_term.strip()
            if not term:
                continue

            needle = term.lower()
            found = 0
            for m in re.finditer(re.escape(needle), low):
                if found >= max_snippets_per_term:
                    break
                start = max(0, m.start() - window_chars)
                end = min(len(text), m.end() + window_chars)
                snippet = text[start:end].strip()
                # Bound total output size
                if total_chars + len(snippet) > max_total_chars:
                    break
                snippets.append({"term": term, "snippet": snippet})
                total_chars += len(snippet)
                found += 1

        return {
            "status": "success",
            "url": fetch.get("url"),
            "source": fetch.get("source"),
            "format": fetch.get("format"),
            "content_type": fetch.get("content_type"),
            "retrieval_trace": fetch.get("trace") or [],
            "snippets": snippets,
            "snippets_count": len(snippets),
            "truncated": total_chars >= max_total_chars,
        }


@register_tool("EuropePMCFullTextFetchTool")
class EuropePMCFullTextFetchTool(BaseTool):
    """
    Fetch full text content for a PMC article with deterministic fallbacks and
    machine-readable provenance (retrieval_trace).

    This tool is intended for machine consumption: it always returns a structured
    status payload and, when successful, includes source/format/content_type.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/xml, text/xml;q=0.9, text/html;q=0.8, */*;q=0.7",
                # NCBI/PMC frequently blocks the default python-requests UA.
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

    def _build_fulltext_xml_url(self, arguments: dict) -> str | None:
        fulltext_xml_url = arguments.get("fulltext_xml_url")
        if isinstance(fulltext_xml_url, str) and fulltext_xml_url.strip():
            return fulltext_xml_url.strip()

        pmcid = arguments.get("pmcid")
        if isinstance(pmcid, str) and pmcid.strip():
            pmcid = pmcid.strip()
            pmcid = pmcid if pmcid.upper().startswith("PMC") else f"PMC{pmcid}"
            return (
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid}/fullTextXML"
            )

        source_db = arguments.get("source_db") or arguments.get("source")
        article_id = arguments.get("article_id")
        if (
            isinstance(source_db, str)
            and source_db.strip()
            and isinstance(article_id, str)
            and article_id.strip()
        ):
            return f"https://www.ebi.ac.uk/europepmc/webservices/rest/{source_db.strip()}/{article_id.strip()}/fullTextXML"

        return None

    def run(self, arguments):
        fulltext_url = self._build_fulltext_xml_url(arguments)
        pmcid = arguments.get("pmcid")

        output_format = arguments.get("output_format", "text")
        if output_format not in ("text", "raw"):
            output_format = "text"

        include_raw = bool(arguments.get("include_raw", False))

        try:
            max_chars = int(arguments.get("max_chars", 200000))
        except (TypeError, ValueError):
            max_chars = 200000
        max_chars = max(1000, min(max_chars, 2_000_000))

        try:
            max_raw_chars = int(arguments.get("max_raw_chars", 200000))
        except (TypeError, ValueError):
            max_raw_chars = 200000
        max_raw_chars = max(1000, min(max_raw_chars, 2_000_000))

        try:
            timeout = int(arguments.get("timeout", 30))
        except (TypeError, ValueError):
            timeout = 30
        timeout = max(5, min(timeout, 120))

        if not fulltext_url and not isinstance(pmcid, str):
            return {
                "status": "error",
                "error": "Provide `pmcid`, or `fulltext_xml_url`, or (`source_db` + `article_id`).",
                "retryable": False,
            }

        fetch = _fetch_fulltext_with_trace(
            self.session,
            europe_fulltext_xml_url=fulltext_url,
            pmcid=pmcid,
            timeout=timeout,
        )
        content = fetch.get("content")
        if not isinstance(content, str) or not content.strip():
            return {
                "status": "error",
                "error": "Full text fetch failed",
                "url": fetch.get("url") or fulltext_url,
                "status_code": fetch.get("status_code"),
                "retryable": fetch.get("status_code") in (408, 429, 500, 502, 503, 504),
                "retrieval_trace": fetch.get("trace") or [],
            }

        raw_out = None
        truncated_raw = False
        if include_raw:
            raw_out = content[:max_raw_chars]
            truncated_raw = len(content) > max_raw_chars

        if output_format == "raw":
            return {
                "status": "success",
                "url": fetch.get("url"),
                "source": fetch.get("source"),
                "format": fetch.get("format"),
                "content_type": fetch.get("content_type"),
                "retrieval_trace": fetch.get("trace") or [],
                "content": content[:max_chars],
                "truncated": len(content) > max_chars,
                "raw": raw_out,
                "raw_truncated": truncated_raw if include_raw else None,
            }

        # output_format == "text"
        try:
            if fetch.get("format") == "xml":
                root = ET.fromstring(content or "")
                text = " ".join("".join(root.itertext()).split())
            else:
                text = _extract_text_from_html(content)
        except ET.ParseError:
            return {
                "status": "error",
                "error": "Full text returned invalid XML",
                "url": fetch.get("url") or fulltext_url,
                "retryable": True,
                "retrieval_trace": fetch.get("trace") or [],
            }

        out_text = text[:max_chars]
        return {
            "status": "success",
            "url": fetch.get("url"),
            "source": fetch.get("source"),
            "format": fetch.get("format"),
            "content_type": fetch.get("content_type"),
            "retrieval_trace": fetch.get("trace") or [],
            "text": out_text,
            "truncated": len(text) > max_chars,
            "raw": raw_out,
            "raw_truncated": truncated_raw if include_raw else None,
        }


@register_tool("EuropePMCRESTTool")
class EuropePMCRESTTool(BaseTool):
    """
    Generic REST tool for Europe PMC API endpoints.
    Supports citations, references, and other article-related endpoints.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/europepmc/webservices/rest"
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})
        self.timeout = 30

    def _build_url(self, arguments):
        """Build URL from endpoint template and arguments, applying schema defaults for missing path params."""
        endpoint = self.tool_config["fields"]["endpoint"]
        url = endpoint

        # Merge schema defaults so optional path params (e.g. {source}) are always substituted
        props = self.tool_config.get("parameter", {}).get("properties", {})
        merged = {k: v.get("default") for k, v in props.items() if "default" in v}
        merged.update(arguments)

        for key, value in merged.items():
            placeholder = f"{{{key}}}"
            if placeholder in url and value is not None:
                url = url.replace(placeholder, str(value))
        return url

    def run(self, arguments):
        """Execute the Europe PMC REST API request."""
        try:
            url = self._build_url(arguments)

            # Extract query parameters (those not in URL path)
            params = {"format": "json"}
            endpoint_template = self.tool_config["fields"]["endpoint"]

            # Add parameters that are not path parameters
            for key, value in arguments.items():
                placeholder = f"{{{key}}}"
                if placeholder not in endpoint_template and value is not None:
                    # Europe PMC expects pageSize, not page_size; limit maps to pageSize too
                    if key in ("page_size", "limit"):
                        params["pageSize"] = value
                    else:
                        params[key] = value

            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                max_attempts=3,
            )

            if response.status_code == 200:
                data = response.json()
                return {"status": "success", "data": data, "url": response.url}
            else:
                return {
                    "status": "error",
                    "error": f"Europe PMC API returned status {response.status_code}",
                    "url": response.url,
                    "status_code": response.status_code,
                    "detail": response.text[:200] if response.text else None,
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Europe PMC API request failed: {str(e)}",
                "url": url if "url" in locals() else None,
            }


@register_tool("EuropePMCStructuredFullTextTool")
class EuropePMCStructuredFullTextTool(BaseTool):
    """
    Retrieve and parse full-text XML from Europe PMC into structured sections
    (title, abstract, introduction, methods, results, discussion, figures,
    tables, references).  Accepts a PMC ID or PMID (auto-resolved via the
    Europe PMC search API).
    """

    _SECTION_KEYWORDS: dict[str, list[str]] = {
        "introduction": ["introduction", "background", "intro"],
        "methods": [
            "methods",
            "materials and methods",
            "material and methods",
            "methodology",
            "experimental",
            "experimental procedures",
            "study design",
            "patients and methods",
        ],
        "results": ["results", "findings"],
        "discussion": ["discussion"],
        "conclusions": ["conclusions", "conclusion", "summary"],
        "acknowledgments": ["acknowledgments", "acknowledgements", "funding"],
    }

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/xml, text/xml;q=0.9, */*;q=0.8",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            }
        )

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _local(tag: str) -> str:
        """Strip XML namespace prefix."""
        return tag.rsplit("}", 1)[-1] if "}" in tag else tag

    @staticmethod
    def _itertext(el) -> str:
        """Collapse all text under *el* into a single whitespace-normalised string."""
        return " ".join("".join(el.itertext()).split())

    def _resolve_pmid_to_pmcid(self, pmid: str) -> str | None:
        """Use Europe PMC search to convert a PMID to a PMCID."""
        url = (
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            f"?query=EXT_ID:{pmid}&format=json&pageSize=1"
        )
        try:
            resp = request_with_retry(
                self.session, "GET", url, timeout=15, max_attempts=2
            )
            if resp.status_code != 200:
                return None
            results = resp.json().get("resultList", {}).get("result", [])
            if results:
                return results[0].get("pmcid") or None
        except Exception:
            pass
        return None

    def _classify_section(self, title_text: str) -> str:
        """Map a section title to a canonical name, or return 'other'."""
        low = title_text.lower().strip()
        for canonical, keywords in self._SECTION_KEYWORDS.items():
            for kw in keywords:
                if low == kw or low.startswith(kw):
                    return canonical
        return "other"

    # ------------------------------------------------------------------
    # XML parsing
    # ------------------------------------------------------------------

    def _parse_article_xml(self, xml_text: str) -> dict:
        """Parse JATS/NLM article XML into structured sections."""
        root = ET.fromstring(xml_text)

        # --- title ---
        title_el = root.find(".//article-title")
        title = self._itertext(title_el) if title_el is not None else None

        # --- abstract ---
        abstract_el = root.find(".//abstract")
        abstract = self._itertext(abstract_el) if abstract_el is not None else None

        # --- body sections ---
        sections: dict[str, list[dict]] = {}
        body = root.find(".//body")
        if body is not None:
            for sec in body.findall("sec"):
                sec_type_attr = sec.attrib.get("sec-type", "")
                title_el = sec.find("title")
                sec_title = self._itertext(title_el) if title_el is not None else ""

                # Classify
                canonical = self._classify_section(sec_title)
                if canonical == "other" and sec_type_attr:
                    # Fallback to sec-type attribute
                    canonical = self._classify_section(sec_type_attr)

                # Skip reference-list and footnote sections
                if sec_type_attr in ("ref-list", "fn-group"):
                    continue

                text = self._itertext(sec)
                entry = {"title": sec_title, "text": text}
                sections.setdefault(canonical, []).append(entry)

        # Flatten single-entry sections into strings for common ones
        structured_body: dict[str, str | list[dict]] = {}
        for key in (
            "introduction",
            "methods",
            "results",
            "discussion",
            "conclusions",
            "acknowledgments",
        ):
            parts = sections.pop(key, [])
            if len(parts) == 1:
                structured_body[key] = parts[0]["text"]
            elif len(parts) > 1:
                structured_body[key] = parts
        # Remaining sections go into 'other_sections'
        other = []
        for key, entries in sections.items():
            other.extend(entries)
        if other:
            structured_body["other_sections"] = other

        # --- figures ---
        figures = []
        for fig in root.iter("fig"):
            fig_id = fig.attrib.get("id", "")
            label_el = fig.find("label")
            label = self._itertext(label_el) if label_el is not None else None
            cap_el = fig.find(".//caption")
            caption = self._itertext(cap_el) if cap_el is not None else None
            if label or caption:
                figures.append({"id": fig_id, "label": label, "caption": caption})

        # --- tables ---
        tables = []
        for tbl in root.iter("table-wrap"):
            tbl_id = tbl.attrib.get("id", "")
            label_el = tbl.find("label")
            label = self._itertext(label_el) if label_el is not None else None
            cap_el = tbl.find(".//caption")
            caption = self._itertext(cap_el) if cap_el is not None else None
            if label or caption:
                tables.append({"id": tbl_id, "label": label, "caption": caption})

        # --- references ---
        references = []
        for ref in root.iter("ref"):
            ref_id = ref.attrib.get("id", "")
            text = self._itertext(ref)
            if text:
                references.append({"id": ref_id, "text": text})

        return {
            "title": title,
            "abstract": abstract,
            "sections": structured_body,
            "figures": figures,
            "tables": tables,
            "references": references,
            "figure_count": len(figures),
            "table_count": len(tables),
            "reference_count": len(references),
        }

    # ------------------------------------------------------------------
    # run
    # ------------------------------------------------------------------

    def run(self, arguments):
        pmcid = arguments.get("pmcid")
        pmid = arguments.get("pmid")

        # Resolve PMID -> PMCID when only PMID is given
        if not pmcid and pmid:
            pmcid = self._resolve_pmid_to_pmcid(str(pmid))
            if not pmcid:
                return {
                    "status": "error",
                    "error": (
                        f"Could not resolve PMID {pmid} to a PMC ID. "
                        "The article may not be in PubMed Central or may not have open-access full text."
                    ),
                }

        if not pmcid:
            return {
                "status": "error",
                "error": "Provide `pmcid` (e.g. 'PMC7096075') or `pmid` (e.g. '32226684').",
            }

        # Normalise PMC ID
        pmcid_norm, _ = _normalize_pmcid(pmcid)
        if not pmcid_norm:
            return {
                "status": "error",
                "error": f"Invalid pmcid format: {pmcid!r}",
            }

        try:
            max_chars = int(arguments.get("max_section_chars", 50000))
        except (TypeError, ValueError):
            max_chars = 50000
        max_chars = max(1000, min(max_chars, 500000))

        # Fetch full text using the shared fallback chain
        fetch = _fetch_fulltext_with_trace(
            self.session,
            europe_fulltext_xml_url=(
                f"https://www.ebi.ac.uk/europepmc/webservices/rest/{pmcid_norm}/fullTextXML"
            ),
            pmcid=pmcid_norm,
            timeout=30,
        )
        content = fetch.get("content")
        if not isinstance(content, str) or not content.strip():
            return {
                "status": "error",
                "error": (
                    f"Full text not available for {pmcid_norm}. "
                    "The article may not be open access."
                ),
                "retrieval_trace": fetch.get("trace") or [],
            }

        # Only XML sources can be structurally parsed
        if fetch.get("format") != "xml":
            return {
                "status": "error",
                "error": (
                    f"Full text for {pmcid_norm} was retrieved as HTML, "
                    "which cannot be structurally parsed into sections. "
                    "Use EuropePMC_get_fulltext for plain-text extraction instead."
                ),
                "retrieval_trace": fetch.get("trace") or [],
            }

        try:
            parsed = self._parse_article_xml(content)
        except ET.ParseError as exc:
            return {
                "status": "error",
                "error": f"XML parse error: {exc}",
                "retrieval_trace": fetch.get("trace") or [],
            }

        # Truncate long section text
        sections = parsed.get("sections", {})
        for key, val in sections.items():
            if isinstance(val, str) and len(val) > max_chars:
                sections[key] = val[:max_chars] + "... [truncated]"
            elif isinstance(val, list):
                for entry in val:
                    if isinstance(entry, dict) and isinstance(entry.get("text"), str):
                        if len(entry["text"]) > max_chars:
                            entry["text"] = (
                                entry["text"][:max_chars] + "... [truncated]"
                            )

        return {
            "status": "success",
            "data": parsed,
            "metadata": {
                "pmcid": pmcid_norm,
                "source": fetch.get("source"),
                "format": fetch.get("format"),
            },
        }
