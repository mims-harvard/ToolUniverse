"""
Clinical Society Guideline Tools (ADA, AHA/ACC, NCCN).

Provides PubMed-based searches for clinical practice guidelines from
the American Diabetes Association (ADA), American Heart Association (AHA),
American College of Cardiology (ACC), and National Comprehensive Cancer
Network (NCCN).  Also provides web scraping for NCCN patient guidelines.
"""

import io
import os
import re
import time
import xml.etree.ElementTree as ET

import pdfplumber
import requests
from bs4 import BeautifulSoup

from .base_tool import BaseTool
from .tool_registry import register_tool

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def _eutils_params(extra=None):
    """Return base params with optional NCBI API key."""
    params = {}
    api_key = os.environ.get("NCBI_API_KEY")
    if api_key:
        params["api_key"] = api_key
    if extra:
        params.update(extra)
    return params


def _rate_limit():
    """Respect NCBI rate limit (3 requests/sec without key, 10 with key)."""
    if os.environ.get("NCBI_API_KEY"):
        time.sleep(0.15)
    else:
        time.sleep(0.4)


def _pubmed_search(query, limit=10, sort="date"):
    """Search PubMed and return list of PMIDs."""
    params = _eutils_params(
        {
            "db": "pubmed",
            "term": query,
            "retmode": "json",
            "retmax": limit,
            "sort": sort,
        }
    )
    resp = requests.get(f"{EUTILS_BASE}/esearch.fcgi", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    return data.get("esearchresult", {}).get("idlist", [])


def _pubmed_summaries(pmids):
    """Fetch PubMed esummary for a list of PMIDs. Returns dict keyed by PMID."""
    if not pmids:
        return {}
    params = _eutils_params(
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "json",
        }
    )
    resp = requests.get(f"{EUTILS_BASE}/esummary.fcgi", params=params, timeout=20)
    resp.raise_for_status()
    data = resp.json()
    result = data.get("result", {})
    # Remove the 'uids' key if present
    result.pop("uids", None)
    return result


def _pubmed_abstracts(pmids):
    """Fetch abstracts for PMIDs using efetch XML. Returns dict PMID -> abstract."""
    if not pmids:
        return {}
    params = _eutils_params(
        {
            "db": "pubmed",
            "id": ",".join(pmids),
            "retmode": "xml",
            "rettype": "abstract",
        }
    )
    resp = requests.get(f"{EUTILS_BASE}/efetch.fcgi", params=params, timeout=30)
    resp.raise_for_status()

    abstracts = {}
    try:
        root = ET.fromstring(resp.content)
        for article in root.findall(".//PubmedArticle"):
            pmid_elem = article.find(".//PMID")
            if pmid_elem is None:
                continue
            pmid = pmid_elem.text
            # Collect all AbstractText elements (may have multiple for structured)
            abstract_parts = []
            for at in article.findall(".//AbstractText"):
                label = at.get("Label", "")
                # Also gather tail text from child elements
                full = ET.tostring(at, encoding="unicode", method="text").strip()
                if label:
                    abstract_parts.append(f"{label}: {full}")
                else:
                    abstract_parts.append(full)
            abstracts[pmid] = " ".join(abstract_parts) if abstract_parts else ""
    except ET.ParseError:
        pass
    return abstracts


def _build_article_result(pmid, summary, abstract=""):
    """Build a standardized article result dict from esummary + abstract."""
    articleids = summary.get("articleids", [])
    pmc_ids = [a["value"] for a in articleids if a.get("idtype") == "pmc"]
    doi_ids = [a["value"] for a in articleids if a.get("idtype") == "doi"]

    pmc_id = pmc_ids[0] if pmc_ids else None
    doi = (
        doi_ids[0]
        if doi_ids
        else summary.get("elocationid", "").replace("doi: ", "")
        if "doi:" in summary.get("elocationid", "")
        else ""
    )

    # Extract year from pubdate
    pubdate = summary.get("pubdate", "")
    year_match = re.search(r"(\d{4})", pubdate)
    year = int(year_match.group(1)) if year_match else None

    return {
        "title": summary.get("title", ""),
        "abstract": abstract[:2000] if abstract else "",
        "year": year,
        "pmid": pmid,
        "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        "pmc_url": f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
        if pmc_id
        else None,
        "doi": doi,
        "journal": summary.get("source", ""),
        "publication_date": pubdate,
    }


