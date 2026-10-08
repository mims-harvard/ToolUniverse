"""
SABIO-RK Biochemical Reaction Kinetics database tool for ToolUniverse.

SABIO-RK (http://sabiork.h-its.org/) contains information about biochemical
reactions, their kinetic equations with parameters and experimental conditions.

API: https://sabiork.h-its.org/sabioRestWebServices/
No authentication required. Free public access.
"""

import json
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


def parse_solr_kinetic_law(json_field: Any) -> Dict[str, Any]:
    """Pull the measured constants out of a Solr doc's ``Json`` field.

    The Solr index (``/api/ft/proxy-select``) has no ``Parameter`` or
    ``ParameterUnit`` field; asking for them returns nothing. The values live
    in ``Json`` (a JSON string, ~10 kB per entry) under
    ``kineticlaw.parameter[]``. Only constants with a reported value are kept:
    assay concentration ranges (role "Variable") and the value-less
    placeholders SABIO-RK stores for some laws would only add noise.
    ``value``/``unit`` are as reported; ``value_si``/``unit_si`` are SABIO-RK's
    own normalisation (Km in M, kcat in s^(-1)), which is what aggregation
    across entries needs.
    """
    if isinstance(json_field, list):
        json_field = json_field[0] if json_field else None
    try:
        law = json.loads(json_field) if isinstance(json_field, str) else json_field
    except ValueError:
        law = None
    if not isinstance(law, dict):
        return {"parameters": [], "conditions": {}}

    parameters = []
    for raw in (law.get("kineticlaw") or {}).get("parameter") or []:
        if not isinstance(raw, dict) or raw.get("start_value") is None:
            continue
        if raw.get("role") != "Constant":
            continue
        unit = raw.get("unit") or {}
        species_key = (raw.get("species") or {}).get("species_key") or ""
        # "1 | Ethanol | Substrate" -> "Ethanol"
        key_parts = [part.strip() for part in species_key.split("|")]
        entry = {
            "type": (raw.get("parameter_type") or {}).get("name") or raw.get("name"),
            "name": raw.get("name"),
            "species": key_parts[1] if len(key_parts) > 1 else None,
            "value": raw.get("start_value"),
            "unit": unit.get("name"),
            "value_si": raw.get("n_start_value"),
            "unit_si": unit.get("n_name"),
        }
        if raw.get("end_value") is not None:
            entry["end_value"] = raw["end_value"]
        if raw.get("standard_deviation") is not None:
            entry["standard_deviation"] = raw["standard_deviation"]
        parameters.append(entry)

    conditions_raw = law.get("experimental_conditions") or {}
    conditions = {}
    ph = (conditions_raw.get("envvar_ph") or {}).get("start_value")
    if ph is not None:
        conditions["ph"] = ph
    temperature = conditions_raw.get("envvar_temperature") or {}
    if temperature.get("start_value") is not None:
        conditions["temperature"] = temperature["start_value"]
        conditions["temperature_unit"] = temperature.get("unit")
    return {"parameters": parameters, "conditions": conditions}


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
        """Build SABIO-RK Solr query string from arguments.

        The new Solr endpoint uses Title-Cased field names matching the
        Solr schema (ECNumber, EnzymeName, Substrate, Organism, Product,
        ParameterType). Multi-word values must be quoted.
        """
        parts = []
        if ec := arguments.get("ec_number", ""):
            parts.append(f"ECNumber:{ec}")
        if ename := arguments.get("enzyme_name", ""):
            parts.append(f'EnzymeName:"{ename}"')
        if substrate := arguments.get("substrate", ""):
            parts.append(f'Substrate:"{substrate}"')
        if organism := arguments.get("organism", ""):
            parts.append(f'Organism:"{organism}"')
        if product := arguments.get("product", ""):
            parts.append(f'Product:"{product}"')
        if param_type := arguments.get("parameter_type", ""):
            parts.append(f'ParameterType:"{param_type}"')
        if not parts:
            return ""
        return " AND ".join(parts)

    def _search_reactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search SABIO-RK kinetic laws via the new Solr-backed endpoint.

        The legacy /sabioRestWebServices/searchKineticLaws/entryIDs?q=
        endpoint was retired in 2025; the SPA at sabiork.h-its.org now
        proxies queries to a Solr index at /api/ft/proxy-select. Each
        document already contains the kinetics fields we previously had
        to re-fetch as SBML, so the two-step fetch is collapsed into one
        Solr call.
        """
        query = self._build_query(arguments)
        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required: ec_number, enzyme_name, substrate, organism, or product",
            }

        limit = int(arguments.get("limit", 20))
        url = "https://sabiork.h-its.org/api/ft/proxy-select"
        params = {
            "q": query,
            "df": "Everything",
            "wt": "json",
            "rows": limit,
            "fl": ",".join(
                [
                    "EntryID",
                    "SabioReactionID",
                    "ReactionEquation",
                    "ECNumber",
                    "EnzymeName",
                    "Organism",
                    "Tissue",
                    "Substrate",
                    "Product",
                    "Catalyst",
                    "ParameterType",
                    "Json",
                    "KineticMechanismType",
                    "PubMedID",
                    "InsertDate",
                ]
            ),
        }
        try:
            resp = requests.get(url, params=params, timeout=self.timeout)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"SABIO-RK Solr timed out after {self.timeout}s",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"SABIO-RK Solr returned HTTP {resp.status_code}: {resp.text[:200]}",
            }

        try:
            body = resp.json()
        except ValueError:
            return {
                "status": "error",
                "error": "SABIO-RK Solr returned non-JSON response",
            }
        response = body.get("response", {}) or {}
        total_count = response.get("numFound", 0)
        docs = response.get("docs", []) or []

        # Flatten Solr doc into the legacy {kinetic_laws:[{entry_id,
        # reaction_equation, ec_number, ...}]} shape so callers see no
        # behavioural change. Multi-valued Solr fields come back as lists;
        # join them or pick the first as appropriate.
        def _first(v):
            return v[0] if isinstance(v, list) and v else v

        records = []
        for d in docs:
            law = parse_solr_kinetic_law(d.get("Json"))
            records.append(
                {
                    "entry_id": str(_first(d.get("EntryID")) or ""),
                    "sabio_reaction_id": str(_first(d.get("SabioReactionID")) or ""),
                    "reaction_equation": _first(d.get("ReactionEquation")),
                    "ec_number": _first(d.get("ECNumber")),
                    "enzyme_name": _first(d.get("EnzymeName")),
                    "organism": _first(d.get("Organism")),
                    "tissue": _first(d.get("Tissue")),
                    "substrates": d.get("Substrate")
                    if isinstance(d.get("Substrate"), list)
                    else [d.get("Substrate")]
                    if d.get("Substrate")
                    else [],
                    "products": d.get("Product")
                    if isinstance(d.get("Product"), list)
                    else [d.get("Product")]
                    if d.get("Product")
                    else [],
                    "catalysts": d.get("Catalyst")
                    if isinstance(d.get("Catalyst"), list)
                    else [d.get("Catalyst")]
                    if d.get("Catalyst")
                    else [],
                    "parameters": law["parameters"],
                    "parameter_types": d.get("ParameterType")
                    if isinstance(d.get("ParameterType"), list)
                    else [],
                    "parameter_units": sorted(
                        {p["unit"] for p in law["parameters"] if p.get("unit")}
                    ),
                    "conditions": law["conditions"],
                    "mechanism_type": _first(d.get("KineticMechanismType")),
                    "pubmed_id": _first(d.get("PubMedID")),
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "kinetic_laws": records,
                "total_count": total_count,
                "returned_count": len(records),
            },
            "metadata": {
                "source": "SABIO-RK (Solr backend)",
                "url": "https://sabiork.h-its.org/api/ft/proxy-select",
                "note": f"Showing {len(records)} of {total_count} kinetic laws",
            },
        }
