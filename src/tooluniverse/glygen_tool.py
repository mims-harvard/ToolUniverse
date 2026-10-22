# glygen_tool.py
"""
GlyGen REST API tool for ToolUniverse.

GlyGen is a data integration and dissemination project for carbohydrate
and glycoconjugate related data. It integrates glycan structures, glycoproteins,
glycosylation sites, species, enzymes, and publications.

API: https://api.glygen.org
No authentication required. Free for academic/research use.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

GLYGEN_BASE_URL = "https://api.glygen.org"


@register_tool("GlyGenTool")
class GlyGenTool(BaseTool):
    """
    Tool for querying the GlyGen glycoinformatics database.

    GlyGen provides access to glycan structures, glycoproteins, glycosylation
    sites, biosynthetic enzymes, and related publications from integrated
    sources including GlyTouCan, GlyConnect, UniProt, and PubMed.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 60)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "glycan"
        )
        self.query_mode = tool_config.get("fields", {}).get("query_mode", "detail")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the GlyGen API call."""
        try:
            return self._dispatch(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"GlyGen API request timed out after {self.timeout} seconds",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to GlyGen API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"GlyGen API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying GlyGen: {str(e)}",
            }

    def _dispatch(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint based on config."""
        if self.endpoint_type == "glycan" and self.query_mode == "detail":
            return self._glycan_detail(arguments)
        elif self.endpoint_type == "glycan" and self.query_mode == "search":
            return self._glycan_search(arguments)
        elif self.endpoint_type == "protein" and self.query_mode == "detail":
            return self._protein_detail(arguments)
        elif self.endpoint_type == "protein" and self.query_mode == "search":
            return self._protein_search(arguments)
        elif self.endpoint_type == "site" and self.query_mode == "detail":
            return self._site_detail(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint_type/query_mode: {self.endpoint_type}/{self.query_mode}",
            }

    def _glycan_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific glycan by GlyTouCan accession."""
        glytoucan_ac = arguments.get("glytoucan_ac", "")
        if not glytoucan_ac:
            return {"status": "error", "error": "glytoucan_ac parameter is required"}

        url = f"{GLYGEN_BASE_URL}/glycan/detail/{glytoucan_ac}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        # Extract key fields for structured response
        result = {
            "glytoucan_ac": raw.get("glytoucan", {}).get("glytoucan_ac"),
            "mass": raw.get("mass"),
            "number_monosaccharides": raw.get("number_monosaccharides"),
            "glycan_type": raw.get("glycan_type"),
            "iupac": raw.get("iupac"),
            "wurcs": raw.get("wurcs"),
            "classification": raw.get("classification", []),
            "species": [dict(s) for s in raw.get("species", [])],
            "species_count": len(raw.get("species", [])),
            "glycoprotein_count": len(raw.get("glycoprotein", [])),
            "glycoproteins": [
                {**gp, "uniprot_ac": gp.get("uniprot_canonical_ac")}
                for gp in raw.get("glycoprotein", [])
            ],
            "returned_glycoprotein_count": len(raw.get("glycoprotein", [])),
            "publication_count": len(raw.get("publication", [])),
            "composition": raw.get("composition", []),
            "byonic": raw.get("byonic"),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": glytoucan_ac,
                "endpoint": "glycan/detail",
            },
        }

    def _glycan_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for glycans by mass range, monosaccharide count, organism, etc."""
        # Build search query
        query = {}
        if "mass_min" in arguments or "mass_max" in arguments:
            mass = {}
            if "mass_min" in arguments:
                mass["min"] = arguments["mass_min"]
            if "mass_max" in arguments:
                mass["max"] = arguments["mass_max"]
            query["mass"] = mass

        if "monosaccharide_min" in arguments or "monosaccharide_max" in arguments:
            mono = {}
            if "monosaccharide_min" in arguments:
                mono["min"] = arguments["monosaccharide_min"]
            if "monosaccharide_max" in arguments:
                mono["max"] = arguments["monosaccharide_max"]
            query["number_monosaccharides"] = mono

        if "glycan_type" in arguments:
            query["glycan_type"] = arguments["glycan_type"]

        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required (mass_min/max, monosaccharide_min/max, glycan_type)",
            }

        pagination_args = self._validate_search_pagination(arguments)
        if isinstance(pagination_args, dict):
            return pagination_args
        offset, limit = pagination_args

        # Step 1: Submit search
        search_url = f"{GLYGEN_BASE_URL}/glycan/search/"
        search_resp = requests.post(
            search_url,
            json=query,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        list_id = search_data.get("list_id")

        if not list_id:
            return {
                "status": "success",
                "data": [],
                "metadata": self._search_pagination_metadata(
                    {}, [], offset, limit, {"list_id": None, "query": query}
                ),
            }

        # Step 2: Retrieve results
        list_url = f"{GLYGEN_BASE_URL}/glycan/list/"
        list_body = {
            "id": list_id,
            "offset": offset,
            "limit": limit,
            "sort": "hit_score",
            "order": "desc",
        }
        list_resp = requests.post(
            list_url,
            json=list_body,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        list_resp.raise_for_status()
        list_data = list_resp.json()

        results = []
        for item in list_data.get("results", []):
            results.append(
                {
                    "glytoucan_ac": item.get("glytoucan_ac"),
                    "mass": item.get("mass"),
                    "number_proteins": item.get("number_proteins"),
                    "number_enzymes": item.get("number_enzymes"),
                    "number_species": item.get("number_species"),
                    "hit_score": item.get("hit_score"),
                    "byonic": item.get("byonic"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_pagination_metadata(
                list_data,
                results,
                offset,
                limit,
                {"list_id": list_id, "query": query},
            ),
        }

    @staticmethod
    def _validate_search_pagination(arguments: Dict[str, Any]):
        """Validate GlyGen's one-based list offset without silent clamping."""
        limit = arguments.get("limit", 20)
        offset = arguments.get("offset", 1)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
        ):
            return {
                "status": "error",
                "error": "limit must be an integer between 1 and 50",
                "parameter": "limit",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 1:
            return {
                "status": "error",
                "error": "offset must be a positive one-based integer",
                "parameter": "offset",
            }
        return offset, limit

    @staticmethod
    def _search_pagination_metadata(
        list_data: Dict[str, Any],
        results: list,
        requested_offset: int,
        requested_limit: int,
        extra: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build continuation metadata from GlyGen's list response."""
        pagination = list_data.get("pagination", {})
        offset = pagination.get("offset", requested_offset)
        limit = pagination.get("limit", requested_limit)
        total = pagination.get("total_length", len(results))
        try:
            offset = int(offset)
        except (TypeError, ValueError):
            offset = requested_offset
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = requested_limit
        try:
            total = int(total)
        except (TypeError, ValueError):
            total = len(results)
        returned_count = len(results)
        has_more = offset - 1 + returned_count < total
        metadata = {
            "total_results": total,
            "returned_count": returned_count,
            "offset": offset,
            "requested_offset": requested_offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": offset + returned_count if returned_count and has_more else None,
            "truncated": has_more,
            "result_set_complete": not has_more,
        }
        metadata.update(extra)
        return metadata

    def _protein_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get glycoprotein details including glycosylation sites."""
        uniprot_ac = arguments.get("uniprot_ac", "")
        if not uniprot_ac:
            return {"status": "error", "error": "uniprot_ac parameter is required"}

        url = f"{GLYGEN_BASE_URL}/protein/detail/{uniprot_ac}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        # Extract key fields
        protein_names = raw.get("protein_names", [])
        gene_names = raw.get("gene_names", [])
        glycosylation = raw.get("glycosylation", [])
        species = raw.get("species", [])

        result = {
            "protein_name": protein_names[0].get("name") if protein_names else None,
            "gene_names": [g.get("name") for g in gene_names],
            "gene_name_count": len(gene_names),
            "gene_name_details": [dict(g) for g in gene_names],
            "species": species[0].get("name") if species else None,
            "mass": raw.get("mass"),
            "sequence_length": len(raw.get("sequence", {}).get("sequence", "")),
            "glycosylation_count": len(glycosylation),
            "glycosylation_sites": [
                {
                    **g,
                    "position": g.get("start_pos"),
                    "residue": g.get("residue"),
                    "type": g.get("type"),
                    "glytoucan_ac": g.get("glytoucan_ac"),
                    "site_category": g.get("site_category"),
                }
                for g in glycosylation
            ],
            "returned_glycosylation_count": len(glycosylation),
            "function": raw.get("function", [{}])[0].get("annotation")
            if raw.get("function")
            else None,
            "disease_count": len(raw.get("disease", [])),
            "snv_count": len(raw.get("snv", [])),
            "pathway_count": len(raw.get("pathway", [])),
            "publication_count": len(raw.get("publication", [])),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": uniprot_ac,
                "endpoint": "protein/detail",
            },
        }

    def _protein_search(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Search for glycoproteins by organism, glycosylation type, etc."""
        query = {}

        if "organism_id" in arguments:
            query["organism"] = {"id": arguments["organism_id"]}

        if "glycosylation_evidence" in arguments:
            query["glycosylation_evidence"] = arguments["glycosylation_evidence"]

        if "glycosylation_type" in arguments:
            query["glycosylation_type"] = arguments["glycosylation_type"]

        if "protein_name" in arguments:
            query["protein_name"] = arguments["protein_name"]

        if "gene_name" in arguments:
            query["gene_name"] = arguments["gene_name"]

        if not query:
            return {
                "status": "error",
                "error": "At least one search parameter required (organism_id, glycosylation_evidence, glycosylation_type, protein_name, gene_name)",
            }

        pagination_args = self._validate_search_pagination(arguments)
        if isinstance(pagination_args, dict):
            return pagination_args
        offset, limit = pagination_args

        # Step 1: Submit search
        search_url = f"{GLYGEN_BASE_URL}/protein/search/"
        search_resp = requests.post(
            search_url,
            json=query,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        search_resp.raise_for_status()
        search_data = search_resp.json()
        list_id = search_data.get("list_id")

        if not list_id:
            return {
                "status": "success",
                "data": [],
                "metadata": self._search_pagination_metadata(
                    {}, [], offset, limit, {"list_id": None, "query": query}
                ),
            }

        # Step 2: Retrieve results
        list_url = f"{GLYGEN_BASE_URL}/protein/list/"
        list_body = {
            "id": list_id,
            "offset": offset,
            "limit": limit,
            "sort": "hit_score",
            "order": "desc",
        }
        list_resp = requests.post(
            list_url,
            json=list_body,
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        list_resp.raise_for_status()
        list_data = list_resp.json()

        results = []
        for item in list_data.get("results", []):
            results.append(
                {
                    "uniprot_canonical_ac": item.get("uniprot_canonical_ac"),
                    "protein_name": item.get("protein_name"),
                    "gene_name": item.get("gene_name"),
                    "organism": item.get("organism"),
                    "glycosylation_count": (item.get("total_n_glycosites") or 0)
                    + (item.get("total_o_glycosites") or 0),
                    "hit_score": item.get("hit_score"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": self._search_pagination_metadata(
                list_data,
                results,
                offset,
                limit,
                {"list_id": list_id, "query": query},
            ),
        }

    def _site_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get details about a specific glycosylation site."""
        site_id = arguments.get("site_id", "")
        if not site_id:
            return {
                "status": "error",
                "error": "site_id parameter is required (format: UniProtAC-isoform.start.end, e.g. P02724-1.52.52)",
            }

        url = f"{GLYGEN_BASE_URL}/site/detail/{site_id}/"
        response = requests.post(
            url,
            json={},
            timeout=self.timeout,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        raw = response.json()

        result = {
            "site_id": raw.get("id"),
            "uniprot_ac": raw.get("uniprot_canonical_ac"),
            "start_pos": raw.get("start_pos"),
            "end_pos": raw.get("end_pos"),
            "site_seq": raw.get("site_seq"),
            "start_aa": raw.get("start_aa"),
            "upstream_seq": raw.get("up_seq"),
            "downstream_seq": raw.get("down_seq"),
            "glycosylation": raw.get("glycosylation", []),
            "phosphorylation": raw.get("phosphorylation", []),
            "snv": raw.get("snv", []),
            "mutagenesis": raw.get("mutagenesis", []),
            "species": raw.get("species"),
            "all_sites_count": len(raw.get("all_sites", [])),
            "categories": raw.get("categories", []),
        }

        return {
            "status": "success",
            "data": result,
            "metadata": {
                "source": "GlyGen",
                "query": site_id,
                "endpoint": "site/detail",
            },
        }
