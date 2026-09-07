# gsa_tool.py
"""
GSA (Genome Sequence Archive) tool for ToolUniverse.

GSA (ngdc.cncb.ac.cn/gsa), run by China's National Genomics Data Center
(NGDC/CNCB), is a major raw-sequencing-data archive alongside NCBI's SRA,
EBI's ENA, and Japan's DDBJ (the latter already covered by
ddbj_tool.py) -- but for a large and growing share of Chinese-origin
genomic datasets, GSA is the primary or only archive. There is no JSON
API; accession pages are server-rendered HTML (Chinese-labeled fields),
so this tool parses that page for a given CRA-format run/study
accession, returning its title, associated BioProject, publication
link, file count/size, and direct HTTPS/FTP download URLs.

No authentication required.
"""

from typing import Any, Dict, Optional

import requests
from bs4 import BeautifulSoup

from .base_tool import BaseTool
from .tool_registry import register_tool

GSA_BASE_URL = "https://ngdc.cncb.ac.cn/gsa"
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ToolUniverse/1.0)"}


def _panel_by_heading(soup: BeautifulSoup, heading_text: str):
    for panel in soup.find_all("div", class_="panel-heading"):
        if heading_text in panel.get_text():
            return panel.find_parent("div", class_="panel")
    return None


def _label_value(soup: BeautifulSoup, label: str) -> Optional[str]:
    b = soup.find("b", string=lambda s: s and label in s)
    if not b:
        return None
    return b.parent.get_text(strip=True).replace(label, "").strip() or None


def _publication_info(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    panel = _panel_by_heading(soup, "出版信息")
    fields = {"title": None, "journal": None, "year": None, "doi": None, "pubmed_id": None}
    if panel is None:
        return fields
    label_map = {
        "文章标题": "title",
        "杂志名称": "journal",
        "发表年份": "year",
        "Doi": "doi",
        "PubMed ID": "pubmed_id",
    }
    for row in panel.find_all("div", class_="row"):
        strong = row.find("strong")
        if not strong:
            continue
        key = label_map.get(strong.get_text(strip=True))
        if key is None:
            continue
        divs = row.find_all("div")
        if divs:
            fields[key] = divs[-1].get_text(strip=True) or None
    return fields


def _download_urls(soup: BeautifulSoup) -> Dict[str, Optional[str]]:
    panel = _panel_by_heading(soup, "数据下载")
    urls = {"https": None, "ftp": None}
    if panel is None:
        return urls
    https_a = panel.find("a", href=lambda h: h and h.startswith("https://download.cncb.ac.cn"))
    ftp_a = panel.find("a", href=lambda h: h and h.startswith("ftp://"))
    urls["https"] = https_a.get("href") if https_a else None
    urls["ftp"] = ftp_a.get("href") if ftp_a else None
    return urls


@register_tool("GSATool")
class GSATool(BaseTool):
    """Look up a GSA (Genome Sequence Archive) accession's metadata page.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        accession = (arguments.get("accession") or "").strip().upper()
        if not accession:
            return {
                "status": "error",
                "error": "accession is required, e.g. 'CRA002926'.",
            }

        try:
            resp = requests.get(
                f"{GSA_BASE_URL}/browse/{accession}",
                headers=_HEADERS,
                timeout=self.timeout,
            )
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GSA request timed out after {self.timeout}s",
            }
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"GSA request failed: {e}"}
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")
        title = _label_value(soup, "标题:")
        if title is None:
            return {
                "status": "error",
                "error": f"No GSA accession found for '{accession}'.",
            }

        bioproject_b = soup.find("b", string=lambda s: s and "项目编号" in s)
        bioproject_a = bioproject_b.parent.find("a") if bioproject_b else None

        return {
            "status": "success",
            "data": {
                "accession": accession,
                "title": title,
                "bioproject_accession": (
                    bioproject_a.get_text(strip=True) if bioproject_a else None
                ),
                "bioproject_url": bioproject_a.get("href") if bioproject_a else None,
                "release_date": _label_value(soup, "发布日期:"),
                "file_count": _label_value(soup, "文件个数:"),
                "file_size": _label_value(soup, "文件大小:"),
                "publication": _publication_info(soup),
                "download_urls": _download_urls(soup),
            },
            "metadata": {
                "accession": accession,
                "source": "GSA / National Genomics Data Center (ngdc.cncb.ac.cn)",
            },
        }
