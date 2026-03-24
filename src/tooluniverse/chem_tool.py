"""
ChEMBL API Tools

This module provides tools for accessing the ChEMBL database:
- ChEMBLTool: Specialized tool for similarity search
- ChEMBLRESTTool: Generic REST API tool for ChEMBL endpoints
"""

import requests
from urllib.parse import quote
from typing import Any, Dict, Optional

# from rdkit import Chem
from .base_tool import BaseTool
from .tool_registry import register_tool
from .http_utils import request_with_retry
from indigo import Indigo


@register_tool("ChEMBLRESTTool")
class ChEMBLRESTTool(BaseTool):
    """
    Generic ChEMBL REST API tool.
    Wrapper for ChEMBL API endpoints defined in chembl_tools.json.
    Supports all ChEMBL data resources: molecules, targets, assays, activities, drugs, etc.
    """

    def __init__(self, tool_config: Dict):
        super().__init__(tool_config)
        self.base_url = "https://www.ebi.ac.uk/chembl/api/data"
        self.session = requests.Session()
        self.session.headers.update(
            {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        )
        self.timeout = 30

    def _build_url(self, args: Dict[str, Any]) -> str:
        """Build URL from endpoint template and arguments"""
        endpoint_template = self.tool_config.get("fields", {}).get("endpoint", "")
        tool_name = self.tool_config.get("name", "")

        if endpoint_template:
            url = endpoint_template
            # Feature-120B-003: normalize molecule_chembl_id → chembl_id for URL template
            if (
                "{chembl_id}" in url
                and "chembl_id" not in args
                and "molecule_chembl_id" in args
            ):
                args = dict(args, chembl_id=args["molecule_chembl_id"])
            # Replace placeholders in URL
            for k, v in args.items():
                url = url.replace(f"{{{k}}}", str(v))
            # Feature-31A-03 fix: /drug.json does not support pref_name__icontains filtering
            # (ChEMBL server silently ignores it). When a name query is given, route to
            # /molecule.json which supports full text filtering.
            if url.endswith("/drug.json") and (
                args.get("query") or args.get("q") or args.get("pref_name__contains")
            ):
                url = url.replace("/drug.json", "/molecule.json")
            # If URL doesn't start with http, prepend base_url
            if not url.startswith("http"):
                url = self.base_url + url
            return url

        # Build URL based on tool name patterns
        if tool_name.startswith("ChEMBL_get_molecule"):
            # Feature-120B-003: accept molecule_chembl_id as alias for chembl_id
            chembl_id = args.get("chembl_id") or args.get("molecule_chembl_id", "")
            if chembl_id:
                return f"{self.base_url}/molecule/{chembl_id}.json"
        elif tool_name.startswith("ChEMBL_get_target"):
            target_id = args.get("target_chembl_id", "")
            if target_id:
                return f"{self.base_url}/target/{target_id}.json"
        elif tool_name.startswith("ChEMBL_get_assay"):
            assay_id = args.get("assay_chembl_id", "")
            if assay_id:
                return f"{self.base_url}/assay/{assay_id}.json"
        elif tool_name.startswith("ChEMBL_get_activity"):
            activity_id = args.get("activity_id", "")
            if activity_id:
                return f"{self.base_url}/activity/{activity_id}.json"
        elif tool_name.startswith("ChEMBL_get_drug"):
            drug_id = args.get("drug_chembl_id", "")
            if drug_id:
                return f"{self.base_url}/drug/{drug_id}.json"

        return self.base_url

    def _build_params(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Build query parameters for ChEMBL API"""
        params = {}
        self.tool_config.get("name", "")

        # ChEMBL API uses query parameters for filtering
        # Common parameters: limit, offset, format, ordering
        # max_results is an alias for limit
        if "max_results" in args and "limit" not in args:
            params["limit"] = args["max_results"]
        if "limit" in args:
            params["limit"] = args["limit"]
        if "offset" in args:
            params["offset"] = args["offset"]
        if "format" in args:
            params["format"] = args["format"]
        else:
            # Feature-26B-07: for image endpoints, apply default "svg" from the JSON
            # schema rather than "json" (image endpoints don't accept format=json).
            tool_name = self.tool_config.get("name", "")
            endpoint = self.tool_config.get("fields", {}).get("endpoint", "")
            is_image = (
                "get_molecule_image" in tool_name.lower() or "/image/" in endpoint
            )
            if is_image:
                # Apply the JSON schema default for image format
                schema_props = (
                    self.tool_config.get("parameter", {})
                    .get("properties", {})
                    .get("format", {})
                )
                params["format"] = schema_props.get("default", "svg")
            else:
                params["format"] = "json"
        # Optional field projection to reduce payload size on heavy endpoints.
        # ChEMBL supports projection via the `only` query parameter.
        # We accept ToolUniverse argument name `fields` and map it to `only`.
        # Power users can also pass `only` directly.
        only_value = args.get("only", None)
        fields_value = args.get("fields", None)
        projection_value = only_value if only_value is not None else fields_value
        if projection_value is not None:
            if isinstance(projection_value, (list, tuple)):
                params["only"] = ",".join(str(f) for f in projection_value)
            else:
                params["only"] = str(projection_value)
        if "ordering" in args:
            params["ordering"] = args["ordering"]

        # Feature-26B-03/13: Map `q` to `pref_name__icontains` so that intuitive
        # text searches work (ChEMBL uses field__lookup syntax, not q=).
        # Also map `query` and `pref_name__contains` as aliases.
        name_query = (
            args.get("q") or args.get("query") or args.get("pref_name__contains")
        )
        if name_query is not None:
            params["pref_name__icontains"] = name_query

        # Feature-30B-05: Map `drug_chembl_id` to `molecule_chembl_id__exact` so
        # ChEMBL_get_drug_mechanisms accepts the same ID param as ChEMBL_get_drug.
        # Feature-32B-07: Also accept `molecule_chembl_id` as an alias.
        # Feature-39A-01: Also accept `chembl_id` as a common alias.
        # Feature-40B-02: For mechanism endpoints, use `parent_molecule_chembl_id` — the
        # /mechanism.json endpoint indexes records by the parent/active molecule, not
        # individual salt/prodrug forms. molecule_chembl_id__exact returns 0 results.
        drug_id = (
            args.get("drug_chembl_id")
            or args.get("molecule_chembl_id")
            or args.get("chembl_id")
        )
        tool_name_local = self.tool_config.get("name", "")
        if drug_id is not None:
            if tool_name_local in (
                "ChEMBL_get_drug_mechanisms",
                "ChEMBL_search_mechanisms",
            ):
                params["parent_molecule_chembl_id"] = drug_id
            else:
                params["molecule_chembl_id__exact"] = drug_id

        # Map target_chembl_id and assay_chembl_id to __exact API params
        # when used as query filters (not as URL path components)
        target_id = args.get("target_chembl_id")
        # Feature-120B-001: only exclude ChEMBL_get_target (single lookup), not
        # ChEMBL_get_target_activities or ChEMBL_get_target_assays which need the filter
        if target_id is not None and tool_name_local not in (
            "ChEMBL_get_target",
            "ChEMBL_search_targets",
        ):
            params["target_chembl_id__exact"] = target_id

        assay_id = args.get("assay_chembl_id")
        if assay_id is not None and not tool_name_local.startswith("ChEMBL_get_assay"):
            params["assay_chembl_id__exact"] = assay_id

        # Feature-79A: mechanism_of_action__contains → __icontains for case-insensitive search
        moa_filter = args.get("mechanism_of_action__contains")
        if moa_filter is not None:
            params["mechanism_of_action__icontains"] = moa_filter

        # Add any filter parameters (ChEMBL uses field__filter syntax)
        # e.g., molecule_chembl_id__exact, pref_name__icontains
        for key, value in args.items():
            if (
                key
                not in [
                    "limit",
                    "offset",
                    "format",
                    "fields",
                    "only",
                    "ordering",
                    "q",  # handled above: mapped to pref_name__icontains
                    "query",  # handled above: alias for q
                    "pref_name__contains",  # handled above: alias for pref_name__icontains
                    "mechanism_of_action__contains",  # handled above: mapped to __icontains
                    "max_results",  # handled above: alias for limit
                    "chembl_id",
                    "target_chembl_id",  # handled above: mapped to target_chembl_id__exact
                    "assay_chembl_id",  # handled above: mapped to assay_chembl_id__exact
                    "activity_id",
                    "drug_chembl_id",  # handled above: mapped to molecule_chembl_id__exact / parent_molecule_chembl_id
                    "molecule_chembl_id",  # handled above: alias for drug_chembl_id
                    "drug_name",  # Feature-40B-03: not a valid ChEMBL API param; caught in run() with error
                ]
                and value is not None
            ):
                params[key] = value

        return params

    def _extract_parent_chembl_id(self, mol: dict) -> Optional[str]:
        """Extract the parent ChEMBL ID from a molecule record."""
        mol_id = mol.get("molecule_chembl_id")
        # Feature-45B-07: prefer the parent compound over salt/formulation entries.
        hierarchy = mol.get("molecule_hierarchy") or {}
        parent_id = hierarchy.get("parent_chembl_id")
        if parent_id and parent_id != mol_id:
            return parent_id
        return mol_id

    def _lookup_chembl_id_by_name(self, drug_name: str) -> Optional[str]:
        """Look up a ChEMBL molecule ID by preferred name (case-insensitive).

        Feature-79B-001: Uses icontains first (most reliable), then iexact as
        fallback. The iexact and search endpoints frequently timeout for newer drugs.
        Returns the ChEMBL ID of the first matching molecule, or None.
        """
        base = f"{self.base_url}/molecule.json"
        headers = {"Accept": "application/json", "User-Agent": "ToolUniverse/1.0"}
        # Try icontains first (faster/more reliable than iexact on ChEMBL API)
        for lookup_params in (
            {"pref_name__icontains": drug_name, "format": "json", "limit": 5},
            {"pref_name__iexact": drug_name, "format": "json", "limit": 5},
        ):
            try:
                resp = requests.get(
                    base, params=lookup_params, headers=headers, timeout=20
                )
                resp.raise_for_status()
                molecules = resp.json().get("molecules", [])
                if molecules:
                    # Prefer exact name match when icontains returns multiple
                    for mol in molecules:
                        if (mol.get("pref_name") or "").lower() == drug_name.lower():
                            return self._extract_parent_chembl_id(mol)
                    return self._extract_parent_chembl_id(molecules[0])
            except Exception:
                pass
        return None

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the ChEMBL API call"""
        try:
            url = self._build_url(arguments)
            params = self._build_params(arguments)
            tool_name = self.tool_config.get("name", "")

            # Feature-39A-01: ChEMBL_get_drug_mechanisms — validate at least one molecule
            # filter is present; without it the ChEMBL API returns all mechanisms
            # in the database (misleading success with random data).
            if tool_name == "ChEMBL_get_drug_mechanisms":
                mol_id = (
                    arguments.get("drug_chembl_id")
                    or arguments.get("molecule_chembl_id")
                    or arguments.get("chembl_id")
                    or arguments.get("molecule_chembl_id__exact")
                    or arguments.get("drug_chembl_id__exact")  # Feature-40A-01
                )
                # Feature-45A-05: when mol_id came from drug_chembl_id__exact (or other aliases),
                # it is not yet mapped to drug_chembl_id in arguments, so _build_params
                # still sends drug_chembl_id__exact=... as a raw API param that /mechanism.json
                # doesn't recognize — causing all 7568 mechanisms to be returned.
                # Fix: rebuild params after ensuring drug_chembl_id is set.
                if mol_id and not arguments.get("drug_chembl_id"):
                    arguments = dict(arguments)
                    arguments["drug_chembl_id"] = mol_id
                    params = self._build_params(arguments)

                if not mol_id:
                    # Feature-42A-01: auto-lookup ChEMBL ID by drug_name if provided
                    drug_name = arguments.get("drug_name")
                    if drug_name:
                        mol_id = self._lookup_chembl_id_by_name(drug_name)
                        if mol_id:
                            arguments = dict(arguments)
                            arguments["drug_chembl_id"] = mol_id
                            params = self._build_params(arguments)
                        else:
                            return {
                                "status": "error",
                                "error": f"Drug '{drug_name}' not found in ChEMBL database. "
                                "Try ChEMBL_search_molecules or ChEMBL_search_drugs to find the ChEMBL ID first.",
                            }
                    else:
                        return {
                            "status": "error",
                            "error": "drug_chembl_id is required for ChEMBL_get_drug_mechanisms. "
                            "Provide the ChEMBL ID (e.g., 'CHEMBL25' for aspirin) or drug_name "
                            "for automatic lookup (e.g., 'trastuzumab', 'lapatinib'). "
                            "Aliases accepted: drug_chembl_id, molecule_chembl_id, chembl_id.",
                        }

            # Feature-40B-03: ChEMBL_search_mechanisms — drug_name is not a valid ChEMBL
            # API parameter; it is silently ignored, returning unrelated mechanisms.
            # Feature-41B-01: query/pref_name__icontains is also silently ignored by
            # /mechanism.json endpoint — catch it here and return a helpful error.
            if tool_name == "ChEMBL_search_mechanisms":
                # target_chembl_id is silently ignored by /mechanism.json
                target_id = arguments.get("target_chembl_id")
                if target_id:
                    return {
                        "status": "error",
                        "error": f"target_chembl_id='{target_id}' is not supported for "
                        "ChEMBL_search_mechanisms. The /mechanism.json endpoint ignores "
                        "target-based filters. To find mechanisms for a target: "
                        "(1) use ChEMBL_search_activities with target_chembl_id to find "
                        "drugs acting on the target, then (2) use ChEMBL_get_drug_mechanisms "
                        "with the drug_chembl_id. Alternatively, filter by "
                        "mechanism_of_action__icontains (e.g., 'DPP4 inhibitor').",
                    }

                drug_name = arguments.get("drug_name")
                query_name = arguments.get("query") or arguments.get("q")
                if drug_name or query_name:
                    bad_param = (
                        f"drug_name='{drug_name}'"
                        if drug_name
                        else f"query='{query_name}'"
                    )
                    return {
                        "status": "error",
                        "error": f"{bad_param} is not supported for ChEMBL_search_mechanisms. "
                        "The /mechanism.json endpoint ignores name-based filters. "
                        "To search mechanisms by drug name: (1) find the ChEMBL ID with "
                        "ChEMBL_search_molecules or ChEMBL_search_drugs, then (2) use "
                        "drug_chembl_id (e.g., 'CHEMBL3137343' for pembrolizumab). "
                        "Alternatively, filter by mechanism_of_action__contains (e.g., 'PD-1').",
                    }

            # Feature-36A-01: ChEMBL_get_molecule_targets — the /target.json endpoint
            # does NOT support molecule_chembl_id__exact filtering (silently ignored).
            # Correct approach: query /activity.json?molecule_chembl_id=X and
            # deduplicate the target fields from the activity records.
            if tool_name == "ChEMBL_get_molecule_targets":
                mol_id = arguments.get("molecule_chembl_id__exact") or arguments.get(
                    "molecule_chembl_id"
                )
                if mol_id:
                    activity_url = self.base_url + "/activity.json"
                    limit = arguments.get("limit", 500)
                    act_params = {
                        "molecule_chembl_id": mol_id,
                        "limit": min(limit, 500),
                        "format": "json",
                        "only": "target_chembl_id,target_pref_name,target_organism,target_tax_id",
                    }
                    resp = request_with_retry(
                        self.session,
                        "GET",
                        activity_url,
                        params=act_params,
                        timeout=self.timeout,
                        max_attempts=3,
                    )
                    resp.raise_for_status()
                    act_data = resp.json()
                    activities = act_data.get("activities", [])
                    # Deduplicate by target_chembl_id
                    seen = set()
                    targets = []
                    for act in activities:
                        tid = act.get("target_chembl_id")
                        if tid and tid not in seen:
                            seen.add(tid)
                            targets.append(
                                {
                                    "target_chembl_id": tid,
                                    "pref_name": act.get("target_pref_name"),
                                    "organism": act.get("target_organism"),
                                }
                            )
                    return {
                        "status": "success",
                        "data": {"targets": targets},
                        "molecule_chembl_id": mol_id,
                        "count": len(targets),
                        "url": resp.url,
                    }
                return {
                    "status": "error",
                    "error": "molecule_chembl_id__exact or molecule_chembl_id is required",
                }

            # Check if this is an image endpoint
            is_image_endpoint = (
                "get_molecule_image" in tool_name.lower() or "/image/" in url
            )

            response = request_with_retry(
                self.session,
                "GET",
                url,
                params=params,
                timeout=self.timeout,
                max_attempts=3,
                backoff_seconds=0.5,
            )
            response.raise_for_status()

            # Handle image endpoints differently
            if is_image_endpoint:
                content_type = response.headers.get("Content-Type", "")
                if "image" in content_type or "svg" in content_type:
                    # Return the image URL and content type for binary data
                    return {
                        "status": "success",
                        "data": f"Image data available at URL (Content-Type: {content_type})",
                        "url": response.url,
                        "content_type": content_type,
                        "image_size_bytes": len(response.content),
                    }

            data = response.json()

            response_data = {
                "status": "success",
                "data": data,
                "url": response.url,
            }

            # Extract count if available (ChEMBL pagination)
            if isinstance(data, dict):
                if "page_meta" in data:
                    response_data["page_meta"] = data["page_meta"]
                if "page" in data:
                    response_data["pagination"] = data["page"]

            # Count results if it's a list or has a results key
            if isinstance(data, list):
                response_data["count"] = len(data)
            elif isinstance(data, dict):
                # ChEMBL often returns data in a key matching the resource name
                for key in [
                    "molecules",
                    "targets",
                    "assays",
                    "activities",
                    "drugs",
                    "mechanisms",
                    "indications",
                    "binding_sites",
                ]:
                    if key in data and isinstance(data[key], list):
                        response_data["count"] = len(data[key])
                        break

            return response_data

        except requests.exceptions.HTTPError as e:
            resp = e.response
            status_code = getattr(resp, "status_code", None)
            detail = None
            if getattr(resp, "text", None):
                # Include a short preview of the response body for debugging,
                # but avoid returning huge payloads.
                detail = resp.text[:500]
            return {
                "status": "error",
                "error": f"ChEMBL API returned HTTP {status_code}",
                "url": getattr(resp, "url", url if "url" in locals() else None),
                "status_code": status_code,
                "detail": detail,
            }
        except requests.exceptions.RequestException as e:
            return {
                "status": "error",
                "error": f"ChEMBL API request failed: {str(e)}",
                "url": url if "url" in locals() else None,
                "detail": repr(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "url": url if "url" in locals() else None,
                "detail": repr(e),
            }


@register_tool("ChEMBLTool")
class ChEMBLTool(BaseTool):
    """
    Tool to search for molecules similar to a given compound name or SMILES using the ChEMBL Web Services API.

    Note: This tool is designed for small molecule compounds only. Biologics (antibodies, proteins,
    oligonucleotides, etc.) do not have SMILES structures and cannot be used for structure-based
    similarity search. The tool will provide detailed error messages when biologics are queried,
    explaining the reason and suggesting alternative tools.
    """

    def __init__(self, tool_config, base_url="https://www.ebi.ac.uk/chembl/api/data"):
        super().__init__(tool_config)
        self.base_url = base_url
        self.indigo = Indigo()

    def run(self, arguments):
        query = arguments.get("query")
        similarity_threshold = arguments.get("similarity_threshold", 80)
        max_results = arguments.get("max_results", 20)

        if not query:
            return {"status": "error", "error": "`query` parameter is required."}
        return self._search_similar_molecules(query, similarity_threshold, max_results)

    def get_chembl_id_by_name(self, compound_name):
        """
        Search ChEMBL for a compound by name and return the ChEMBL ID of the first match.
        """
        headers = {"Accept": "application/json"}
        search_url = f"{self.base_url}/molecule/search.json?q={quote(compound_name)}"
        print(search_url)
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        results = response.json().get("molecules", [])
        if not results or not isinstance(results, list):
            return {
                "status": "error",
                "error": "No valid results found for the compound name.",
            }
        if not results:
            return {
                "status": "error",
                "error": "No results found for the compound name.",
            }
        top_molecules = results[:3]  # Get the top 3 results
        chembl_ids = [
            molecule.get("molecule_chembl_id")
            for molecule in top_molecules
            if molecule.get("molecule_chembl_id")
        ]
        if not chembl_ids:
            return {
                "status": "error",
                "error": "No ChEMBL IDs found for the compound name.",
            }
        return {"chembl_ids": chembl_ids}

    def get_smiles_pref_name_by_chembl_id(self, query):
        """
        Given a ChEMBL ID, return a dict with canonical SMILES and preferred name.
        """
        headers = {"Accept": "application/json"}
        if query.upper().startswith("CHEMBL"):
            molecule_url = f"{self.base_url}/molecule/{quote(query)}.json"
            response = requests.get(molecule_url, headers=headers)
            response.raise_for_status()
            molecule = response.json()
            if not molecule or not isinstance(molecule, dict):
                return {
                    "status": "error",
                    "error": "No valid molecule found for the given ChEMBL ID.",
                }
            molecule_structures = molecule.get("molecule_structures")
            if not molecule_structures or not isinstance(molecule_structures, dict):
                return {
                    "status": "error",
                    "error": "Molecule structures not found or invalid for the ChEMBL ID.",
                }
            smiles = molecule_structures.get("canonical_smiles")
            pref_name = molecule.get("pref_name")
            if not smiles:
                return {
                    "status": "error",
                    "error": "SMILES not found for the given ChEMBL ID.",
                }
            return {"smiles": smiles, "pref_name": pref_name}
        else:
            return None

    def get_chembl_smiles_pref_name_id_by_name(self, compound_name):
        """
        Search ChEMBL for a compound by name and return a list of dicts with ChEMBL ID, canonical SMILES, and preferred name for the top 5 matches.
        """
        headers = {"Accept": "application/json"}
        search_url = f"{self.base_url}/molecule/search.json?q={quote(compound_name)}"
        response = requests.get(search_url, headers=headers)
        response.raise_for_status()
        results = response.json().get("molecules", [])
        if not results or not isinstance(results, list):
            return {
                "status": "error",
                "error": "No valid results found for the compound name.",
            }
        top_molecules = results[:5]
        output = []
        molecules_without_smiles = []
        for molecule in top_molecules:
            chembl_id = molecule.get("molecule_chembl_id", None)
            molecule_structures = molecule.get("molecule_structures", {})
            molecule_type = molecule.get("molecule_type", "Unknown")
            if molecule_structures is not None:
                smiles = molecule_structures.get("canonical_smiles", None)
            else:
                smiles = None
            pref_name = molecule.get("pref_name")
            if chembl_id and smiles:
                output.append(
                    {"chembl_id": chembl_id, "smiles": smiles, "pref_name": pref_name}
                )
            elif chembl_id and not smiles:
                smiles_pre_name_dict = self.get_smiles_pref_name_by_chembl_id(chembl_id)
                if (
                    isinstance(smiles_pre_name_dict, dict)
                    and "error" not in smiles_pre_name_dict
                ):
                    output.append(
                        {
                            "chembl_id": chembl_id,
                            "smiles": smiles_pre_name_dict["smiles"],
                            "pref_name": smiles_pre_name_dict.get("pref_name"),
                        }
                    )
                else:
                    # Store info about molecules found but without SMILES
                    molecules_without_smiles.append(
                        {
                            "chembl_id": chembl_id,
                            "pref_name": pref_name,
                            "molecule_type": molecule_type,
                        }
                    )
        if not output:
            # Provide detailed error message with reason and alternative tools
            error_msg = "No ChEMBL IDs or SMILES found for the compound name."
            if molecules_without_smiles:
                molecule_types = set(
                    [
                        m.get("molecule_type")
                        for m in molecules_without_smiles
                        if m.get("molecule_type")
                    ]
                )
                if any(
                    mt in ["Antibody", "Protein", "Oligonucleotide", "Oligosaccharide"]
                    for mt in molecule_types
                ):
                    error_msg = (
                        f"The compound '{compound_name}' was found in ChEMBL but does not have a SMILES structure. "
                        f"This tool is designed for small molecule compounds only. "
                        f"The found molecule(s) are of type(s): {', '.join(molecule_types)}. "
                        f"Biologics (antibodies, proteins, etc.) do not have SMILES representations. "
                        f"For searching similar biologics, consider using: "
                        f"PDB_search_similar_structures (for structure/sequence similarity search using PDB ID or sequence), "
                        f"BLAST_protein_search (for protein/antibody sequence similarity search, requires amino acid sequence), "
                        f"or UniProt_search (for searching proteins in UniProt database). "
                        f"For small molecule similarity search, use: PubChem_search_compounds_by_similarity (requires SMILES input)."
                    )
                else:
                    error_msg = (
                        f"The compound '{compound_name}' was found in ChEMBL (ChEMBL ID(s): "
                        f"{', '.join([m.get('chembl_id') for m in molecules_without_smiles[:3]])}) "
                        f"but does not have a SMILES structure available. "
                        f"This tool requires SMILES for similarity search. "
                        f"For searching similar small molecules, consider using: "
                        f"PubChem_search_compounds_by_similarity (requires SMILES input)."
                    )
            return {"status": "error", "error": error_msg}
        return output

    def _search_similar_molecules(self, query, similarity_threshold, max_results):
        headers = {"Accept": "application/json"}

        smiles_info_list = []

        # If the query looks like a ChEMBL ID, fetch its SMILES and pref_name
        if isinstance(query, str) and query.upper().startswith("CHEMBL"):
            result = self.get_smiles_pref_name_by_chembl_id(query)
            if isinstance(result, dict) and "error" in result:
                return result
            smiles_info_list.append(
                {
                    "chembl_id": query,
                    "smiles": result["smiles"],
                    "pref_name": result.get("pref_name"),
                }
            )

        # If not a ChEMBL ID, check if it's a SMILES string (contains structural chars)
        _smiles_chars = set("=()[]@#+\\/%")
        if (
            len(smiles_info_list) == 0
            and isinstance(query, str)
            and any(c in query for c in _smiles_chars)
        ):
            smiles_info_list.append(
                {"chembl_id": None, "smiles": query, "pref_name": None}
            )

        # Otherwise use get_chembl_smiles_pref_name_id_by_name to get info
        if len(smiles_info_list) == 0 and isinstance(query, str):
            results = self.get_chembl_smiles_pref_name_id_by_name(query)
            if isinstance(results, dict) and "error" in results:
                return results
            for item in results:
                smiles_info_list.append(item)

        if len(smiles_info_list) == 0:
            # Check if the compound exists in ChEMBL but without SMILES
            if isinstance(query, str) and not query.upper().startswith("CHEMBL"):
                # Try to get molecule info to provide better error message
                headers = {"Accept": "application/json"}
                search_url = f"{self.base_url}/molecule/search.json?q={quote(query)}"
                try:
                    response = requests.get(search_url, headers=headers)
                    response.raise_for_status()
                    results = response.json().get("molecules", [])
                    if results and len(results) > 0:
                        molecule = results[0]
                        molecule_type = molecule.get("molecule_type", "Unknown")
                        chembl_id = molecule.get("molecule_chembl_id")
                        if molecule_type in [
                            "Antibody",
                            "Protein",
                            "Oligonucleotide",
                            "Oligosaccharide",
                        ]:
                            return {
                                "status": "error",
                                "error": (
                                    f"The compound '{query}' was found in ChEMBL (ChEMBL ID: {chembl_id}) "
                                    f"but is a {molecule_type.lower()}, not a small molecule. "
                                    f"This tool is designed for small molecule compounds only. "
                                    f"Biologics (antibodies, proteins, etc.) do not have SMILES representations "
                                    f"and cannot be used for structure-based similarity search. "
                                    f"For searching similar biologics, consider using: "
                                    f"PDB_search_similar_structures (for structure/sequence similarity search using PDB ID or sequence), "
                                    f"BLAST_protein_search (for protein/antibody sequence similarity search, requires amino acid sequence), "
                                    f"or UniProt_search (for searching proteins in UniProt database). "
                                    f"For small molecule similarity search, use: PubChem_search_compounds_by_similarity (requires SMILES input)."
                                ),
                            }
                except Exception:
                    pass
            return {
                "status": "error",
                "error": (
                    f"SMILES representation not found for the compound '{query}'. "
                    f"This tool requires SMILES structure for similarity search. "
                    f"If you have a SMILES string, you can use it directly as the query. "
                    f"Alternatively, consider using PubChem_search_compounds_by_similarity "
                    f"(requires SMILES input) for similarity search."
                ),
            }

        results_list = []
        for info in smiles_info_list:
            smiles = info["smiles"]
            pref_name = info.get("pref_name")
            chembl_id = info.get("chembl_id")
            mol = self.indigo.loadMolecule(smiles)
            if mol is None:
                return {
                    "status": "error",
                    "error": "Failed to load molecule with Indigo.",
                }

            encoded_smiles = quote(smiles)
            similarity_url = f"{self.base_url}/similarity/{encoded_smiles}/{similarity_threshold}.json?limit={max_results}"
            sim_response = requests.get(similarity_url, headers=headers)
            sim_response.raise_for_status()
            sim_results = sim_response.json().get("molecules", [])
            similar_molecules = []
            for mol in sim_results:
                sim_chembl_id = mol.get("molecule_chembl_id")
                sim_pref_name = mol.get("pref_name", "N/A")
                mol_structures = mol.get("molecule_structures", {})
                if mol_structures is None:
                    continue
                mol_smiles = mol_structures.get("canonical_smiles", "N/A")
                similarity = mol.get("similarity", "N/A")
                similar_molecules.append(
                    {
                        "chembl_id": sim_chembl_id,
                        "pref_name": sim_pref_name,
                        "smiles": mol_smiles,
                        "similarity": similarity,
                    }
                )
            if len(similar_molecules) == 0:
                continue
            results_list.append(
                {
                    "chembl_id": chembl_id,
                    "pref_name": pref_name,
                    "smiles": smiles,
                    "similar_molecules": similar_molecules,
                }
            )

        return results_list