def _search_and_fetch(query, limit=5):
    """Combined search + summary + abstract fetch pipeline."""
    pmids = _pubmed_search(query, limit=limit)
    if not pmids:
        return []

    _rate_limit()
    summaries = _pubmed_summaries(pmids)

    _rate_limit()
    abstracts = _pubmed_abstracts(pmids)

    results = []
    for pmid in pmids:
        if pmid not in summaries:
            continue
        article = _build_article_result(pmid, summaries[pmid], abstracts.get(pmid, ""))
        results.append(article)
    return results


# ---------------------------------------------------------------------------
# ADA Tools
# ---------------------------------------------------------------------------


@register_tool("ADAStandardsTool")
class ADAStandardsTool(BaseTool):
    """
    American Diabetes Association (ADA) Standards of Care tools.

    Supports three operations:
    - list_sections: List all sections of the current ADA Standards of Care
    - search: Search ADA guidelines by topic via PubMed
    - get_section: Fetch content of a specific ADA Standards section via PMC
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments):
        try:
            op = self.operation
            if op == "list_sections":
                return self._list_sections(arguments)
            elif op == "search":
                return self._search(arguments)
            elif op == "get_section":
                return self._get_section(arguments)
            return {"error": f"Unknown operation: {op}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
        except Exception as e:
            return {"error": f"Error: {e}"}

    def _list_sections(self, arguments):
        """List all sections of the current ADA Standards of Care via PubMed."""
        year = arguments.get("year", 2026)
        query = (
            f'"Standards of Care in Diabetes-{year}" AND '
            f'"American Diabetes Association"[Corporate Author]'
        )
        pmids = _pubmed_search(query, limit=25, sort="date")
        if not pmids:
            return []

        _rate_limit()
        summaries = _pubmed_summaries(pmids)

        sections = []
        for pmid in pmids:
            if pmid not in summaries:
                continue
            s = summaries[pmid]
            title = s.get("title", "")
            articleids = s.get("articleids", [])
            pmc_ids = [a["value"] for a in articleids if a.get("idtype") == "pmc"]
            doi_ids = [a["value"] for a in articleids if a.get("idtype") == "doi"]

            # Extract section number from title like "9. Pharmacologic..."
            sec_match = re.match(r"(\d+)\.\s", title)
            section_number = int(sec_match.group(1)) if sec_match else None

            sections.append(
                {
                    "title": title,
                    "section_number": section_number,
                    "pmid": pmid,
                    "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                    "pmc_url": (
                        f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_ids[0]}/"
                        if pmc_ids
                        else None
                    ),
                    "doi": doi_ids[0] if doi_ids else None,
                    "year": year,
                }
            )

        # Sort by section number (numbered sections first, then unnumbered)
        sections.sort(
            key=lambda x: (x["section_number"] is None, x["section_number"] or 0)
        )
        return sections

    def _search(self, arguments):
        """Search ADA guidelines by topic using PubMed."""
        query_text = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        if not query_text:
            return {"error": "query parameter is required"}

        pubmed_query = (
            f'("American Diabetes Association"[Corporate Author]) AND ({query_text})'
        )
        return _search_and_fetch(pubmed_query, limit=limit)

    def _get_section(self, arguments):
        """Fetch content of a specific ADA Standards section via PMC."""
        pmid = arguments.get("pmid", "")
        if not pmid:
            return {"error": "pmid parameter is required"}

        pmid = str(pmid)

        # First get summary to find PMC ID
        summaries = _pubmed_summaries([pmid])
        if pmid not in summaries:
            return {"error": f"PMID {pmid} not found"}

        summary = summaries[pmid]
        articleids = summary.get("articleids", [])
        pmc_ids = [a["value"] for a in articleids if a.get("idtype") == "pmc"]

        _rate_limit()
        # Fetch abstract
        abstracts = _pubmed_abstracts([pmid])
        abstract = abstracts.get(pmid, "")

        result = {
            "title": summary.get("title", ""),
            "pmid": pmid,
            "abstract": abstract,
            "journal": summary.get("source", ""),
            "publication_date": summary.get("pubdate", ""),
            "pmc_url": None,
            "full_text_snippet": None,
        }

        # Try to fetch full text from PMC if available
        if pmc_ids:
            pmc_id = pmc_ids[0]
            result["pmc_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
            _rate_limit()
            try:
                ft_url = f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmc_id}/unicode"
                ft_resp = requests.get(ft_url, timeout=30)
                if ft_resp.status_code == 200:
                    ft_data = ft_resp.json()
                    # Extract text passages
                    passages = []
                    for doc in ft_data.get("documents", []):
                        for passage in doc.get("passages", []):
                            text = passage.get("text", "")
                            section = passage.get("infons", {}).get("section_type", "")
                            ptype = passage.get("infons", {}).get("type", "")
                            if (
                                text
                                and ptype != "ref"
                                and section not in ("REF", "COMP_INT")
                            ):
                                passages.append(text)
                    if passages:
                        # Return first 5000 chars of combined passages
                        combined = "\n\n".join(passages)
                        result["full_text_snippet"] = combined[:5000]
            except Exception:
                pass  # PMC full text is optional

        return result


# ---------------------------------------------------------------------------
# AHA/ACC Tools
# ---------------------------------------------------------------------------


@register_tool("AHAACCGuidelineTool")
class AHAACCGuidelineTool(BaseTool):
    """
    American Heart Association (AHA) and American College of Cardiology (ACC)
    guideline tools. Uses PubMed to search and list clinical practice guidelines.

    Supports three operations:
    - search: Search AHA/ACC guidelines by topic
    - list_aha: List recent AHA guidelines
    - list_acc: List recent ACC guidelines
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "search")

    def run(self, arguments):
        try:
            op = self.operation
            if op == "search":
                return self._search(arguments)
            elif op == "list_aha":
                return self._list_org(arguments, "American Heart Association")
            elif op == "list_acc":
                return self._list_org(arguments, "American College of Cardiology")
            elif op == "get_guideline":
                return self._get_guideline(arguments)
            return {"error": f"Unknown operation: {op}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
        except Exception as e:
            return {"error": f"Error: {e}"}

    def _search(self, arguments):
        """Search AHA/ACC guidelines by topic."""
        query_text = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        year_from = arguments.get("year_from")

        if not query_text:
            return {"error": "query parameter is required"}

        date_filter = ""
        if year_from:
            date_filter = (
                f' AND ("{year_from}"[Date - Publication] : "3000"[Date - Publication])'
            )

        pubmed_query = (
            f'(("American Heart Association"[Corporate Author] OR '
            f'"American College of Cardiology"[Corporate Author]) AND '
            f'("guideline"[Title] OR "practice guideline"[Publication Type])) '
            f"AND ({query_text}){date_filter}"
        )
        return _search_and_fetch(pubmed_query, limit=limit)

    def _get_guideline(self, arguments):
        """Fetch full text of an AHA/ACC guideline from PMC by PMID."""
        pmid = str(arguments.get("pmid", ""))
        if not pmid:
            return {"error": "pmid parameter is required"}

        summaries = _pubmed_summaries([pmid])
        if pmid not in summaries:
            return {"error": f"PMID {pmid} not found in PubMed"}

        summary = summaries[pmid]
        articleids = summary.get("articleids", [])
        pmc_ids = [a["value"] for a in articleids if a.get("idtype") == "pmc"]

        _rate_limit()
        abstracts = _pubmed_abstracts([pmid])

        result = {
            "title": summary.get("title", ""),
            "pmid": pmid,
            "abstract": abstracts.get(pmid, ""),
            "journal": summary.get("source", ""),
            "publication_date": summary.get("pubdate", ""),
            "pmc_url": None,
            "full_text_snippet": None,
            "is_open_access": bool(pmc_ids),
        }

        if pmc_ids:
            pmc_id = pmc_ids[0]
            result["pmc_url"] = f"https://www.ncbi.nlm.nih.gov/pmc/articles/{pmc_id}/"
            _rate_limit()
            try:
                ft_url = (
                    f"https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/"
                    f"pmcoa.cgi/BioC_json/{pmc_id}/unicode"
                )
                ft_resp = requests.get(ft_url, timeout=30)
                if ft_resp.status_code == 200:
                    ft_data = ft_resp.json()
                    passages = []
                    for doc in ft_data.get("documents", []):
                        for passage in doc.get("passages", []):
                            text = passage.get("text", "")
                            section = passage.get("infons", {}).get("section_type", "")
                            ptype = passage.get("infons", {}).get("type", "")
                            if (
                                text
                                and ptype != "ref"
                                and section not in ("REF", "COMP_INT")
                            ):
                                passages.append(text)
                    if passages:
                        result["full_text_snippet"] = "\n\n".join(passages)[:6000]
            except Exception:
                pass

        return result

    def _list_org(self, arguments, org_name):
        """List recent guidelines from a specific organization."""
        limit = arguments.get("limit", 10)
        year_from = arguments.get("year_from")

        date_filter = ""
        if year_from:
            date_filter = (
                f' AND ("{year_from}"[Date - Publication] : "3000"[Date - Publication])'
            )

        pubmed_query = (
            f'"{org_name}"[Corporate Author] AND '
            f'("guideline"[Title] OR "practice guideline"[Publication Type])'
            f"{date_filter}"
        )
        return _search_and_fetch(pubmed_query, limit=limit)


# ---------------------------------------------------------------------------
# NCCN Tools
# ---------------------------------------------------------------------------

_NCCN_BASE = "https://www.nccn.org"
_NCCN_GUIDELINES_URL = (
    f"{_NCCN_BASE}/patientresources/patient-resources/guidelines-for-patients"
)


@register_tool("NCCNGuidelineTool")
class NCCNGuidelineTool(BaseTool):
    """
    National Comprehensive Cancer Network (NCCN) guideline tools.

    Supports three operations:
    - list_patient: List NCCN Guidelines for Patients (free, scraped from nccn.org)
    - search: Search NCCN content via PubMed (JNCCN journal articles)
    - get_patient: Get content from a specific NCCN patient guideline page
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.operation = tool_config.get("fields", {}).get("operation", "search")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": _UA})

    def run(self, arguments):
        try:
            op = self.operation
            if op == "list_patient":
                return self._list_patient_guidelines(arguments)
            elif op == "search":
                return self._search(arguments)
            elif op == "get_patient":
                return self._get_patient_guideline(arguments)
            return {"error": f"Unknown operation: {op}"}
        except requests.exceptions.RequestException as e:
            return {"error": f"Request failed: {e}"}
        except Exception as e:
            return {"error": f"Error: {e}"}

    def _list_patient_guidelines(self, arguments):
        """List all NCCN Guidelines for Patients from nccn.org."""
        time.sleep(1)  # Respectful delay
        resp = self.session.get(_NCCN_GUIDELINES_URL, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Category mapping: anchor name -> display category
        category_map = {
            "category_1": "Treatment by Cancer Type",
            "category_2": "Detection, Prevention, and Risk Reduction",
            "category_3": "Supportive Care",
            "category_4": "Specific Populations",
        }

        # Build ordered list of (position, category_name) from <a name="category_N">
        # and (position, guideline_link) for each guideline link
        html_text = str(soup)
        category_positions = []
        for anchor_name, cat_label in category_map.items():
            # Find <a name="category_N"> in the HTML
            pattern = f'name="{anchor_name}"'
            idx = html_text.find(pattern)
            if idx >= 0:
                category_positions.append((idx, cat_label))
        category_positions.sort()

        guidelines = []
        seen_urls = set()

        for link in soup.find_all("a", href=True):
            href = link["href"]
            text = link.get_text(strip=True)

            # Only include links to individual guideline pages
            if "patientGuidelineId" not in href:
                continue
            if not text or len(text) < 3:
                continue

            full_url = _NCCN_BASE + href if href.startswith("/") else href
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Determine category by finding which category anchor precedes this link
            link_str = str(link)
            link_pos = html_text.find(link_str)
            current_category = "Treatment by Cancer Type"
            for cat_pos, cat_label in category_positions:
                if cat_pos < link_pos:
                    current_category = cat_label
                else:
                    break

            guidelines.append(
                {
                    "cancer_type": text,
                    "url": full_url,
                    "category": current_category,
                }
            )

        return guidelines

    def _search(self, arguments):
        """Search NCCN content via PubMed."""
        query_text = arguments.get("query", "")
        limit = arguments.get("limit", 5)
        if not query_text:
            return {"error": "query parameter is required"}

        pubmed_query = (
            f'("National Comprehensive Cancer Network"[Corporate Author] '
            f"OR NCCN[Title]) AND ({query_text})"
        )
        return _search_and_fetch(pubmed_query, limit=limit)

    def _get_patient_guideline(self, arguments):
        """Get content from a specific NCCN patient guideline — scrapes detail page
        and extracts text directly from the PDF using pdfplumber."""
        url = arguments.get("url", "")
        if not url:
            return {"error": "url parameter is required"}
        if "nccn.org" not in url:
            return {"error": "URL must be an nccn.org URL"}

        # Rewrite old-style content/english URLs to the current patientresources path
        if "patientGuidelineId" not in url and "patientresources" not in url:
            return {"error": "URL should come from NCCN_list_patient_guidelines"}

        time.sleep(1)
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "html.parser")

        # Extract title from h2
        cancer_type = ""
        for h2 in soup.find_all("h2"):
            text = h2.get_text(strip=True)
            if text and len(text) > 2:
                cancer_type = text
                break

        # Collect PDF links
        pdf_links = []
        seen_pdfs = set()
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" not in href.lower():
                continue
            full_pdf_url = _NCCN_BASE + href if href.startswith("/") else href
            if full_pdf_url in seen_pdfs:
                continue
            seen_pdfs.add(full_pdf_url)
            label = a.get_text(strip=True) or cancer_type
            pdf_links.append({"label": label, "url": full_pdf_url})

        # Extract version info
        version = ""
        for elem in soup.find_all(string=re.compile(r"\b20\d{2}\b")):
            candidate = elem.strip()
            if re.search(r"\b20\d{2}\b", candidate) and len(candidate) < 60:
                version = candidate
                break

        result = {
            "title": cancer_type or "NCCN Guidelines for Patients",
            "url": url,
            "cancer_type": cancer_type,
            "version": version,
            "pdf_url": pdf_links[0]["url"] if pdf_links else None,
            "pdf_downloads": pdf_links,
            "source": "NCCN Guidelines for Patients",
            "content": None,
        }

        # Download the primary PDF and extract text from first 8 pages
        primary_pdf = pdf_links[0]["url"] if pdf_links else None
        if primary_pdf:
            try:
                time.sleep(0.5)
                pdf_resp = self.session.get(primary_pdf, timeout=30)
                if (
                    pdf_resp.status_code == 200
                    and "pdf" in pdf_resp.headers.get("Content-Type", "").lower()
                ):
                    with pdfplumber.open(io.BytesIO(pdf_resp.content)) as pdf:
                        pages_text = []
                        for page in pdf.pages[:8]:
                            text = page.extract_text()
                            if text and len(text.strip()) > 50:
                                pages_text.append(text.strip())
                    if pages_text:
                        result["content"] = "\n\n---\n\n".join(pages_text)[:6000]
            except Exception:
                pass  # content remains None; pdf_url still returned

        return result
