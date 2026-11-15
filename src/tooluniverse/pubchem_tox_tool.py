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

# An acute-effect description can run long. The cut is kept, because these
# lists are read by an agent and a full HSDB narrative is pages of prose, but
# it is disclosed per row rather than applied in silence at 500 characters.
EFFECT_CHARACTERS = 2000

# The summary tool stays a summary: a preview per topic plus the first few
# statements, both with the cut disclosed. The per-section tools return the
# statements in full.
PREVIEW_CHARACTERS = 500
STATEMENTS_PER_TOPIC = 5
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
        elif self.endpoint == "ecotoxicity_values":
            return self._get_ecotoxicity_values(arguments)
        elif self.endpoint == "human_toxicity_values":
            return self._get_human_toxicity_values(arguments)
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
        # PubChem's name->CID lookup itself 404s when the name doesn't
        # resolve at all (confirmed live) -- raise that as a distinct
        # ValueError here, before it can reach run()'s generic
        # HTTPError(404) handler, which otherwise conflates "compound name
        # never resolved" with "compound resolved fine but this specific
        # toxicity heading is absent for it" into the identical misleading
        # "This heading may not exist for this compound" message.
        if response.status_code == 404:
            raise ValueError(f"No compound found for name: {compound_name}")
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

    @staticmethod
    def _paginate(
        arguments: Dict[str, Any], values: List[Any], default_limit: int
    ) -> tuple[List[Any], Dict[str, Any]]:
        """Page locally extracted PUG View statements without hiding the remainder."""
        limit = arguments.get("limit", default_limit)
        if limit is None:
            limit = default_limit
        offset = arguments.get("offset", 0)
        if offset is None:
            offset = 0
        if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
            raise ValueError("limit must be a positive integer")
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            raise ValueError("offset must be a non-negative integer")

        page = values[offset : offset + limit]
        has_more = offset + len(page) < len(values)
        return page, {
            "total_results": len(values),
            "returned": len(page),
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": offset + len(page) if has_more else None,
        }

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

    @staticmethod
    def _reference_index(record: Dict) -> Dict[Any, Dict]:
        """`Record.Reference` keyed by ReferenceNumber.

        Every statement in a PUG View record carries a `ReferenceNumber` and
        the record carries the references it points into. None of it reached
        the caller: an LD50 of "500 mg/kg" arrived with no way to tell whether
        ECHA, HSDB or ChemIDplus said so, which for a toxicity value is most
        of what decides whether it can be used. The license note travels with
        the source, and PubChem attaches one to several of these collections.
        """
        index = {}
        for ref in record.get("Reference") or []:
            if not isinstance(ref, dict):
                continue
            index[ref.get("ReferenceNumber")] = {
                "source_name": ref.get("SourceName"),
                "source_id": ref.get("SourceID"),
                "reference_name": ref.get("Name"),
                "url": ref.get("URL"),
                "description": ref.get("Description"),
                "license_note": ref.get("LicenseNote"),
                "license_url": ref.get("LicenseURL"),
                "ancestor_node_id": ref.get("ANID"),
            }
        return index

    def _extract_info_from_sections(
        self, sections: List[Dict], heading: str, references: Dict[Any, Dict] = None
    ) -> List[Dict]:
        """Find sections matching heading recursively and extract their Information entries.

        PubChem packs every statement of one notification group into a single
        Information entry holding N StringWithMarkup elements, so reading only
        element 0 dropped the rest. Because GHS codes are ordered numerically
        and physical hazards (H2xx) sort ahead of health hazards (H3xx), that
        systematically discarded carcinogenicity and mutagenicity: benzene came
        back as H225/H401 -- flammable and toxic to aquatic life -- with H350
        "May cause cancer" among the fourteen statements silently lost.
        """
        references = references or {}
        matched = self._find_sections_recursive(sections, heading)
        results = []
        for section in matched:
            for info in section.get("Information", []):
                name = info.get("Name", "")
                val = info.get("Value", {})
                reference = references.get(info.get("ReferenceNumber"))
                strings = val.get("StringWithMarkup") or []
                for sw in strings:
                    markups = sw.get("Markup", [])
                    extras = [m.get("Extra", "") for m in markups if m.get("Extra")]
                    entry = {
                        "name": name,
                        "value": self._strip_html(sw.get("String", "")),
                        "reference_number": info.get("ReferenceNumber"),
                        "reference": reference,
                    }
                    if extras:
                        entry["pictogram_labels"] = extras
                    results.append(entry)
                if strings:
                    continue
                # Not every statement is a string. PubChem answers some
                # sections with the address of an external table instead --
                # arsenic trioxide's Acute Effects is
                # `collection=chemidplus&query_type=sid&query=134991231` --
                # and a loop over StringWithMarkup alone yielded nothing for
                # it, so "the data is in a table over there" was reported as
                # no data at all. The address is reported now; it is not
                # fetched, because that is a different request to a different
                # endpoint and the caller should know it is being made.
                external = val.get("ExternalTableName")
                if external:
                    results.append(
                        {
                            "name": name,
                            "value": None,
                            "reference_number": info.get("ReferenceNumber"),
                            "reference": reference,
                            "external_table": external,
                            "note": (
                                "PubChem holds this section's data in an "
                                "external table rather than inline. The table "
                                "address is in external_table; it has not been "
                                "fetched. An empty value here is not evidence "
                                "that no data exists."
                            ),
                        }
                    )
                elif val.get("Number") is not None:
                    results.append(
                        {
                            "name": name,
                            "value": ", ".join(str(n) for n in val["Number"]),
                            "unit": val.get("Unit"),
                            "reference_number": info.get("ReferenceNumber"),
                            "reference": reference,
                        }
                    )
        return results

    def _statements_in_subtree(
        self, section: Dict, references: Dict[Any, Dict]
    ) -> List[Dict]:
        """Every statement under `section`, at any depth, with its source."""
        found = []
        for info in section.get("Information", []) or []:
            reference = references.get(info.get("ReferenceNumber")) or {}
            for sw in info.get("Value", {}).get("StringWithMarkup") or []:
                found.append(
                    {
                        "name": info.get("Name") or None,
                        "value": self._strip_html(sw.get("String", "")),
                        "source_name": reference.get("source_name"),
                        "source_url": reference.get("url"),
                        "reference": reference or None,
                    }
                )
        for child in section.get("Section", []) or []:
            found.extend(self._statements_in_subtree(child, references))
        return found

    @staticmethod
    def _value_records(raw_info: List[Dict]) -> List[Dict]:
        """One statement per row, with the source that stated it.

        These lists used to be bare strings: "LD50 Rat oral 500 mg/kg" and no
        way to tell whether ECHA, HSDB or ChemIDplus said it, nor what licence
        it carries. The statement keeps its place and its text under `value`;
        what is added beside it is who said so.
        """
        records = []
        for item in raw_info:
            if not item.get("value") and not item.get("external_table"):
                continue
            reference = item.get("reference") or {}
            records.append(
                {
                    "value": item.get("value"),
                    "name": item.get("name") or None,
                    "source_name": reference.get("source_name"),
                    "source_url": reference.get("url"),
                    "license_note": reference.get("license_note"),
                    "license_url": reference.get("license_url"),
                    "reference": reference or None,
                    **(
                        {
                            "external_table": item["external_table"],
                            "note": item.get("note"),
                        }
                        if item.get("external_table")
                        else {}
                    ),
                    **({"unit": item["unit"]} if item.get("unit") else {}),
                }
            )
        return records

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
        ghs_info = self._extract_info_from_sections(
            sections, "GHS Classification", self._reference_index(record)
        )

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
            sections, "Non-Human Toxicity Values", self._reference_index(record)
        )
        tox_values = self._value_records(raw_info)
        page, pagination = self._paginate(arguments, tox_values, 30)

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "toxicity_values_count": len(page),
                "total_toxicity_values": len(tox_values),
                "toxicity_values": page,
            },
            "metadata": {
                "source": "PubChem PUG View (Non-Human Toxicity Values)",
                "cid": cid,
                **pagination,
            },
        }

    def _get_ecotoxicity_values(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get aquatic/environmental ecotoxicity values (LC50/EC50 for fish,
        crustaceans, protozoa, etc.) from the 'Ecotoxicity Values' heading."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "Ecotoxicity Values")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        raw_info = self._extract_info_from_sections(
            sections, "Ecotoxicity Values", self._reference_index(record)
        )
        eco_values = self._value_records(raw_info)
        page, pagination = self._paginate(arguments, eco_values, 30)

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "ecotoxicity_values_count": len(page),
                "total_ecotoxicity_values": len(eco_values),
                "ecotoxicity_values": page,
            },
            "metadata": {
                "source": "PubChem PUG View (Ecotoxicity Values)",
                "cid": cid,
                **pagination,
            },
        }

    def _get_human_toxicity_values(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get human toxicity values (lethal oral doses, IDLH air
        concentrations, fatal exposure thresholds) from the
        'Human Toxicity Values' heading."""
        cid = self._resolve_cid(arguments)

        data = self._get_pugview_data(cid, "Human Toxicity Values")
        record = data.get("Record", {})
        title = record.get("RecordTitle", "")

        sections = record.get("Section", [])
        raw_info = self._extract_info_from_sections(
            sections, "Human Toxicity Values", self._reference_index(record)
        )
        human_values = self._value_records(raw_info)
        page, pagination = self._paginate(arguments, human_values, 30)

        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "human_toxicity_values_count": len(page),
                "total_human_toxicity_values": len(human_values),
                "human_toxicity_values": page,
            },
            "metadata": {
                "source": "PubChem PUG View (Human Toxicity Values)",
                "cid": cid,
                **pagination,
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
            sections, "Carcinogen Classification", self._reference_index(record)
        )
        classifications = []
        for item in raw_info:
            if not item.get("value"):
                continue
            reference = item.get("reference") or {}
            classifications.append(
                {
                    # `source` here is the Information entry's own Name --
                    # "IARC Carcinogenic Agents" -- which is not the same
                    # thing as the collection PubChem took it from. Both are
                    # reported, under names that say which is which.
                    "source": item["name"] if item.get("name") else None,
                    "classification": item["value"],
                    "source_name": reference.get("source_name"),
                    "source_url": reference.get("url"),
                    "license_note": reference.get("license_note"),
                    "license_url": reference.get("license_url"),
                    "reference": reference or None,
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
        raw_info = self._extract_info_from_sections(
            sections, "Target Organs", self._reference_index(record)
        )
        target_organs = self._value_records(raw_info)

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
                raw_info = self._extract_info_from_sections(
                    sections, heading, self._reference_index(record)
                )
                for item in raw_info:
                    if not item.get("value"):
                        continue
                    reference = item.get("reference") or {}
                    text = item["value"]
                    effects.append(
                        {
                            "source": label,
                            # The cut used to be silent at 500 characters, in
                            # the middle of a clinical sign description. It is
                            # longer now and it says when it happened.
                            "effect": text[:EFFECT_CHARACTERS],
                            "effect_truncated": len(text) > EFFECT_CHARACTERS,
                            "effect_length": len(text),
                            "source_name": reference.get("source_name"),
                            "source_url": reference.get("url"),
                            "reference": reference or None,
                        }
                    )
            except Exception:
                continue

        page, pagination = self._paginate(arguments, effects, 20)
        return {
            "status": "success",
            "data": {
                "cid": cid,
                "compound_name": title,
                "effects_count": len(page),
                "total_acute_effects": len(effects),
                "acute_effects": page,
            },
            "metadata": {
                "source": "PubChem PUG View (Acute Effects / Signs and Symptoms)",
                "cid": cid,
                **pagination,
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
        references = self._reference_index(record)
        summary_sections = []

        # Walk through sections to get subsection headings and brief info.
        # `info_count` used to count only the Information entries hanging
        # directly off a topic, three levels down and no deeper, so a topic
        # whose statements sit in a further subsection was reported as having
        # none. It counts the whole subtree now, and the section's own
        # description and source link -- which PubChem answers for 25 of
        # these topics and which say what the section IS -- are carried
        # instead of being passed over for a 200-character preview of the
        # first statement in it.
        for s in sections:
            for ss in s.get("Section", []):
                subsection_name = ss.get("TOCHeading", "")
                sub_items = []
                for sss in ss.get("Section", []) or [ss]:
                    sub_heading = sss.get("TOCHeading", "")
                    statements = self._statements_in_subtree(sss, references)
                    preview = statements[0]["value"] if statements else ""
                    sub_items.append(
                        {
                            "heading": sub_heading,
                            "description": sss.get("Description"),
                            "url": sss.get("URL"),
                            "info_count": len(statements),
                            "preview": preview[:PREVIEW_CHARACTERS] or None,
                            "preview_truncated": len(preview) > PREVIEW_CHARACTERS,
                            # The statements themselves, so a topic reported
                            # as having 7 of them can be read rather than
                            # only counted. Each one says who stated it.
                            "statements": statements[:STATEMENTS_PER_TOPIC],
                            "statements_truncated": len(statements)
                            > STATEMENTS_PER_TOPIC,
                        }
                    )
                if sub_items:
                    summary_sections.append(
                        {
                            "section": subsection_name,
                            "description": ss.get("Description"),
                            "url": ss.get("URL"),
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
