# dailymed_tool.py

import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

try:
    from lxml import etree

    LXML_AVAILABLE = True
except ImportError:
    LXML_AVAILABLE = False

DAILYMED_BASE = "https://dailymed.nlm.nih.gov/dailymed/services/v2"


@register_tool("SearchSPLTool")
class SearchSPLTool(BaseTool):
    """
    Search SPL list based on multiple filter conditions (drug_name/ndc/rxcui/setid/published_date).
    Returns original DailyMed API JSON (including metadata + data array).
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint = f"{DAILYMED_BASE}/spls.json"

    def run(self, arguments):
        params = {}
        if arguments.get("drug_name"):
            params["drug_name"] = arguments["drug_name"]
        if arguments.get("ndc"):
            params["ndc"] = arguments["ndc"]
        if arguments.get("rxcui"):
            params["rxcui"] = arguments["rxcui"]
        if arguments.get("setid"):
            params["setid"] = arguments["setid"]

        if arguments.get("published_date_gte"):
            params["published_date[gte]"] = arguments["published_date_gte"]
        if arguments.get("published_date_eq"):
            params["published_date[eq]"] = arguments["published_date_eq"]

        params["pagesize"] = arguments.get("pagesize", 100)
        params["page"] = arguments.get("page", 1)

        try:
            resp = requests.get(self.endpoint, params=params, timeout=10)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request DailyMed search_spls: {str(e)}",
            }

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"DailyMed API access failed, HTTP {resp.status_code}",
                "detail": resp.text,
            }

        try:
            result = resp.json()
        except ValueError:
            return {
                "status": "error",
                "error": "Unable to parse DailyMed returned JSON.",
                "content": resp.text,
            }

        # Return with standard status envelope
        return {
            "status": "success",
            "data": result.get("data", []),
            "metadata": result.get("metadata", {}),
        }


@register_tool("GetSPLBySetIDTool")
class GetSPLBySetIDTool(BaseTool):
    """
    Get complete SPL label based on SPL Set ID, returns content in XML or JSON format.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Different suffixes for XML and JSON
        self.endpoint_template = f"{DAILYMED_BASE}/spls/{{setid}}.{{fmt}}"

    def run(self, arguments):
        setid = arguments.get("setid")
        fmt = arguments.get("format", "xml")

        if fmt != "xml":
            return {
                "status": "error",
                "error": "DailyMed single SPL API only supports 'xml' format, JSON is not supported.",
            }

        url = self.endpoint_template.format(setid=setid, fmt=fmt)
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request DailyMed get_spl_by_setid: {str(e)}",
            }

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"SPL label not found for Set ID={setid}.",
            }
        elif resp.status_code == 415:
            return {
                "status": "error",
                "error": f"DailyMed API does not support requested format. Set ID={setid} only supports XML format.",
            }
        elif resp.status_code != 200:
            return {
                "status": "error",
                "error": f"DailyMed API access failed, HTTP {resp.status_code}",
                "detail": resp.text,
            }

        return {"status": "success", "xml": resp.text}


