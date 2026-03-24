from typing import Dict, Any, List, Optional
import requests
import re
from tooluniverse.base_tool import BaseTool
from tooluniverse.tool_registry import register_tool


@register_tool("FDAPharmacogenomicBiomarkersTool")
class FDAPharmacogenomicBiomarkersTool(BaseTool):
    """
    Tool to retrieve data from the FDA's Table of Pharmacogenomic Biomarkers in Drug Labeling.
    Fetches the table from the FDA website and provides filtering capabilities.
    """

    FDA_URL = "https://www.fda.gov/drugs/science-and-research-drugs/table-pharmacogenomic-biomarkers-drug-labeling"

    # Standard headers to avoid 403/404 errors from FDA servers
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes the tool to retrieve and filter pharmacogenomic biomarkers.

        Args:
            arguments (Dict[str, Any]):
                - drug_name (str, optional): Filter by drug name (case-insensitive partial match).
                - biomarker (str, optional): Filter by biomarker (case-insensitive partial match).
                - limit (int, optional): Maximum number of results to return (default: 10).

        Returns:
            Dict[str, Any]: A dictionary containing the 'count' and 'results' list.
        """
        drug_name_filter = arguments.get("drug_name")
        biomarker_filter = arguments.get("biomarker")
        limit = arguments.get("limit", 10)

        try:
            # TODO: Add caching mechanism if available in the ecosystem
            # For now, we fetch every time or rely on potential requests caching if configured globally
            response = requests.get(self.FDA_URL, headers=self.HEADERS, timeout=30)
            response.raise_for_status()

            records = self._parse_html_table(response.text)

            # Filter results
            filtered_results = []
            for record in records:
                match = True
                if drug_name_filter:
                    if drug_name_filter.lower() not in record.get("Drug", "").lower():
                        match = False

                if match and biomarker_filter:
                    if (
                        biomarker_filter.lower()
                        not in record.get("Biomarker", "").lower()
                    ):
                        match = False

                if match:
                    filtered_results.append(record)

            # Apply limit
            limited_results = filtered_results[:limit]

            return {
                "status": "success",
                "count": len(filtered_results),
                "shown": len(limited_results),
                "results": limited_results,
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to retrieve or parse FDA data: {str(e)}",
            }

    def _parse_html_table(self, html_content: str) -> List[Dict[str, str]]:
        """
        Parses the HTML content to extract the biomarkers table.
        Uses regex/simple parsing to avoid heavy dependencies like BeautifulSoup if possible,
        or assumes BeautifulSoup is available in the environment (it usually is in this project).
        """
        records = []
        try:
            # Try importing BeautifulSoup, fallback to regex if not available (though highly recommended)
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(html_content, "html.parser")

            # Find the table - usually the first table in the main content or identified by headers
            # The FDA page structure has a table with specific headers
            tables = soup.find_all("table")
            target_table = None

            for table in tables:
                headers = [th.get_text(strip=True) for th in table.find_all("th")]
                # Partial match check for crucial columns
                if any("Drug" in h for h in headers) and any(
                    "Biomarker" in h for h in headers
                ):
                    target_table = table
                    break

            if target_table:
                # Get the header mapping
                headers = [
                    th.get_text(strip=True) for th in target_table.find_all("th")
                ]
                # Map headers to cleaner keys
                header_map = {
                    "Drug": "Drug",
                    "Therapeutic Area": "TherapeuticArea",
                    "Biomarker": "Biomarker",
                    "Labeling Section": "LabelingSection",
                }

                rows = target_table.find_all("tr")[1:]  # Skip header row
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if not cells:
                        continue

                    record = {}
                    for i, cell in enumerate(cells):
                        if i < len(headers):
                            original_header = headers[i]
                            # Clean header for mapping (remove special chars)
                            clean_header = (
                                original_header.replace("\xa0", " ")
                                .replace("*", "")
                                .replace("†", "")
                                .strip()
                            )

                            # Clean cell text
                            cell_text = cell.get_text(strip=True)

                            # Find matching key based on partial match
                            key = None
                            for k in header_map:
                                # Check if configured key is part of the cleaned actual header (e.g. "Labeling Section" in "Labeling Sections")
                                if k in clean_header:
                                    key = header_map[k]
                                    break

                            if key:
                                record[key] = cell_text
                            elif (
                                clean_header
                            ):  # Store unmapped columns if header is not empty
                                record[clean_header] = cell_text

                    if record.get("Drug"):  # Only add valid records
                        records.append(record)

            return records

        except ImportError:
            # Fallback regex parsing if BS4 is missing (less robust)
            # Find table rows
            row_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.DOTALL)
            cell_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.DOTALL)

            matches = row_pattern.findall(html_content)
            for match in matches:
                cells = cell_pattern.findall(match)
                if len(cells) >= 3:  # Assuming at least Drug, Area, Biomarker
                    # Cleanup tags
                    clean_cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
                    # This is very brittle, BS4 is preferred.
                    # Assuming standard FDA columns order: Drug, Therapeutic Area, Biomarker, Labeling Section
                    if len(clean_cells) >= 4:
                        records.append(
                            {
                                "Drug": clean_cells[0],
                                "TherapeuticArea": clean_cells[1],
                                "Biomarker": clean_cells[2],
                                "LabelingSection": clean_cells[3],
                            }
                        )
            return records
