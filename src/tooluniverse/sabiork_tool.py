"""
SABIO-RK Biochemical Reaction Kinetics database tool for ToolUniverse.

SABIO-RK (http://sabiork.h-its.org/) contains information about biochemical
reactions, their kinetic equations with parameters and experimental conditions.

API: https://sabiork.h-its.org/sabioRestWebServices/
No authentication required. Free public access.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

SABIORK_BASE = "https://sabiork.h-its.org/sabioRestWebServices"

# SBO term mapping for kinetic parameter types
_SBO_PARAM_TYPE = {
    "SBO:0000025": "kcat",
    "SBO:0000027": "Km",
    "SBO:0000261": "Ki",
    "SBO:0000302": "kcat/Km",
    "SBO:0000186": "Vmax",
    "SBO:0000320": "specific_activity",
    "SBO:0000022": "forward rate constant",
    "SBO:0000038": "reverse rate constant",
    "SBO:0000048": "forward unimolecular rate constant",
}

# SABIO-RK unit normalization
_UNIT_MAP = {
    "M": "M",
    "swedgeone": "s^{-1}",
    "Mwedgeoneswedgeone": "M^{-1}*s^{-1}",
}


def _is_no_data_response(text: str) -> bool:
    """Check if SABIO-RK returned a 'no data found' plain-text response."""
    return "no data found" in text.lower() or not text.strip().startswith("<")


def _parse_entry_ids(xml_text: str) -> List[str]:
    """Parse entry IDs from SABIO-RK XML response."""
    root = ET.fromstring(xml_text)
    return [el.text for el in root.findall(".//SabioEntryID") if el.text]


def _extract_annotations(reaction_el, ns: dict) -> Dict[str, str]:
    """Extract identifiers from reaction annotations."""
    annotations: Dict[str, str] = {}
    rdf_ns = ns.get("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#")
    for li in reaction_el.findall(f".//{{{rdf_ns}}}li"):
        resource = li.get(f"{{{rdf_ns}}}resource", "")
        if "ec-code" in resource:
            annotations["ec_number"] = resource.split("/")[-1]
        elif "kegg.reaction" in resource:
            annotations["kegg_reaction"] = resource.split("/")[-1]
        elif "sabiork.reaction" in resource:
            annotations["sabiork_reaction_id"] = resource.split("/")[-1]
        elif "bto/" in resource:
            annotations["tissue_bto"] = resource.split("/")[-1]
        elif "taxonomy" in resource:
            annotations["taxonomy_id"] = resource.split("/")[-1]
        elif "pubmed" in resource:
            annotations.setdefault("pubmed_ids", [])
            annotations["pubmed_ids"].append(resource.split("/")[-1])
    return annotations


def _parse_sbml_kinetics(xml_text: str) -> List[Dict[str, Any]]:
    """Parse SBML XML from SABIO-RK into structured kinetic law records."""
    ns = {
        "sbml": "http://www.sbml.org/sbml/level3/version1/core",
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    }

    root = ET.fromstring(xml_text)

    # Build species ID -> name map
    species_map: Dict[str, str] = {}
    for sp in root.findall(".//sbml:species", ns):
        sp_id = sp.get("id", "")
        sp_name = sp.get("name", sp_id)
        species_map[sp_id] = sp_name

    # Parse reactions
    records: List[Dict[str, Any]] = []
    reactions = root.findall(".//sbml:reaction", ns)

    for rxn in reactions:
        annotations = _extract_annotations(rxn, ns)

        # Substrates and products
        substrates = []
        for sr in rxn.findall(".//sbml:listOfReactants/sbml:speciesReference", ns):
            sp_id = sr.get("species", "")
            substrates.append(species_map.get(sp_id, sp_id))

        products = []
        for sr in rxn.findall(".//sbml:listOfProducts/sbml:speciesReference", ns):
            sp_id = sr.get("species", "")
            products.append(species_map.get(sp_id, sp_id))

        # Kinetic parameters
        parameters: List[Dict[str, Any]] = []
        for lp in rxn.findall(".//sbml:localParameter", ns):
            sbo = lp.get("sboTerm", "")
            param_type = _SBO_PARAM_TYPE.get(sbo, sbo)
            param_name = lp.get("name", lp.get("id", ""))
            value_str = lp.get("value", "")
            unit_raw = lp.get("units", "")

            unit = _UNIT_MAP.get(unit_raw, unit_raw)

            try:
                value = float(value_str)
            except (ValueError, TypeError):
                value = value_str

            parameters.append(
                {
                    "type": param_type,
                    "name": param_name,
                    "value": value,
                    "unit": unit,
                    "sbo_term": sbo,
                }
            )

        record: Dict[str, Any] = {
            "substrates": substrates,
            "products": products,
            "parameters": parameters,
        }
        record.update(annotations)
        records.append(record)

    return records


@register_tool("SABIORKTool")
class SABIORKTool(BaseTool):
    """
    Tool for querying SABIO-RK biochemical reaction kinetics database.

    Retrieves kinetic parameters (Km, kcat, Vmax, Ki, etc.) with experimental
    conditions, organism, and literature references.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        operation = arguments.get("operation", "") or self.get_schema_const_operation()
        dispatch = {
            "search_reactions": self._search_reactions,
        }
        handler = dispatch.get(operation)
        if handler is None:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: {', '.join(dispatch)}",
            }
        try:
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SABIO-RK API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to SABIO-RK API",
            }
        except ET.ParseError as e:
            return {
                "status": "error",
                "error": f"Failed to parse SABIO-RK XML response: {e}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"SABIO-RK query failed: {e}",
            }

    def _build_query(self, arguments: Dict[str, Any]) -> str:
        """Build SABIO-RK search query string from arguments."""
        parts = []
        ec = arguments.get("ec_number", "")
        if ec:
            parts.append(f"ecnumber:{ec}")
        ename = arguments.get("enzyme_name", "")
        if ename:
            parts.append(f'EnzymeName:"{ename}"')
        substrate = arguments.get("substrate", "")
        if substrate:
            parts.append(f'Substrate:"{substrate}"')
        organism = arguments.get("organism", "")
        if organism:
            parts.append(f'Organism:"{organism}"')
        product = arguments.get("product", "")
        if product:
            parts.append(f'Product:"{product}"')
        param_type = arguments.get("parameter_type", "")
        if param_type:
            parts.append(f'parametertype:"{param_type}"')
        if not parts:
            return ""
        return " AND ".join(parts)

    def _search_reactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SABIO-RK for kinetic laws matching the query."""
        query = self._build_query(arguments)
        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required: ec_number, enzyme_name, substrate, organism, or product",
            }

        limit = int(arguments.get("limit", 20))

        # Step 1: Get entry IDs
        url = f"{SABIORK_BASE}/searchKineticLaws/entryIDs?q={query}"
        resp = requests.get(url, timeout=self.timeout)
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"SABIO-RK search returned HTTP {resp.status_code}",
            }

        if _is_no_data_response(resp.text):
            return {
                "status": "success",
                "data": {
                    "query": query,
                    "kinetic_laws": [],
                    "total_count": 0,
                    "returned_count": 0,
                },
                "metadata": {"source": "SABIO-RK", "url": url},
            }

        entry_ids = _parse_entry_ids(resp.text)
        total_count = len(entry_ids)

        # Step 2: Fetch SBML for limited set of entries
        fetch_ids = entry_ids[:limit]
        ids_str = ",".join(fetch_ids)
        sbml_url = f"{SABIORK_BASE}/kineticLaws?kinlawids={ids_str}"
        resp2 = requests.get(sbml_url, timeout=self.timeout)
        if resp2.status_code != 200:
            return {
                "status": "error",
                "error": f"SABIO-RK SBML fetch returned HTTP {resp2.status_code}",
            }

        records = _parse_sbml_kinetics(resp2.text)

        # Attach entry IDs to records
        for i, rec in enumerate(records):
            if i < len(fetch_ids):
                rec["entry_id"] = fetch_ids[i]

        return {
            "status": "success",
            "data": {
                "query": query,
                "kinetic_laws": records,
                "total_count": total_count,
                "returned_count": len(records),
            },
            "metadata": {
                "source": "SABIO-RK",
                "url": f"http://sabiork.h-its.org/",
                "note": f"Showing {len(records)} of {total_count} kinetic laws",
            },
        }
