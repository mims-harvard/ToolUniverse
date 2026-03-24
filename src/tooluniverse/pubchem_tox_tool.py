# pubchem_tox_tool.py
"""
PubChem Toxicity/Safety tool for ToolUniverse.

Provides access to PubChem PUG View toxicity and safety data:
- GHS hazard classification (pictograms, signal words, hazard statements)
- Toxicity values (LD50, LC50, non-human toxicity data)
- Carcinogen classification (IARC, NTP, EPA)
- Target organs affected by chemicals
- Acute/chronic toxicity effects
- Safety and hazard summary information

API: https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/
No authentication required. Free public access.
"""

import re
import requests
from typing import Dict, Any, List, Optional
from .base_tool import BaseTool


PUGVIEW_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug_view/data/compound"
PUG_BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound"


class PubChemToxTool(BaseTool):
    """
    Tool for PubChem toxicity and safety data via PUG View API.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "ghs_classification")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the PubChem toxicity API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"PubChem API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to PubChem API"}
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code if e.response is not None else "unknown"
            if code == 404:
                cid = arguments.get("cid", arguments.get("compound_name", ""))
                return {
                    "status": "error",
                    "error": f"No toxicity data found in PubChem for: {cid}. This heading may not exist for this compound.",
                }
            return {"status": "error", "error": f"PubChem API HTTP error: {code}"}
        except ValueError as e:
            return {"status": "error", "error": str(e)}
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying PubChem: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "ghs_classification":
            return self._get_ghs_classification(arguments)
        elif self.endpoint == "toxicity_values":
            return self._get_toxicity_values(arguments)
        elif self.endpoint == "carcinogen_classification":
            return self._get_carcinogen_classification(arguments)
        elif self.endpoint == "target_organs":
            return self._get_target_organs(arguments)
        elif self.endpoint == "acute_effects":
            return self._get_acute_effects(arguments)
        elif self.endpoint == "toxicity_summary":
            return self._get_toxicity_summary(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _resolve_cid(self, arguments: Dict[str, Any]) -> int:
        """Resolve compound name to CID if needed."""
        cid = arguments.get("cid")
        if cid:
            return int(cid)

        compound_name = arguments.get("compound_name", "")
        if not compound_name:
            raise ValueError("Either 'cid' or 'compound_name' parameter is required")

        url = f"{PUG_BASE_URL}/name/{compound_name}/cids/JSON"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()
        cids = data.get("IdentifierList", {}).get("CID", [])
        if not cids:
            raise ValueError(f"No compound found for name: {compound_name}")
        return cids[0]

    def _strip_html(self, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return ""
        return re.sub(r"<[^>]+>", "", text).strip()

    def _find_sections_recursive(
        self, sections: List[Dict], heading: str
    ) -> List[Dict]:
        """Recursively find all sections matching a heading at any depth."""
        found = []
        for s in sections:
            if s.get("TOCHeading") == heading:
                found.append(s)
            # Recurse into subsections
            found.extend(self._find_sections_recursive(s.get("Section", []), heading))
        return found

    def _extract_info_from_sections(
        self, sections: List[Dict], heading: str
    ) -> List[Dict]:
        """Find sections matching heading recursively and extract their Information entries."""
        matched = self._find_sections_recursive(sections, heading)
        results = []
        for section in matched:
            for info in section.get("Information", []):
                name = info.get("Name", "")
                val = info.get("Value", {})
                sws = val.get("StringWithMarkup", [])
                if sws:
                    text = sws[0].get("String", "")
                    markups = sws[0].get("Markup", [])
                    extras = [m.get("Extra", "") for m in markups if m.get("Extra")]
                    entry = {
                        "name": name,
                        "value": self._strip_html(text),
                    }
                    if extras:
                        entry["pictogram_labels"] = extras
                    results.append(entry)
        return results

    def _get_pugview_data(self, cid: int, heading: str) -> Dict:
        """Get PUG View data for a specific heading."""
        url = f"{PUGVIEW_BASE_URL}/{cid}/JSON"
        params = {"heading": heading}
        response = requests.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def _get_ghs_classification(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get GHS (Globally Harmonized System) hazard classification for a compound."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "GHS Classification")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        ghs_info = self._extract_info_from_sections(sections, "GHS Classification")

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "ghs_classification": ghs_info,
            },
            "metadata": {
                "source": "PubChem PUG View (GHS Classification)",
                "cid": cid,
            },
        }

    def _get_toxicity_values(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get non-human toxicity values (LD50, LC50, etc.) for a compound."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "Non-Human Toxicity Values")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        raw_info = self._extract_info_from_sections(
            sections, "Non-Human Toxicity Values"
        )
        tox_values = [item["value"] for item in raw_info if item.get("value")]

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "toxicity_values_count": len(tox_values),
                "toxicity_values": tox_values[:30],
            },
            "metadata": {
                "source": "PubChem PUG View (Non-Human Toxicity Values)",
                "cid": cid,
            },
        }

    def _get_carcinogen_classification(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get carcinogen classification data for a compound."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "Carcinogen Classification")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        raw_info = self._extract_info_from_sections(
            sections, "Carcinogen Classification"
        )
        classifications = []
        for item in raw_info:
            if item.get("value"):
                classifications.append(
                    {
                        "source": item["name"] if item.get("name") else None,
                        "classification": item["value"],
                    }
                )

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "classification_count": len(classifications),
                "classifications": classifications,
            },
            "metadata": {
                "source": "PubChem PUG View (Carcinogen Classification)",
                "cid": cid,
            },
        }

    def _get_target_organs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get target organs affected by a chemical compound."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "Target Organs")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        raw_info = self._extract_info_from_sections(sections, "Target Organs")
        target_organs = [item["value"] for item in raw_info if item.get("value")]

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "target_organs_count": len(target_organs),
                "target_organs": target_organs,
            },
            "metadata": {
                "source": "PubChem PUG View (Target Organs)",
                "cid": cid,
            },
        }

    def _get_acute_effects(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get acute toxicity effects for a compound.

        Pulls from multiple PUG View headings: Signs and Symptoms,
        Acute Effects, and Exposure Routes to provide comprehensive
        acute toxicity information.
        """
        cid = self._resolve_cid(arguments)

        effects = []
        title = ""

        # Try Signs and Symptoms first (most reliable inline data)
        headings_to_try = [
            ("Signs and Symptoms", "Signs and Symptoms"),
            ("Acute Effects", "Acute Effects"),
            ("Exposure Routes", "Exposure Routes"),
        ]

        for heading, label in headings_to_try:
            try:
                data = self._get_pugview_data(cid, heading)
                record = data.get("Record", {})
                if not title:
                    title = record.get("RecordTitle", "")
                sections = record.get("Section", [])
                raw_info = self._extract_info_from_sections(sections, heading)
                for item in raw_info:
                    if item.get("value"):
                        effects.append(
                            {
                                "source": label,
                                "effect": item["value"][:500],
                            }
                        )
            except Exception:
                continue

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "effects_count": len(effects),
                "acute_effects": effects[:20],
            },
            "metadata": {
                "source": "PubChem PUG View (Acute Effects / Signs and Symptoms)",
                "cid": cid,
            },
        }

    def _get_toxicity_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get comprehensive toxicity summary including multiple toxicity data sections."""
        cid = self._resolve_cid(arguments)

        # Get full toxicity section
        data = self._get_pugview_data(cid, "Toxicity")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        summary_sections = []

        # Walk through sections to get subsection headings and brief info
        for s in sections:
            for ss in s.get("Section", []):
                subsection_name = ss.get("TOCHeading", "")
                sub_items = []
                for sss in ss.get("Section", []):
                    sub_heading = sss.get("TOCHeading", "")
                    info_count = len(sss.get("Information", []))
                    # Get first info item as preview
                    preview = ""
                    infos = sss.get("Information", [])
                    if infos:
                        val = infos[0].get("Value", {})
                        sws = val.get("StringWithMarkup", [])
                        if sws:
                            preview = self._strip_html(sws[0].get("String", ""))[:200]
                    sub_items.append(
                        {
                            "heading": sub_heading,
                            "info_count": info_count,
                            "preview": preview if preview else None,
                        }
                    )
                if sub_items:
                    summary_sections.append(
                        {
                            "section": subsection_name,
                            "topics": sub_items,
                        }
                    )

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "toxicity_sections": summary_sections,
            },
            "metadata": {
                "source": "PubChem PUG View (Toxicity Summary)",
                "cid": cid,
            },
        }
