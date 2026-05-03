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
            "species": [
                {
                    "name": s.get("name"),
                    "taxid": s.get("taxid"),
                    "common_name": s.get("common_name"),
                }
                for s in raw.get("species", [])[:20]
            ],
            "glycoprotein_count": len(raw.get("glycoprotein", [])),
            "glycoproteins": [
                {
                    "uniprot_ac": gp.get("uniprot_canonical_ac"),
                    "protein_name": gp.get("protein_name"),
                }
                for gp in raw.get("glycoprotein", [])[:10]
            ],
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
            return {"data": [], "metadata": {"total_results": 0, "query": query}}

        # Step 2: Retrieve results
        limit = min(arguments.get("limit", 20), 50)
        offset = arguments.get("offset", 1)
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
            "metadata": {
                "total_results": list_data.get("pagination", {}).get(
                    "total_length", len(results)
                ),
                "list_id": list_id,
                "query": query,
                "offset": offset,
                "limit": limit,
            },
        }

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
            "gene_names": [g.get("name") for g in gene_names[:5]],
            "species": species[0].get("name") if species else None,
            "mass": raw.get("mass"),
            "sequence_length": len(raw.get("sequence", {}).get("sequence", "")),
            "glycosylation_count": len(glycosylation),
            "glycosylation_sites": [
                {
                    "position": g.get("start_pos"),
                    "residue": g.get("residue"),
                    "type": g.get("type"),
                    "glytoucan_ac": g.get("glytoucan_ac"),
                    "site_category": g.get("site_category"),
                }
                for g in glycosylation[:30]
            ],
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
            return {"data": [], "metadata": {"total_results": 0, "query": query}}

        # Step 2: Retrieve results
        limit = min(arguments.get("limit", 20), 50)
        offset = arguments.get("offset", 1)
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
                    "glycosylation_count": item.get("total_n_glycosites", 0)
                    + item.get("total_o_glycosites", 0),
                    "hit_score": item.get("hit_score"),
                }
            )

        return {
            "status": "success",
            "data": results,
            "metadata": {
                "total_results": list_data.get("pagination", {}).get(
                    "total_length", len(results)
                ),
                "list_id": list_id,
                "query": query,
                "offset": offset,
                "limit": limit,
            },
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
