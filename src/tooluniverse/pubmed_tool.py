import os
import time
import threading
import xml.etree.ElementTree as ET
from typing import Any, Dict
from .base_rest_tool import BaseRESTTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("PubMedRESTTool")
class PubMedRESTTool(BaseRESTTool):
    """Generic REST tool for PubMed E-utilities (efetch, elink).

    Implements rate limiting per NCBI guidelines:
    - Without API key: 3 requests/second
    - With API key: 10 requests/second

    API key is read from environment variable NCBI_API_KEY.
    Get your free key at: https://www.ncbi.nlm.nih.gov/account/
    """

    # Class-level rate limiting (shared across all instances)
    _last_request_time = 0.0
    _rate_limit_lock = threading.Lock()

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Get API key from environment as fallback
        self.default_api_key = os.environ.get("NCBI_API_KEY", "")

    def _get_param_mapping(self) -> Dict[str, str]:
        """Map PubMed E-utilities parameter names."""
        return {
            "limit": "retmax",  # limit -> retmax for E-utilities
        }

    def _enforce_rate_limit(self, has_api_key: bool) -> None:
        """Enforce NCBI E-utilities rate limits.

        Args:
            has_api_key: Whether an API key is provided
        """
        # Rate limits per NCBI guidelines
        # https://www.ncbi.nlm.nih.gov/books/NBK25497/#chapter2.Usage_Guidelines_and_Requiremen
        # Using conservative intervals to avoid rate limit errors:
        # - Without API key: 3 req/sec -> 0.4s interval (more conservative than 0.33s)
        # - With API key: 10 req/sec -> 0.15s interval (more conservative than 0.1s)
        min_interval = 0.15 if has_api_key else 0.4

        with self._rate_limit_lock:
            current_time = time.time()
            time_since_last = current_time - PubMedRESTTool._last_request_time

            if time_since_last < min_interval:
                sleep_time = min_interval - time_since_last
                time.sleep(sleep_time)

            PubMedRESTTool._last_request_time = time.time()

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build E-utilities parameters with special handling."""
        params = {}

        # Start with default params from config (db, dbfrom, cmd, linkname, retmode, rettype)
        for key in ["db", "dbfrom", "cmd", "linkname", "retmode", "rettype"]:
            if key in self.tool_config["fields"]:
                params[key] = self.tool_config["fields"][key]

        # Handle PMID as 'id' parameter (for efetch, elink)
        # PMIDs can be passed as integer or string, coerce to string for API
        if "pmid" in args:
            pmid = args["pmid"]
            if isinstance(pmid, int):
                pmid = str(pmid)
            elif not isinstance(pmid, str):
                raise ValueError(
                    f"pmid must be string or integer, got {type(pmid).__name__}"
                )
            params["id"] = pmid.strip()

        # Handle query as 'term' parameter (for esearch)
        if "query" in args:
            params["term"] = args["query"]

        # Add API key from environment variable
        if self.default_api_key:
            params["api_key"] = self.default_api_key

        # Handle limit/max_results — accept max_results as alias for limit.
        # Use `is not None` so limit=0 is honoured (0 is falsy but valid).
        limit_val = (
            args.get("limit")
            if args.get("limit") is not None
            else args.get("max_results")
        )
        if limit_val is not None:
            params["retmax"] = max(0, int(limit_val))

        # Forward date-range parameters for esearch
        for date_key in ("mindate", "maxdate", "datetype"):
            if date_key in args and args[date_key]:
                params[date_key] = args[date_key]

        # Forward sort parameter for esearch
        # Valid values: pub_date, Author, JournalName, relevance
        if "sort" in args and args["sort"]:
            params["sort"] = args["sort"]

        # Set retmode to json for elink and esearch (easier parsing)
        endpoint = self.tool_config["fields"]["endpoint"]
        if "retmode" not in params and ("elink" in endpoint or "esearch" in endpoint):
            params["retmode"] = "json"

        return params

    def _fetch_summaries(self, pmid_list: list) -> Dict[str, Any]:
        """Fetch article summaries for a list of PMIDs using esummary.

        Args:
            pmid_list: List of PubMed IDs

        Returns:
            Dict with article summaries or error
        """
        if not pmid_list:
            return {"status": "success", "data": []}

        def parse_article(pmid: str, article_data: Dict[str, Any]) -> Dict[str, Any]:
            # Extract author list
            authors = []
            if "authors" in article_data:
                authors = [
                    author.get("name", "") for author in article_data["authors"]
                ][:5]  # Limit to first 5 authors

            # Extract article info
            pub_date = article_data.get("pubdate", "")
            pub_year = pub_date.split()[0] if pub_date else ""

            elocationid = article_data.get("elocationid", "")
            # Extract DOI: handle formats like "doi: 10.1234/abc" and mixed
            # "pii: 2026.02.14.705936. 10.64898/2026.02.14.705936" (preprints).
            doi = ""
            if "doi:" in elocationid:
                # Find the "doi:" token and extract what follows it
                doi_part = elocationid[elocationid.index("doi:") + 4 :].strip()
                # Take the first token that contains '/' (valid DOI structure)
                for token in doi_part.split():
                    if "/" in token:
                        doi = token.rstrip(".")
                        break
            doi = doi or None

            journal = article_data.get(
                "fulljournalname", article_data.get("source", "")
            )
            journal = journal or None

            # Check for PMC ID
            pmcid = ""
            for aid in article_data.get("articleids", []):
                if aid.get("idtype") == "pmc":
                    raw_val = aid["value"]
                    # NCBI esummary returns PMC IDs already prefixed (e.g. "PMC12948714").
                    # Avoid double-prefixing to "PMCPMC12948714".
                    pmcid = raw_val if raw_val.startswith("PMC") else f"PMC{raw_val}"
                    break
            pmcid = pmcid or None

            return {
                "pmid": pmid,
                "title": article_data.get("title", ""),
                "authors": authors,
                "journal": journal,
                "pub_date": pub_date,
                "pub_year": pub_year,
                "doi": doi,
                "pmcid": pmcid,
                "article_type": ", ".join(article_data.get("pubtype", [])),
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "doi_url": f"https://doi.org/{doi}" if doi else None,
                "pmc_url": (
                    f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
                    if pmcid
                    else None
                ),
            }

        try:
            has_api_key = bool(self.default_api_key)
            base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
            summary_url = f"{base}/esummary.fcgi"

            articles = []
            failed_pmids = []
            warnings = []

            # Batch fetch first, then isolate failures.
            chunk_size = 100
            for chunk_start in range(0, len(pmid_list), chunk_size):
                chunk = pmid_list[chunk_start : chunk_start + chunk_size]
                self._enforce_rate_limit(has_api_key)
                params = {
                    "db": "pubmed",
                    "id": ",".join(chunk),
                    "retmode": "json",
                }
                if self.default_api_key:
                    params["api_key"] = self.default_api_key

                response = request_with_retry(
                    self.session,
                    "GET",
                    summary_url,
                    params=params,
                    timeout=self.timeout,
                    max_attempts=3,
                )

                if response.status_code != 200:
                    warnings.append(
                        f"Batch summary fetch failed (HTTP {response.status_code}) for {len(chunk)} PMIDs"
                    )
                    failed_pmids.extend(chunk)
                    continue

                try:
                    data = response.json()
                except ValueError:
                    warnings.append(
                        f"Batch summary fetch returned invalid JSON for {len(chunk)} PMIDs"
                    )
                    failed_pmids.extend(chunk)
                    continue

                if "error" in data:
                    warnings.append(
                        f"NCBI API error on batch summary fetch: {data.get('error')}"
                    )
                    failed_pmids.extend(chunk)
                    continue

                result = data.get("result", {})
                for pmid in chunk:
                    article_data = result.get(pmid)
                    if article_data:
                        articles.append(parse_article(pmid, article_data))
                    else:
                        failed_pmids.append(pmid)

            # Retry failures one-by-one to isolate transient per-ID issues.
            retry_failed_pmids = []
            for pmid in failed_pmids:
                self._enforce_rate_limit(has_api_key)
                params = {"db": "pubmed", "id": pmid, "retmode": "json"}
                if self.default_api_key:
                    params["api_key"] = self.default_api_key

                try:
                    response = request_with_retry(
                        self.session,
                        "GET",
                        summary_url,
                        params=params,
                        timeout=self.timeout,
                        max_attempts=2,
                    )
                except Exception as error:
                    retry_failed_pmids.append((pmid, str(error)))
                    continue

                if response.status_code != 200:
                    retry_failed_pmids.append((pmid, f"HTTP {response.status_code}"))
                    continue

                try:
                    data = response.json()
                    article_data = data.get("result", {}).get(pmid)
                    if article_data:
                        articles.append(parse_article(pmid, article_data))
                    else:
                        retry_failed_pmids.append((pmid, "summary missing for PMID"))
                except Exception as error:
                    retry_failed_pmids.append((pmid, str(error)))

            if retry_failed_pmids:
                warnings.append(
                    f"Failed to fetch summaries for {len(retry_failed_pmids)} PMIDs after per-ID retry"
                )

            if not articles:
                error_msg = (
                    warnings[0] if warnings else "Failed to fetch article summaries"
                )
                return {"status": "error", "error": error_msg}

            result = {"status": "success", "data": articles}
            if warnings:
                result["warning"] = "; ".join(warnings)
            return result

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to fetch article summaries: {str(e)}",
            }

    def _parse_efetch_xml(self, response) -> Dict[str, Any]:
        """Parse PubMed efetch XML into structured article data."""
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError:
            return {"status": "success", "data": response.text, "url": response.url}

        def _text(el, path, default=""):
            found = el.find(path) if el is not None else None
            return found.text if found is not None and found.text else default

        def _itertext(el, path):
            found = el.find(path) if el is not None else None
            return "".join(found.itertext()) if found is not None else ""

        def _parse_article(article_el):
            cit = article_el.find("MedlineCitation")
            art = cit.find("Article") if cit is not None else None
            if cit is None or art is None:
                return None

            pmid = _text(cit, "PMID")
            title = _itertext(art, "ArticleTitle")

            # Abstract: join labeled sections
            abstract_parts = []
            for at in art.findall("Abstract/AbstractText") or []:
                label, text = at.get("Label", ""), "".join(at.itertext()).strip()
                if text:
                    abstract_parts.append(f"{label}: {text}" if label else text)
            abstract = " ".join(abstract_parts)

            # Authors (first 10)
            authors = []
            for au in (art.findall("AuthorList/Author") or [])[:10]:
                last, fore = au.findtext("LastName", ""), au.findtext("ForeName", "")
                name = f"{last} {fore}".strip() if last else fore
                if not name:
                    continue
                entry = {"name": name}
                aff = _text(au, ".//Affiliation")
                if aff:
                    entry["affiliation"] = aff
                authors.append(entry)

            journal_el = art.find("Journal")
            journal = _text(journal_el, "Title") or _text(journal_el, "ISOAbbreviation")

            doi = next(
                (
                    eid.text
                    for eid in art.findall("ELocationID")
                    if eid.get("EIdType") == "doi" and eid.text
                ),
                "",
            )

            pd = art.find(".//PubDate")
            pub_year = _text(pd, "Year")
            pub_date = " ".join(
                filter(None, [pub_year, _text(pd, "Month"), _text(pd, "Day")])
            )

            mesh = [
                d.text
                for d in cit.findall("MeshHeadingList/MeshHeading/DescriptorName")
                if d.text
            ]
            pub_types = [pt.text for pt in art.findall(".//PublicationType") if pt.text]

            return {
                "pmid": pmid,
                "title": title,
                "abstract": abstract or None,
                "authors": authors,
                "journal": journal or None,
                "pub_date": pub_date,
                "pub_year": pub_year,
                "doi": doi or None,
                "doi_url": f"https://doi.org/{doi}" if doi else None,
                "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                "mesh_terms": mesh or None,
                "publication_types": pub_types or None,
            }

        articles = [
            a
            for a in (_parse_article(el) for el in root.findall(".//PubmedArticle"))
            if a
        ]
        data = articles[0] if len(articles) == 1 else articles
        result = {"status": "success", "data": data, "url": response.url}
        if len(articles) != 1:
            result["count"] = len(articles)
        return result

    def _fetch_abstracts(self, pmid_list: list[str]) -> Dict[str, str]:
        """Best-effort abstract fetch via efetch XML for a list of PMIDs."""
        pmids = [str(p).strip() for p in (pmid_list or []) if str(p).strip()]
        if not pmids:
            return {}

        has_api_key = bool(self.default_api_key)
        base = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        url = f"{base}/efetch.fcgi"

        # Batch efetch; keep payload bounded.
        self._enforce_rate_limit(has_api_key)
        params: Dict[str, Any] = {
            "db": "pubmed",
            "id": ",".join(pmids[:200]),
            "retmode": "xml",
        }
        if self.default_api_key:
            params["api_key"] = self.default_api_key

        resp = request_with_retry(
            self.session,
            "GET",
            url,
            params=params,
            timeout=self.timeout,
            max_attempts=3,
        )
        if resp.status_code != 200:
            return {}

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return {}

        abstracts: Dict[str, str] = {}
        for pubmed_article in root.findall(".//PubmedArticle"):
            pmid_el = pubmed_article.find(".//MedlineCitation/PMID")
            pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""
            if not pmid:
                continue
            parts: list[str] = []
            for at in pubmed_article.findall(
                ".//MedlineCitation/Article/Abstract/AbstractText"
            ):
                # PubMed AbstractText often contains inline tags (e.g. <i/>).
                # Using itertext() avoids truncating at the first child element.
                text = " ".join("".join(at.itertext()).split())
                if text:
                    parts.append(text)
            if parts:
                abstracts[pmid] = "\n".join(parts)
        return abstracts

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        PubMed E-utilities need special handling for direct endpoint URLs.
        Enforces NCBI rate limits to prevent API errors.
        """
        url = None
        try:
            # Enforce rate limiting before making request
            has_api_key = bool(self.default_api_key)
            self._enforce_rate_limit(has_api_key)

            endpoint = self.tool_config["fields"]["endpoint"]
            params = self._build_params(arguments)

            response = request_with_retry(
                self.session,
                "GET",
                endpoint,
                params=params,
                timeout=self.timeout,
                max_attempts=3,
            )

            if response.status_code != 200:
                return {
                    "status": "error",
                    "error": "PubMed API error",
                    "url": response.url,
                    "status_code": response.status_code,
                    "detail": (response.text or "")[:500],
                }

            # Try JSON first (elink, esearch)
            try:
                data = response.json()

                # Check for API errors in response
                if "ERROR" in data:
                    error_msg = data.get("ERROR", "Unknown API error")
                    return {
                        "status": "error",
                        "data": f"NCBI API error: {error_msg[:200]}",
                        "url": response.url,
                    }

                # For esearch responses, extract ID list and fetch summaries
                if "esearchresult" in data:
                    esearch_result = data.get("esearchresult", {})
                    id_list = esearch_result.get("idlist", [])

                    # If this is a search request (has 'query' in arguments),
                    # fetch article summaries and return as list
                    if "query" in arguments and id_list:
                        summary_result = self._fetch_summaries(id_list)

                        if summary_result["status"] == "error":
                            # Preserve stable return type: always return a list of
                            # article-shaped objects. If summaries fail entirely,
                            # return minimal stubs with PMID + URL so downstream
                            # agents can still act on the result.
                            import logging

                            _logger = logging.getLogger(__name__)
                            _logger.warning(
                                f"Failed to fetch article summaries: "
                                f"{summary_result.get('error')}"
                            )
                            limit = arguments.get("limit")
                            try:
                                limit = int(limit) if limit is not None else None
                            except (TypeError, ValueError):
                                limit = None

                            stub_items = [
                                {
                                    "pmid": str(pmid),
                                    "title": None,
                                    "authors": [],
                                    "journal": None,
                                    "pub_date": None,
                                    "pub_year": None,
                                    "doi": None,
                                    "pmcid": None,
                                    "article_type": None,
                                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                    "partial": True,
                                    "warning": summary_result.get(
                                        "error", "Failed to fetch summaries"
                                    ),
                                }
                                for pmid in id_list
                            ]
                            return stub_items[:limit] if limit else stub_items

                        articles = summary_result["data"]
                        warning = summary_result.get("warning")
                        if warning:
                            for a in articles:
                                if isinstance(a, dict):
                                    a["partial"] = True
                                    a["warning"] = warning

                        include_abstract = bool(arguments.get("include_abstract", True))
                        if include_abstract and articles:
                            pmids = [
                                str(a.get("pmid")).strip()
                                for a in articles
                                if isinstance(a, dict) and a.get("pmid")
                            ]
                            abstract_map = self._fetch_abstracts(pmids)
                            if abstract_map:
                                for a in articles:
                                    if not isinstance(a, dict):
                                        continue
                                    pmid = str(a.get("pmid") or "").strip()
                                    if pmid and abstract_map.get(pmid):
                                        a["abstract"] = abstract_map.get(pmid)
                                        a["abstract_source"] = "PubMed"
                            else:
                                for a in articles:
                                    if isinstance(a, dict) and "abstract" not in a:
                                        a["abstract"] = None
                                        a["abstract_source"] = None

                        return {
                            "status": "success",
                            "data": articles,
                            "metadata": {
                                "count": len(articles),
                                "total": int(
                                    esearch_result.get("count", len(articles))
                                ),
                                "query": arguments.get("query"),
                                "source": "PubMed",
                            },
                        }

                    # Return just IDs for non-search requests (as list)
                    return id_list

                # For elink responses with LinkOut URLs (llinks command)
                if "linksets" in data:
                    linksets = data.get("linksets", [])
                    # Check for empty linksets with errors
                    if not linksets or (linksets and len(linksets) == 0):
                        return {
                            "status": "success",
                            "data": [],
                            "count": 0,
                            "url": response.url,
                        }

                    if linksets and len(linksets) > 0:
                        linkset = linksets[0]
                        # Extract linked IDs
                        if "linksetdbs" in linkset:
                            linksetdbs = linkset.get("linksetdbs", [])
                            if linksetdbs and len(linksetdbs) > 0:
                                links = linksetdbs[0].get("links", [])
                                try:
                                    limit = (
                                        int(arguments.get("limit"))
                                        if arguments.get("limit") is not None
                                        else None
                                    )
                                except (TypeError, ValueError):
                                    limit = None
                                if limit is not None:
                                    links = links[:limit]

                                # Enrich with article metadata
                                pmids = [
                                    str(lk["id"] if isinstance(lk, dict) else lk)
                                    for lk in links
                                ]
                                scores = {
                                    str(lk["id"]): lk.get("score")
                                    for lk in links
                                    if isinstance(lk, dict)
                                }
                                summary = self._fetch_summaries(pmids)
                                if summary.get("status") == "success" and summary.get(
                                    "data"
                                ):
                                    for item in summary["data"]:
                                        score = (
                                            scores.get(str(item.get("pmid", "")))
                                            if isinstance(item, dict)
                                            else None
                                        )
                                        if score is not None:
                                            item["relevance_score"] = score
                                    links = summary["data"]
                                return {
                                    "status": "success",
                                    "data": links,
                                    "count": len(links),
                                    "url": response.url,
                                }
                        # Extract LinkOut URLs (idurllist)
                        elif "idurllist" in linkset:
                            return {
                                "status": "success",
                                "data": linkset.get("idurllist", {}),
                                "url": response.url,
                            }
                        else:
                            # Linkset exists but no linksetdbs or idurllist = no results
                            return {
                                "status": "success",
                                "data": [],
                                "count": 0,
                                "url": response.url,
                            }

                # For elink responses with LinkOut URLs (llinks returns direct idurllist)
                if "idurllist" in data:
                    return {
                        "status": "success",
                        "data": data.get("idurllist", []),
                        "url": response.url,
                    }

                return {
                    "status": "success",
                    "data": data,
                    "url": response.url,
                }
            except Exception:
                # For XML responses (efetch), parse into structured data
                return self._parse_efetch_xml(response)

        except Exception as e:
            return {
                "status": "error",
                "error": f"PubMed API error: {str(e)}",
                "url": url,
            }
