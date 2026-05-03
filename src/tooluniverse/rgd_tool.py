"""
RGD Tool - Rat Genome Database

Provides access to rat gene data, disease annotations, phenotype associations,
QTL data, and orthologs via the RGD REST API.

API: https://rest.rgd.mcw.edu/rgdws/
No authentication required.

Reference: Smith et al., Nucleic Acids Res. 2023
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool


RGD_BASE = "https://rest.rgd.mcw.edu/rgdws"


@register_tool("RGDTool")
class RGDTool(BaseTool):
    """
    Tool for querying the Rat Genome Database (RGD).

    Supported operations:
    - get_gene: Get rat gene details by RGD ID
    - search_genes: Search rat genes by symbol/keyword
    - get_annotations: Get disease/phenotype annotations for a gene
    - get_orthologs: Get orthologs across species
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = 30
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "get_gene"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "ToolUniverse/1.0 (https://github.com/mims-harvard/ToolUniverse)"
            }
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            handlers = {
                "get_gene": self._get_gene,
                "search_genes": self._search_genes,
                "get_annotations": self._get_annotations,
                "get_orthologs": self._get_orthologs,
            }
            handler = handlers.get(self.endpoint_type)
            if not handler:
                return {
                    "status": "error",
                    "error": f"Unknown endpoint: {self.endpoint_type}",
                }
            return handler(arguments)
        except requests.exceptions.Timeout:
            return {"status": "error", "error": "RGD API request timed out"}
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to RGD API"}
        except Exception as e:
            return {"status": "error", "error": f"RGD API error: {str(e)}"}

    def _get_gene(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rgd_id = arguments.get("rgd_id") or arguments.get("gene_id", "")
        if not rgd_id:
            return {"status": "error", "error": "rgd_id is required"}
        rgd_id = str(rgd_id).replace("RGD:", "")

        resp = self.session.get(f"{RGD_BASE}/genes/{rgd_id}", timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        return {
            "status": "success",
            "data": {
                "rgd_id": data.get("rgdId"),
                "symbol": data.get("symbol"),
                "name": data.get("name"),
                "description": data.get("agrDescription") or data.get("description"),
                "type": data.get("type"),
                "ensembl_symbol": data.get("ensemblGeneSymbol"),
                "refseq_status": data.get("refSeqStatus"),
            },
            "metadata": {"source": "RGD", "query_id": rgd_id},
        }

    def _search_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        query = arguments.get("query") or arguments.get("gene_symbol", "")
        if not query:
            return {"status": "error", "error": "query is required"}

        limit = arguments.get("limit", 10)

        # Use Alliance of Genome Resources search (aggregates RGD data)
        # RGD's own symbol search is unreliable (returns 400 for many queries)
        alliance_url = "https://www.alliancegenome.org/api/search"
        params = {"q": query, "category": "gene", "limit": limit}
        resp = self.session.get(alliance_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        genes = []
        for r in data.get("results", []):
            pk = r.get("primaryKey", "")
            # Filter to RGD entries only (rat genes)
            if not pk.startswith("RGD:"):
                continue
            genes.append(
                {
                    "rgd_id": pk.replace("RGD:", ""),
                    "symbol": r.get("symbol"),
                    "name": r.get("name"),
                    "species": r.get("species", "Rattus norvegicus"),
                    "synonyms": r.get("synonyms", [])[:5],
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                "query": query,
                "returned": len(genes),
                "total_alliance_results": data.get("total", 0),
                "source": "RGD via Alliance of Genome Resources",
            },
        }

    def _get_annotations(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rgd_id = arguments.get("rgd_id") or arguments.get("gene_id", "")
        if not rgd_id:
            return {"status": "error", "error": "rgd_id is required"}
        rgd_id = str(rgd_id).replace("RGD:", "")

        aspect = arguments.get("aspect", "")  # D=disease, P=pathway, etc.

        resp = self.session.get(
            f"{RGD_BASE}/annotations/rgdId/{rgd_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            data = [data] if data else []

        # Filter by aspect if specified
        if aspect:
            data = [d for d in data if d.get("aspect") == aspect.upper()]

        # Group by aspect
        from collections import Counter

        aspect_counts = Counter(d.get("aspect", "?") for d in data)

        annotations = []
        for ann in data[:50]:
            annotations.append(
                {
                    "term": ann.get("term"),
                    "term_acc": ann.get("termAcc"),
                    "qualifier": ann.get("qualifier"),
                    "aspect": ann.get("aspect"),
                    "evidence": ann.get("evidence"),
                    "data_src": ann.get("dataSrc"),
                    "notes": (ann.get("notes") or "")[:200],
                }
            )

        aspect_labels = {
            "D": "Disease",
            "E": "Expression",
            "P": "Pathway",
            "F": "Molecular Function",
            "C": "Cellular Component",
            "W": "Phenotype",
        }

        return {
            "status": "success",
            "data": annotations,
            "metadata": {
                "rgd_id": rgd_id,
                "total_annotations": len(data) if not aspect else len(annotations),
                "returned": len(annotations),
                "aspect_counts": {
                    aspect_labels.get(k, k): v for k, v in aspect_counts.items()
                },
                "source": "RGD",
            },
        }

    def _get_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        rgd_id = arguments.get("rgd_id") or arguments.get("gene_id", "")
        if not rgd_id:
            return {"status": "error", "error": "rgd_id is required"}
        rgd_id = str(rgd_id).replace("RGD:", "")

        resp = self.session.get(
            f"{RGD_BASE}/genes/orthologs/{rgd_id}",
            timeout=self.timeout,
        )
        resp.raise_for_status()
        data = resp.json()

        if not isinstance(data, list):
            data = [data] if data else []

        species_map = {
            1: "human",
            2: "mouse",
            3: "rat",
            4: "chinchilla",
            5: "bonobo",
            6: "dog",
            7: "squirrel",
            9: "pig",
            13: "green_monkey",
            14: "naked_mole_rat",
        }

        orthologs = []
        for o in data:
            orthologs.append(
                {
                    "rgd_id": o.get("rgdId"),
                    "symbol": o.get("symbol"),
                    "name": o.get("name"),
                    "species": species_map.get(
                        o.get("speciesTypeKey"), str(o.get("speciesTypeKey"))
                    ),
                }
            )

        return {
            "status": "success",
            "data": orthologs,
            "metadata": {
                "query_rgd_id": rgd_id,
                "ortholog_count": len(orthologs),
                "source": "RGD",
            },
        }
