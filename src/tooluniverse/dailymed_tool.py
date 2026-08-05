# dailymed_tool.py

import json
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

        # Fix-R33A-1: "limit" is the dominant pagination param name across
        # ToolUniverse (CPIC, ClinVar, GWAS, ...), so a caller guessing it
        # here instead of DailyMed's own "pagesize" was silently ignored --
        # confirmed live (limit=3 still returned all 44 isoniazid labels).
        params["pagesize"] = arguments.get("pagesize") or arguments.get("limit") or 100
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

        # Fix-R6A-2/R6D-3/R6E-3: DailyMed's own API literally serializes
        # absent pagination links as the JSON string "null" rather than a
        # real null, so a caller's `if metadata["next_page_url"]:` truthy
        # check treats a missing next page as present. Normalize before
        # returning instead of passing the upstream quirk straight through.
        metadata = {
            k: (None if v == "null" else v)
            for k, v in result.get("metadata", {}).items()
        }

        # Return with standard status envelope
        return {
            "status": "success",
            "data": result.get("data", []),
            "metadata": metadata,
        }


@register_tool("GetSPLBySetIDTool")
class GetSPLBySetIDTool(BaseTool):
    """
    Get complete SPL label based on SPL Set ID, returns content in XML or JSON format.

    When configured with a ``resource`` field (e.g. 'media' or 'history'), fetches
    the corresponding DailyMed JSON sub-resource for the Set ID instead of the
    full SPL XML document.
    """

    def __init__(self, tool_config):
        super().__init__(tool_config)
        # Different suffixes for XML and JSON
        self.endpoint_template = f"{DAILYMED_BASE}/spls/{{setid}}.{{fmt}}"
        # Optional sub-resource (media / history) served as JSON
        self.resource = tool_config.get("fields", {}).get("resource")

    def run(self, arguments):
        if self.resource in ("media", "history"):
            return self._get_resource(arguments)
        return self._get_full_spl(arguments)

    def _get_resource(self, arguments):
        """Fetch a JSON sub-resource (media or history) for an SPL Set ID."""
        setid = arguments.get("setid")
        if not setid or not str(setid).strip():
            return {"status": "error", "error": "setid parameter is required"}

        url = f"{DAILYMED_BASE}/spls/{str(setid).strip()}/{self.resource}.json"
        try:
            resp = requests.get(url, timeout=30)
        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to request DailyMed {self.resource}: {str(e)}",
            }

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"SPL {self.resource} not found for Set ID={setid}.",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"DailyMed API access failed, HTTP {resp.status_code}",
            }

        try:
            result = resp.json()
        except ValueError:
            return {
                "status": "error",
                "error": f"Unable to parse DailyMed {self.resource} JSON.",
            }

        data = result.get("data", {})
        if self.resource == "media":
            payload = {
                "setid": data.get("setid", str(setid).strip()),
                "title": data.get("title"),
                "spl_version": data.get("spl_version"),
                "media": data.get("media", []) or [],
            }
        else:  # history
            payload = {
                "setid": (data.get("spl") or {}).get("setid", str(setid).strip()),
                "title": (data.get("spl") or {}).get("title"),
                "history": data.get("history", []) or [],
            }

        return {
            "status": "success",
            "data": payload,
            "metadata": result.get("metadata", {}),
        }

    def _get_full_spl(self, arguments):
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

        return {"status": "success", "xml": resp.text, "data": {"xml": resp.text}}


