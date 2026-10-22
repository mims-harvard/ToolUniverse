"""
SABIO-RK Biochemical Reaction Kinetics database tool for ToolUniverse.

SABIO-RK (http://sabiork.h-its.org/) contains information about biochemical
reactions, their kinetic equations with parameters and experimental conditions.

API: https://sabiork.h-its.org/sabioRestWebServices/
No authentication required. Free public access.
"""

import json
import re
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
        if not isinstance(arguments, dict):
            return {"status": "error", "error": "arguments must be an object"}
        allowed = {
            "operation",
            "ec_number",
            "enzyme_name",
            "substrate",
            "organism",
            "product",
            "parameter_type",
            "limit",
            "offset",
        }
        unknown = sorted(set(arguments) - allowed)
        if unknown:
            return {
                "status": "error",
                "error": f"Unsupported parameter(s): {', '.join(unknown)}",
            }
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

        def quoted(value: str) -> str:
            return value.replace("\\", "\\\\").replace('"', '\\"')

        parts = []
        if ec := arguments.get("ec_number", ""):
            parts.append(f"ECNumber:{ec}")
        if ename := arguments.get("enzyme_name", ""):
            parts.append(f'EnzymeName:"{quoted(ename)}"')
        if substrate := arguments.get("substrate", ""):
            parts.append(f'Substrate:"{quoted(substrate)}"')
        if organism := arguments.get("organism", ""):
            parts.append(f'Organism:"{quoted(organism)}"')
        if product := arguments.get("product", ""):
            parts.append(f'Product:"{quoted(product)}"')
        if param_type := arguments.get("parameter_type", ""):
            parts.append(f'ParameterType:"{quoted(param_type)}"')
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
        search_fields = (
            "ec_number",
            "enzyme_name",
            "substrate",
            "organism",
            "product",
            "parameter_type",
        )
        for field in search_fields:
            value = arguments.get(field)
            if value is not None and (not isinstance(value, str) or not value.strip()):
                return {
                    "status": "error",
                    "error": f"{field} must be a non-empty string when provided",
                }
            if isinstance(value, str):
                arguments[field] = value.strip()

        ec_number = arguments.get("ec_number")
        if ec_number and not re.fullmatch(
            r"[0-9]+\.(?:[0-9]+|-)\.(?:[0-9]+|-)\.(?:[0-9]+|-)", ec_number
        ):
            return {
                "status": "error",
                "error": "ec_number must be a four-part EC number such as 1.1.1.1",
            }

        query = self._build_query(arguments)
        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required: ec_number, enzyme_name, substrate, organism, product, or parameter_type",
            }

        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 100",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {"status": "error", "error": "offset must be a non-negative integer"}
        url = "https://sabiork.h-its.org/api/ft/proxy-select"
        params = {
            "q": query,
            "df": "Everything",
            "wt": "json",
            "rows": limit,
            "start": offset,
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
                    "Parameter",
                    "ParameterType",
                    "ParameterUnit",
                    "KineticMechanismType",
                    "PubMedID",
                    "InsertDate",
                    "Json",
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
        if not isinstance(body, dict) or not isinstance(body.get("response"), dict):
            return {
                "status": "error",
                "error": "SABIO-RK Solr returned a malformed response",
            }
        response = body["response"]
        total_count = response.get("numFound")
        returned_start = response.get("start", offset)
        docs = response.get("docs")
        if (
            isinstance(total_count, bool)
            or not isinstance(total_count, int)
            or total_count < 0
            or returned_start != offset
            or not isinstance(docs, list)
            or any(not isinstance(doc, dict) for doc in docs)
            or len(docs) > limit
            or offset + len(docs) > total_count
            or (offset < total_count and not docs)
        ):
            return {
                "status": "error",
                "error": "SABIO-RK Solr returned inconsistent pagination metadata or records",
            }

        # Flatten Solr doc into the legacy {kinetic_laws:[{entry_id,
        # reaction_equation, ec_number, ...}]} shape so callers see no
        # behavioural change. Multi-valued Solr fields come back as lists;
        # join them or pick the first as appropriate.
        def _first(v):
            return v[0] if isinstance(v, list) and v else v

        records = []
        for d in docs:
            entry_id_value = _first(d.get("EntryID"))
            if entry_id_value is None or str(entry_id_value).strip() == "":
                return {
                    "status": "error",
                    "error": "SABIO-RK returned a record without EntryID",
                }
            entry_id = str(entry_id_value)

            source_filter_fields = {
                "ec_number": "ECNumber",
                "enzyme_name": "EnzymeName",
                "substrate": "Substrate",
                "organism": "Organism",
                "product": "Product",
                "parameter_type": "ParameterType",
            }
            for argument_name, source_field in source_filter_fields.items():
                requested = arguments.get(argument_name)
                if not requested:
                    continue
                source_values = d.get(source_field)
                if not isinstance(source_values, list):
                    source_values = [source_values] if source_values is not None else []
                normalized_values = [
                    str(value).casefold()
                    for value in source_values
                    if value is not None
                ]
                requested_normalized = requested.casefold()
                matches = (
                    requested_normalized in normalized_values
                    if argument_name == "ec_number"
                    else any(
                        requested_normalized in source_value
                        for source_value in normalized_values
                    )
                )
                if not matches:
                    return {
                        "status": "error",
                        "error": f"SABIO-RK entry {entry_id} does not satisfy requested {argument_name} filter",
                    }

            raw_record = None
            raw_json = d.get("Json")
            if isinstance(raw_json, list):
                raw_json = raw_json[0] if raw_json else None
            if isinstance(raw_json, str):
                try:
                    raw_record = json.loads(raw_json)
                except json.JSONDecodeError:
                    return {
                        "status": "error",
                        "error": f"SABIO-RK entry {entry_id} contains invalid Json",
                    }
            elif isinstance(raw_json, dict):
                raw_record = raw_json

            if raw_record is not None:
                if (
                    not isinstance(raw_record, dict)
                    or str(raw_record.get("id")) != entry_id
                ):
                    return {
                        "status": "error",
                        "error": f"SABIO-RK entry {entry_id} Json identity mismatch",
                    }
                kinetic_law = raw_record.get("kineticlaw")
                if not isinstance(kinetic_law, dict):
                    return {
                        "status": "error",
                        "error": f"SABIO-RK entry {entry_id} has malformed kinetic law data",
                    }
                raw_parameters = kinetic_law.get("parameter", [])
                if not isinstance(raw_parameters, list) or any(
                    not isinstance(parameter, dict) for parameter in raw_parameters
                ):
                    return {
                        "status": "error",
                        "error": f"SABIO-RK entry {entry_id} has malformed kinetic parameters",
                    }
                parameters = []
                for parameter in raw_parameters:
                    parameter_type = parameter.get("parameter_type", {})
                    unit = parameter.get("unit", {})
                    if not isinstance(parameter_type, dict) or not isinstance(
                        unit, dict
                    ):
                        return {
                            "status": "error",
                            "error": f"SABIO-RK entry {entry_id} has malformed parameter metadata",
                        }
                    parameters.append(
                        {
                            "type": parameter_type.get("name"),
                            "name": parameter.get("name"),
                            "role": parameter.get("role"),
                            "value": parameter.get("start_value"),
                            "unit": unit.get("name"),
                            "normalized_value": parameter.get("n_start_value"),
                            "normalized_unit": unit.get("n_name"),
                            "sbo_term": parameter_type.get("sbo_term"),
                            "species": parameter.get("species"),
                            "comment": parameter.get("comment"),
                        }
                    )
                experimental_conditions = raw_record.get("experimental_conditions")
                publication = raw_record.get("publication")
                enzyme_description = raw_record.get("enzyme_description")
                source_record_complete = True
            else:
                legacy_parameters = d.get("Parameter")
                parameters = (
                    legacy_parameters if isinstance(legacy_parameters, list) else []
                )
                experimental_conditions = None
                publication = None
                enzyme_description = None
                source_record_complete = False

            records.append(
                {
                    "entry_id": entry_id,
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
                    "parameters": parameters,
                    "parameter_types": d.get("ParameterType")
                    if isinstance(d.get("ParameterType"), list)
                    else [],
                    "parameter_units": d.get("ParameterUnit")
                    if isinstance(d.get("ParameterUnit"), list)
                    else [],
                    "mechanism_type": _first(d.get("KineticMechanismType")),
                    "pubmed_id": _first(d.get("PubMedID")),
                    "insert_date": _first(d.get("InsertDate")),
                    "experimental_conditions": experimental_conditions,
                    "publication": publication,
                    "enzyme_description": enzyme_description,
                    "source_record": raw_record,
                    "source_record_complete": source_record_complete,
                }
            )

        has_more = offset + len(records) < total_count

        return {
            "status": "success",
            "data": {
                "query": query,
                "kinetic_laws": records,
                "total_count": total_count,
                "returned_count": len(records),
                "offset": offset,
                "has_more": has_more,
                "next_offset": offset + len(records) if has_more else None,
                "result_set_complete": offset == 0 and len(records) == total_count,
            },
            "metadata": {
                "source": "SABIO-RK (Solr backend)",
                "url": "https://sabiork.h-its.org/api/ft/proxy-select",
                "page_complete": True,
                "source_records_complete": all(
                    record["source_record_complete"] for record in records
                ),
                "note": f"Showing records {offset} through {offset + len(records) - 1} of {total_count} kinetic laws"
                if records
                else f"No records returned at offset {offset}; total matching kinetic laws: {total_count}",
            },
        }