@register_tool("DailyMedSPLParserTool")
class DailyMedSPLParserTool(BaseTool):
    """
    Parse DailyMed SPL XML into structured data (adverse reactions, dosing, contraindications, interactions, PK).
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.endpoint_template = f"{DAILYMED_BASE}/spls/{{setid}}.xml"

        # XML namespaces used in SPL documents
        self.ns = {"hl7": "urn:hl7-org:v3"}

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to parser based on operation."""
        if not LXML_AVAILABLE:
            return {
                "status": "error",
                "error": "lxml not available. Install with: pip install lxml",
            }

        operation = arguments.get("operation")
        # Auto-fill operation from tool config const if not provided by user
        if not operation:
            operation = self.get_schema_const_operation()
        setid = arguments.get("setid")

        # Auto-resolve drug_name to setid when only the name is provided
        if not setid:
            drug_name = arguments.get("drug_name")
            if drug_name:
                try:
                    resp = requests.get(
                        f"{DAILYMED_BASE}/spls.json",
                        params={"drug_name": drug_name, "pagesize": 1},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        items = resp.json().get("data", [])
                        if items:
                            setid = items[0].get("setid")
                except Exception:
                    pass

        if not setid:
            return {
                "status": "error",
                "error": (
                    "Missing required parameter: setid. "
                    "Provide a DailyMed Set ID UUID, or use drug_name for automatic lookup."
                ),
            }

        if not operation:
            return {"status": "error", "error": "Missing required parameter: operation"}

        # Fetch SPL XML
        xml_result = self._fetch_spl_xml(setid)
        if xml_result.get("status") == "error":
            return xml_result

        xml_content = xml_result.get("xml")
        if not xml_content:
            return {"status": "error", "error": "No XML content returned"}

        # Parse XML
        try:
            root = etree.fromstring(xml_content.encode("utf-8"))
        except Exception as e:
            return {"status": "error", "error": f"Failed to parse XML: {str(e)}"}

        # Route to appropriate parser
        if operation == "parse_adverse_reactions":
            operation_result = self._parse_adverse_reactions(root)
        elif operation == "parse_dosing":
            operation_result = self._parse_dosing(root)
        elif operation == "parse_contraindications":
            operation_result = self._parse_contraindications(root)
        elif operation == "parse_drug_interactions":
            operation_result = self._parse_drug_interactions(root)
        elif operation == "parse_clinical_pharmacology":
            operation_result = self._parse_clinical_pharmacology(root)
        else:
            return {"status": "error", "error": f"Unknown operation: {operation}"}

        result = self._with_data_payload(operation_result)
        if result.get("status") == "success":
            result["metadata"] = {
                "source": "DailyMed",
                "setid": setid,
                "drug_name": arguments.get("drug_name"),
                "operation": operation,
            }
        return result

    def _with_data_payload(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure successful operation responses include a standardized data wrapper."""
        if not isinstance(result, dict):
            return {"status": "success", "data": {"value": result}, "value": result}

        if result.get("status") != "success":
            return result

        if "data" in result:
            return result

        data = {k: v for k, v in result.items() if k != "status"}
        return {"status": "success", "data": data}

    def _fetch_spl_xml(self, setid: str) -> Dict[str, Any]:
        """Fetch SPL XML from DailyMed API."""
        url = self.endpoint_template.format(setid=setid)
        try:
            resp = requests.get(url, timeout=30)
        except Exception as e:
            return {"status": "error", "error": f"Failed to fetch SPL: {str(e)}"}

        if resp.status_code == 404:
            return {"status": "error", "error": f"SPL not found for setid={setid}"}
        elif resp.status_code != 200:
            return {
                "status": "error",
                "error": f"HTTP {resp.status_code}: {resp.text[:200]}",
            }

        return {"status": "success", "xml": resp.text}

    def _parse_adverse_reactions(self, root) -> Dict[str, Any]:
        """Parse adverse reactions section into structured table."""
        try:
            # Find adverse reactions section (code 34084-4)
            sections = root.xpath(
                "//hl7:section[hl7:code[@code='34084-4']]", namespaces=self.ns
            )

            if not sections:
                return {
                    "status": "success",
                    "adverse_reactions": [],
                    "note": "No adverse reactions section found",
                }

            adverse_reactions = []
            for section in sections:
                # Extract text content
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    # Look for tables
                    tables = text_el.xpath(".//hl7:table", namespaces=self.ns)
                    for table in tables:
                        table_data = self._extract_table_data(table)
                        if table_data:
                            adverse_reactions.extend(table_data)

                    # If no tables, extract paragraph text
                    if not tables:
                        paragraphs = text_el.xpath(
                            ".//hl7:paragraph", namespaces=self.ns
                        )
                        for para in paragraphs:
                            text_content = "".join(para.itertext()).strip()
                            if text_content and len(text_content) > 10:
                                adverse_reactions.append(
                                    {"type": "text", "content": text_content}
                                )

            return {
                "status": "success",
                "adverse_reactions": adverse_reactions,
                "count": len(adverse_reactions),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse adverse reactions: {str(e)}",
            }

    def _parse_dosing(self, root) -> Dict[str, Any]:
        """Parse dosage and administration section."""
        try:
            # Find dosage section (code 34068-7)
            sections = root.xpath(
                "//hl7:section[hl7:code[@code='34068-7']]", namespaces=self.ns
            )

            if not sections:
                return {
                    "status": "success",
                    "dosing_info": [],
                    "note": "No dosing section found",
                }

            dosing_info = []
            for section in sections:
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    # Extract tables
                    tables = text_el.xpath(".//hl7:table", namespaces=self.ns)
                    for table in tables:
                        table_data = self._extract_table_data(table)
                        if table_data:
                            dosing_info.extend(table_data)

                    # Extract paragraphs
                    paragraphs = text_el.xpath(".//hl7:paragraph", namespaces=self.ns)
                    for para in paragraphs:
                        text_content = "".join(para.itertext()).strip()
                        if text_content and len(text_content) > 10:
                            dosing_info.append(
                                {"type": "dosing_text", "content": text_content}
                            )

                    # Extract list items (some drugs encode dosing as <list><item> elements)
                    for item in text_el.xpath(".//hl7:item", namespaces=self.ns):
                        text_content = "".join(item.itertext()).strip()
                        if text_content and len(text_content) > 5:
                            dosing_info.append(
                                {"type": "dosing_text", "content": text_content}
                            )

            return {
                "status": "success",
                "dosing_info": dosing_info,
                "count": len(dosing_info),
            }

        except Exception as e:
            return {"status": "error", "error": f"Failed to parse dosing: {str(e)}"}

    def _parse_contraindications(self, root) -> Dict[str, Any]:
        """Parse contraindications section."""
        try:
            # Find contraindications section (code 34070-3)
            sections = root.xpath(
                "//hl7:section[hl7:code[@code='34070-3']]", namespaces=self.ns
            )

            if not sections:
                return {
                    "status": "success",
                    "contraindications": [],
                    "note": "No contraindications section found",
                }

            contraindications = []
            for section in sections:
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    # Extract lists
                    list_items = text_el.xpath(".//hl7:item", namespaces=self.ns)
                    for item in list_items:
                        text_content = "".join(item.itertext()).strip()
                        if text_content and len(text_content) > 5:
                            contraindications.append(
                                {
                                    "type": "contraindication",
                                    "description": text_content,
                                }
                            )

                    # Extract paragraphs if no list items
                    if not list_items:
                        paragraphs = text_el.xpath(
                            ".//hl7:paragraph", namespaces=self.ns
                        )
                        for para in paragraphs:
                            text_content = "".join(para.itertext()).strip()
                            if text_content and len(text_content) > 2:
                                contraindications.append(
                                    {
                                        "type": "contraindication",
                                        "description": text_content,
                                    }
                                )

            return {
                "status": "success",
                "contraindications": contraindications,
                "count": len(contraindications),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse contraindications: {str(e)}",
            }

    def _parse_drug_interactions(self, root) -> Dict[str, Any]:
        """Parse drug interactions section."""
        try:
            # Find drug interactions section (code 34073-7)
            sections = root.xpath(
                "//hl7:section[hl7:code[@code='34073-7']]", namespaces=self.ns
            )

            if not sections:
                return {
                    "status": "success",
                    "interactions": [],
                    "note": "No drug interactions section found",
                }

            interactions = []
            for section in sections:
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    # Extract tables
                    tables = text_el.xpath(".//hl7:table", namespaces=self.ns)
                    for table in tables:
                        table_data = self._extract_table_data(table)
                        if table_data:
                            interactions.extend(table_data)

                    # Extract paragraphs
                    paragraphs = text_el.xpath(".//hl7:paragraph", namespaces=self.ns)
                    for para in paragraphs:
                        text_content = "".join(para.itertext()).strip()
                        if text_content and len(text_content) > 10:
                            interactions.append(
                                {"type": "interaction_text", "content": text_content}
                            )

            return {
                "status": "success",
                "interactions": interactions,
                "count": len(interactions),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse drug interactions: {str(e)}",
            }

    def _parse_clinical_pharmacology(self, root) -> Dict[str, Any]:
        """Parse clinical pharmacology section."""
        try:
            # Find clinical pharmacology section (code 34090-1)
            sections = root.xpath(
                "//hl7:section[hl7:code[@code='34090-1']]", namespaces=self.ns
            )

            if not sections:
                return {
                    "status": "success",
                    "pharmacology": [],
                    "note": "No clinical pharmacology section found",
                }

            pharmacology = []
            for section in sections:
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    # Extract tables
                    tables = text_el.xpath(".//hl7:table", namespaces=self.ns)
                    for table in tables:
                        table_data = self._extract_table_data(table)
                        if table_data:
                            pharmacology.extend(table_data)

                    # Extract paragraphs
                    paragraphs = text_el.xpath(".//hl7:paragraph", namespaces=self.ns)
                    for para in paragraphs:
                        text_content = "".join(para.itertext()).strip()
                        if text_content and len(text_content) > 10:
                            pharmacology.append(
                                {"type": "pharmacology_text", "content": text_content}
                            )

            return {
                "status": "success",
                "pharmacology": pharmacology,
                "count": len(pharmacology),
            }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to parse clinical pharmacology: {str(e)}",
            }

    def _extract_table_data(self, table_element) -> List[Dict[str, Any]]:
        """Extract structured data from table element."""
        try:
            rows_data = []

            # Get table headers
            headers = []
            thead = table_element.xpath(".//hl7:thead", namespaces=self.ns)
            if thead:
                header_cells = thead[0].xpath(".//hl7:th", namespaces=self.ns)
                headers = ["".join(cell.itertext()).strip() for cell in header_cells]

            # Get table rows
            tbody = table_element.xpath(".//hl7:tbody", namespaces=self.ns)
            if tbody:
                rows = tbody[0].xpath(".//hl7:tr", namespaces=self.ns)
                for row in rows:
                    cells = row.xpath(".//hl7:td", namespaces=self.ns)
                    cell_data = ["".join(cell.itertext()).strip() for cell in cells]

                    if cell_data:
                        # Create dict if we have headers
                        if headers and len(headers) == len(cell_data):
                            row_dict = {
                                "type": "table_row",
                                "data": dict(zip(headers, cell_data)),
                            }
                        else:
                            row_dict = {"type": "table_row", "data": cell_data}
                        rows_data.append(row_dict)

            return rows_data

        except Exception:
            return []