def _dedupe_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Fix-R4C-1: SPL documents often expose the same section content
    through multiple matching <section> elements (e.g. a Highlights summary
    plus the Full Prescribing Information), so a parser can walk the
    identical paragraph/table text more than once. Dedupe by content,
    preserving first-seen order, so the same statement never appears twice
    in one response. A no-op when there's no duplication to begin with."""
    seen = set()
    deduped = []
    for item in items:
        key = json.dumps(item, sort_keys=True)
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return deduped


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
            if arguments.get("drug_name"):
                # Fix-R4C-2: drug_name WAS provided but the lookup above found
                # no matching SPL (or the lookup call itself failed) -- the old
                # generic "setid missing" message told the user to do exactly
                # what they already did, instead of reporting the real problem.
                return {
                    "status": "error",
                    "error": (
                        f"No DailyMed SPL found for drug_name="
                        f"'{arguments['drug_name']}'. Check the spelling, or "
                        "supply an exact `setid` (DailyMed Set ID UUID) instead."
                    ),
                }
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
            # Fix-R9A-2/R9D-3: metadata.drug_name was only ever populated
            # from the caller's own `drug_name` argument, so it was always
            # null for the common case of calling with `setid` directly
            # (e.g. after a prior search_spls call) -- even though the SPL
            # itself already names the product. Fall back to the SPL's own
            # manufacturedProduct name, which is already available on the
            # parsed XML at no extra network cost.
            drug_name = arguments.get("drug_name")
            if not drug_name:
                name_el = root.xpath(
                    "//hl7:manufacturedProduct/hl7:manufacturedProduct/hl7:name",
                    namespaces=self.ns,
                )
                if name_el and name_el[0].text:
                    drug_name = name_el[0].text.strip()
            result["metadata"] = {
                "source": "DailyMed",
                "setid": setid,
                "drug_name": drug_name,
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
                text_elements = section.xpath(".//hl7:text", namespaces=self.ns)
                for text_el in text_elements:
                    adverse_reactions.extend(
                        self._extract_ordered_content(text_el, "text")
                    )

            adverse_reactions = _dedupe_items(adverse_reactions)

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
                    dosing_info.extend(
                        self._extract_ordered_content(text_el, "dosing_text")
                    )

            dosing_info = _dedupe_items(dosing_info)

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

            contraindications = _dedupe_items(contraindications)

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
                    interactions.extend(
                        self._extract_ordered_content(text_el, "interaction_text")
                    )

            interactions = _dedupe_items(interactions)

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
                    pharmacology.extend(
                        self._extract_ordered_content(text_el, "pharmacology_text")
                    )

            pharmacology = _dedupe_items(pharmacology)

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

    def _extract_ordered_content(
        self, text_el, text_type: str, min_len: int = 10
    ) -> List[Dict[str, Any]]:
        """Fix-R5B-1/R7A-1: walk a <text> element's direct children
        (paragraph/list/table) in document order instead of the old
        approach of extracting all tables, then all paragraphs, then all
        list items in three separate passes. That old approach broke in
        two independent ways: (1) SPL sections routinely interleave a
        heading paragraph immediately before the table or list it
        introduces (e.g. "Juvenile Idiopathic Arthritis (2.3):" followed
        by its dosing table), and grouping every table before every
        paragraph destroyed that association; (2) some methods had no
        <list>/<item> handling at all, so e.g. warfarin's adverse-reactions
        section -- whose actual reaction list is encoded as <list><item>
        blocks alongside intro <paragraph> sentences -- silently dropped
        every list item, leaving only the generic intro sentences."""
        items: List[Dict[str, Any]] = []
        for child in text_el.iterchildren():
            tag = etree.QName(child).localname
            if tag == "table":
                # _extract_table_data always returns a list, so extend()
                # handles the empty case without a separate guard.
                items.extend(self._extract_table_data(child))
            elif tag == "paragraph":
                text_content = "".join(child.itertext()).strip()
                if text_content and len(text_content) > min_len:
                    items.append({"type": text_type, "content": text_content})
            elif tag == "list":
                for item_el in child.xpath(".//hl7:item", namespaces=self.ns):
                    text_content = "".join(item_el.itertext()).strip()
                    if text_content and len(text_content) > 5:
                        items.append({"type": text_type, "content": text_content})
        return items

    def _cell_text(self, element) -> str:
        """Fix-R6E-2: SPL table cells use <br/> as an in-cell line break
        (e.g. "TRIKAFTA" on one line, "N=202" on the next, "n (%)" on a
        third), but joining itertext() with no separator collapsed these
        into a single run like "TRIKAFTAN=202n (%)". Walk the cell's mixed
        content and insert a space at each <br/> boundary instead."""
        parts: List[str] = []

        def walk(el) -> None:
            if el.text:
                parts.append(el.text)
            for child in el:
                if etree.QName(child).localname == "br":
                    parts.append(" ")
                else:
                    walk(child)
                if child.tail:
                    parts.append(child.tail)

        walk(element)
        return " ".join("".join(parts).split())

    def _extract_table_data(self, table_element) -> List[Dict[str, Any]]:
        """Extract structured data from table element."""
        try:
            rows_data = []

            # Get table headers
            headers = []
            thead = table_element.xpath(".//hl7:thead", namespaces=self.ns)
            if thead:
                header_cells = thead[0].xpath(".//hl7:th", namespaces=self.ns)
                headers = [self._cell_text(cell) for cell in header_cells]

            # Get table rows
            tbody = table_element.xpath(".//hl7:tbody", namespaces=self.ns)
            if tbody:
                rows = tbody[0].xpath(".//hl7:tr", namespaces=self.ns)
                for row in rows:
                    cells = row.xpath(".//hl7:td", namespaces=self.ns)
                    cell_data = [self._cell_text(cell) for cell in cells]

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
