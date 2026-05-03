#!/usr/bin/env python3
"""
PMC (PubMed Central) Tool for searching full-text biomedical literature.

PMC is the free full-text archive of biomedical and life sciences journal
literature at the U.S. National Institutes of Health's National Library of
Medicine. This tool provides access to millions of full-text articles.
"""

import requests
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional, Tuple
from .base_tool import BaseTool
from .http_utils import request_with_retry
from .tool_registry import register_tool


@register_tool("PMCTool")
class PMCTool(BaseTool):
    """Tool for searching PMC full-text biomedical literature."""

    def __init__(self, tool_config=None):
        super().__init__(tool_config)
        self.base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ToolUniverse/1.0",
                "Accept": "application/json, application/xml;q=0.9, */*;q=0.8",
            }
        )

    def _normalize_pmcid(self, pmc_id: str) -> str:
        pmc_id = (pmc_id or "").strip()
        if not pmc_id:
            return ""
        return pmc_id if pmc_id.upper().startswith("PMC") else f"PMC{pmc_id}"

    def _extract_year_from_date(self, date_str: Optional[str]) -> Optional[str]:
        if not date_str:
            return None
        s = str(date_str).strip()
        if len(s) >= 4 and s[:4].isdigit():
            return s[:4]
        for part in s.split():
            if len(part) == 4 and part.isdigit():
                return part
        return None

    def _parse_esummary_item(self, item: ET.Element) -> Any:
        item_type = (item.attrib.get("Type") or "").lower()
        if item_type == "list":
            children = [c for c in item.findall("Item") if isinstance(c.tag, str)]
            child_names = [c.attrib.get("Name") for c in children]
            if all(child_names) and len(set(child_names)) == len(child_names):
                return {
                    n: self._parse_esummary_item(c)
                    for n, c in zip(child_names, children)
                }
            return [self._parse_esummary_item(c) for c in children]
        return (item.text or "").strip()

    def _parse_esummary_xml(self, xml_text: str) -> Dict[str, Dict[str, Any]]:
        """Parse NCBI E-utilities esummary XML into a dict keyed by numeric PMC id."""
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return {}

        results: Dict[str, Dict[str, Any]] = {}
        for docsum in root.findall(".//DocSum"):
            pmc_numeric_id = (docsum.findtext("Id") or "").strip()
            if not pmc_numeric_id:
                continue
            parsed: Dict[str, Any] = {}
            for item in docsum.findall("Item"):
                name = item.attrib.get("Name")
                if not name:
                    continue
                parsed[name] = self._parse_esummary_item(item)
            results[pmc_numeric_id] = parsed
        return results

    def _build_paper_from_summary(
        self, pmc_numeric_id: str, items: Dict[str, Any]
    ) -> Dict[str, Any]:
        article_ids = items.get("ArticleIds", {})
        if not isinstance(article_ids, dict):
            article_ids = {}

        pmcid = self._normalize_pmcid(
            article_ids.get("pmcid") or article_ids.get("pmc") or pmc_numeric_id
        )
        # NCBI esummary XML uses "pmid" as the key (not "pubmed")
        raw_pmid = article_ids.get("pmid") or article_ids.get("pubmed")
        pmid = raw_pmid if isinstance(raw_pmid, str) else None
        doi = (
            article_ids.get("doi") if isinstance(article_ids.get("doi"), str) else None
        )

        authors: List[str] = []
        author_list = items.get("AuthorList")
        if isinstance(author_list, list):
            authors = [a for a in author_list if isinstance(a, str) and a.strip()]
        elif isinstance(author_list, dict):
            # Some formats use {"Author": ["..."]} or {"Author": "..."}.
            author_value = author_list.get("Author")
            if isinstance(author_value, list):
                authors = [a for a in author_value if isinstance(a, str) and a.strip()]
            elif isinstance(author_value, str) and author_value.strip():
                authors = [author_value.strip()]

        pub_date = (
            items.get("PubDate") if isinstance(items.get("PubDate"), str) else None
        )
        year = self._extract_year_from_date(pub_date)

        citations_raw = items.get("PmcRefCount", 0)
        try:
            citations = int(citations_raw) if citations_raw not in (None, "") else 0
        except (TypeError, ValueError):
            citations = 0

        title = items.get("Title") if isinstance(items.get("Title"), str) else None
        venue = items.get("Source") if isinstance(items.get("Source"), str) else None

        pub_types = items.get("PubType")
        if isinstance(pub_types, list):
            article_type = (
                ", ".join([p for p in pub_types if isinstance(p, str) and p.strip()])
                or None
            )
        elif isinstance(pub_types, str) and pub_types.strip():
            article_type = pub_types.strip()
        else:
            article_type = None

        return {
            "title": title or "Title not available",
            "abstract": None,  # PMC esummary does not include abstract; avoid misleading sentinels.
            "authors": authors,
            "year": year,
            "pmc_id": pmcid,
            "pmid": pmid,
            "doi": doi,
            "doi_url": f"https://doi.org/{doi}" if doi else None,
            "url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/"
            if pmcid
            else None,
            "pdf_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmcid}/pdf/"
            if pmcid
            else None,
            "venue": venue,
            "open_access": True,
            "source": "PMC",
            "article_type": article_type,
            "citations": citations,
            "data_quality": {
                "has_authors": bool(authors),
                "has_abstract": False,
                "has_year": bool(year),
                "has_pmid": bool(pmid),
                "has_doi": bool(doi),
                "has_url": bool(pmcid),
                "has_venue": bool(venue),
            },
        }

    def _fetch_pubmed_abstracts(self, pmids: List[str]) -> Dict[str, str]:
        """Best-effort: fetch PubMed abstracts for PMIDs via efetch XML."""
        pmids = [str(p).strip() for p in (pmids or []) if str(p).strip()]
        if not pmids:
            return {}

        # NCBI allows batching; keep it small to avoid large XML.
        base = f"{self.base_url}/efetch.fcgi"
        params = {"db": "pubmed", "id": ",".join(pmids[:200]), "retmode": "xml"}
        resp = request_with_retry(
            self.session, "GET", base, params=params, timeout=30, max_attempts=3
        )
        if resp.status_code != 200:
            return {}

        try:
            root = ET.fromstring(resp.text)
        except ET.ParseError:
            return {}

        abstract_by_pmid: Dict[str, str] = {}

        for pubmed_article in root.findall(".//PubmedArticle"):
            pmid_el = pubmed_article.find(".//MedlineCitation/PMID")
            pmid = (pmid_el.text or "").strip() if pmid_el is not None else ""
            if not pmid:
                continue

            abstract_texts = []
            for at in pubmed_article.findall(
                ".//MedlineCitation/Article/Abstract/AbstractText"
            ):
                text = " ".join("".join(at.itertext()).split())
                if text:
                    abstract_texts.append(text)
            if abstract_texts:
                abstract_by_pmid[pmid] = "\n".join(abstract_texts)

        return abstract_by_pmid

    def _search(
        self,
        query: str,
        limit: int = 10,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        article_type: Optional[str] = None,
        include_abstract: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Search for papers using PMC API.

        Args:
            query: Search query
            limit: Maximum number of results
            date_from: Start date filter (YYYY/MM/DD)
            date_to: End date filter (YYYY/MM/DD)
            article_type: Article type filter (e.g., 'research-article', 'review')

        Returns
            List of paper dictionaries
        """
        try:
            # Step 1: Search PMC for article IDs
            search_params = {
                "db": "pmc",
                "term": query,
                "retmax": min(limit, 100),  # NCBI API max limit
                "retmode": "json",
                "sort": "relevance",
            }

            # Add date filters if provided
            if date_from or date_to:
                date_filter = []
                if date_from:
                    date_filter.append(
                        f"({date_from}[PDAT]:{date_to or '3000/12/31'}[PDAT])"
                    )
                else:
                    date_filter.append(f"(:{date_to}[PDAT])")
                search_params["term"] += f" AND {' '.join(date_filter)}"

            # Add article type filter if provided
            if article_type:
                search_params["term"] += f" AND {article_type}[PT]"

            # Make search request
            search_response = request_with_retry(
                self.session,
                "GET",
                f"{self.base_url}/esearch.fcgi",
                params=search_params,
                timeout=30,
                max_attempts=3,
            )
            search_response.raise_for_status()

            search_data = search_response.json()
            pmc_ids = search_data.get("esearchresult", {}).get("idlist", [])

            if not pmc_ids:
                return []

            # Step 2: Get detailed information for each article.
            # Note: NCBI esummary JSON for db=pmc is flaky (frequent HTTP 500).
            # Use XML and parse DocSum instead.
            summary_params = {"db": "pmc", "id": ",".join(pmc_ids), "retmode": "xml"}
            summary_response = request_with_retry(
                self.session,
                "GET",
                f"{self.base_url}/esummary.fcgi",
                params=summary_params,
                timeout=30,
                max_attempts=3,
            )
            summary_response.raise_for_status()

            summary_map = self._parse_esummary_xml(summary_response.text)
            results: List[Dict[str, Any]] = []

            for pmc_numeric_id in pmc_ids:
                items = summary_map.get(str(pmc_numeric_id), {})
                results.append(
                    self._build_paper_from_summary(str(pmc_numeric_id), items)
                )

            if include_abstract:
                pmids = [
                    str(r.get("pmid")).strip()
                    for r in results
                    if isinstance(r, dict) and r.get("pmid")
                ]
                if pmids:
                    abstract_map = self._fetch_pubmed_abstracts(pmids)
                    if abstract_map:
                        for r in results:
                            if not isinstance(r, dict):
                                continue
                            pmid = r.get("pmid")
                            if pmid and abstract_map.get(str(pmid)):
                                r["abstract"] = abstract_map.get(str(pmid))
                                r["abstract_source"] = "PubMed"
                                if isinstance(r.get("data_quality"), dict):
                                    r["data_quality"]["has_abstract"] = True

                # Warn when no PMIDs are available to fetch abstracts
                papers_without_abstract = sum(
                    1 for r in results if isinstance(r, dict) and not r.get("abstract")
                )
                if papers_without_abstract == len(results):
                    for r in results:
                        if isinstance(r, dict):
                            r["abstract_note"] = (
                                "Abstracts unavailable: PMC esummary did not return "
                                "PubMed IDs for these articles. Try PubMed_search_articles "
                                "for abstract access."
                            )

            return results[:limit]

        except requests.exceptions.RequestException as e:
            return [
                {
                    "title": "Error",
                    "abstract": None,
                    "authors": [],
                    "year": None,
                    "url": None,
                    "source": "PMC",
                    "error": f"PMC API request failed: {str(e)}",
                    "retryable": True,
                }
            ]
        except Exception as e:
            return [
                {
                    "title": "Error",
                    "abstract": None,
                    "authors": [],
                    "year": None,
                    "url": None,
                    "source": "PMC",
                    "error": f"PMC API error: {str(e)}",
                    "retryable": False,
                }
            ]

    def _extract_authors(self, authors: List[Dict]) -> List[str]:
        """Extract author names from PMC API response."""
        if not authors:
            return []

        author_names = []
        for author in authors:
            name = author.get("name", "")
            if name:
                author_names.append(name)

        return author_names

    def _extract_year(self, pubdate: str) -> str:
        """Extract year from publication date."""
        if not pubdate:
            return "Unknown"

        try:
            # PMC API returns dates in various formats
            # Extract year from the beginning of the string
            return pubdate[:4]
        except Exception:
            return "Unknown"

    def run(self, tool_arguments) -> List[Dict[str, Any]]:
        """
        Execute the PMC search.

        Args:
            tool_arguments: Dictionary containing search parameters

        Returns
            List of paper dictionaries
        """
        query = tool_arguments.get("query", "")
        if not query:
            return [
                {
                    "title": "Error",
                    "abstract": None,
                    "authors": [],
                    "year": None,
                    "url": None,
                    "source": "PMC",
                    "error": "Query parameter is required",
                    "retryable": False,
                }
            ]

        # Accept common aliases for NCBI-style tools.
        limit = tool_arguments.get("limit")
        if limit is None:
            limit = tool_arguments.get("retmax", 10)
        date_from = tool_arguments.get("date_from")
        date_to = tool_arguments.get("date_to")
        article_type = tool_arguments.get("article_type")
        include_abstract = bool(tool_arguments.get("include_abstract", False))

        return self._search(
            query=query,
            limit=limit,
            date_from=date_from,
            date_to=date_to,
            article_type=article_type,
            include_abstract=include_abstract,
        )
