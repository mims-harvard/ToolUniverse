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
                "get_qtls_in_region": self._get_qtls_in_region,
                "resolve_symbol_or_region": self._resolve_symbol_or_region,
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
        # RGD's own symbol search is unreliable (returns 400 for many queries).
        # Note: the Alliance API no longer honours a `category=gene` query param
        # (it returns zero results) and the gene id is now in `curie` (was
        # `primaryKey`). Fetch unfiltered and keep RGD gene hits client-side.
        alliance_url = "https://www.alliancegenome.org/api/search"
        params = {"q": query, "limit": max(int(limit) * 5, 25)}
        resp = self.session.get(alliance_url, params=params, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        genes = []
        for r in data.get("results", []):
            if r.get("category") != "gene_search_result":
                continue
            curie = r.get("curie", "")
            # Filter to RGD entries only (rat genes)
            if not curie.startswith("RGD:"):
                continue
            genes.append(
                {
                    "rgd_id": curie.replace("RGD:", ""),
                    "symbol": r.get("symbol"),
                    "name": r.get("name"),
                    "species": r.get("species", "Rattus norvegicus"),
                    "synonyms": r.get("synonyms", [])[:5],
                }
            )
            if len(genes) >= int(limit):
                break

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

    # RGD species type keys for the assembly map_key argument.
    _SPECIES_BY_MAP_KEY = {
        360: "rat (rn7, GRCr8)",
        372: "rat (rn7, mRatBN7.2)",
        38: "human (GRCh38)",
        17: "human (GRCh37)",
        35: "mouse (GRCm39)",
        18: "mouse (GRCm38)",
    }

    def _get_qtls_in_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get QTLs overlapping a genomic region (RGD flagship data type)."""
        chromosome = arguments.get("chromosome")
        start = arguments.get("start")
        stop = arguments.get("stop")
        map_key = arguments.get("map_key")
        missing = [
            k
            for k, v in (
                ("chromosome", chromosome),
                ("start", start),
                ("stop", stop),
                ("map_key", map_key),
            )
            if v in (None, "")
        ]
        if missing:
            return {
                "status": "error",
                "error": (
                    "chromosome, start, stop, and map_key are all required "
                    "(e.g., chromosome='10', start=1, stop=50000000, map_key=360 for rat rn7)"
                ),
            }

        chromosome = str(chromosome).replace("chr", "")
        url = f"{RGD_BASE}/qtls/{chromosome}/{int(start)}/{int(stop)}/{int(map_key)}"
        resp = self.session.get(url, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, list):
            data = [data] if data else []

        qtls = []
        for q in data[:100]:
            qtls.append(
                {
                    "rgd_id": q.get("rgdId"),
                    "symbol": q.get("symbol"),
                    "name": q.get("name"),
                    "chromosome": q.get("chromosome"),
                    "lod": q.get("lod"),
                    "p_value": q.get("pvalue"),
                    "variance": q.get("variance"),
                    "inheritance_type": q.get("inheritanceType"),
                }
            )

        return {
            "status": "success",
            "data": qtls,
            "metadata": {
                "chromosome": chromosome,
                "start": int(start),
                "stop": int(stop),
                "map_key": int(map_key),
                "assembly": self._SPECIES_BY_MAP_KEY.get(int(map_key), str(map_key)),
                "total_qtls": len(data),
                "returned": len(qtls),
                "source": "RGD",
            },
        }

    def _resolve_symbol_or_region(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a rat gene symbol to its RGD record, or list genes in a region.

        Two modes:
        - symbol + species_type_key  -> /genes/{symbol}/{speciesTypeKey}
        - chromosome + start + stop + map_key -> /genes/mapped/{chr}/{start}/{stop}/{mapKey}
        """
        symbol = arguments.get("symbol") or arguments.get("gene_symbol")
        chromosome = arguments.get("chromosome")

        if symbol:
            species_type_key = int(arguments.get("species_type_key", 3))
            url = f"{RGD_BASE}/genes/{symbol}/{species_type_key}"
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list):
                data = data[0] if data else {}
            return {
                "status": "success",
                "data": {
                    "key": data.get("key"),
                    "rgd_id": data.get("rgdId"),
                    "symbol": data.get("symbol"),
                    "name": data.get("name"),
                    "type": data.get("type"),
                    "description": data.get("description"),
                    "so_acc_id": data.get("soAccId"),
                    "species_type_key": data.get("speciesTypeKey"),
                },
                "metadata": {
                    "mode": "symbol",
                    "query": symbol,
                    "species_type_key": species_type_key,
                    "source": "RGD",
                },
            }

        if chromosome is not None:
            start = arguments.get("start")
            stop = arguments.get("stop")
            map_key = arguments.get("map_key")
            if start in (None, "") or stop in (None, "") or map_key in (None, ""):
                return {
                    "status": "error",
                    "error": "Region mode requires chromosome, start, stop, and map_key.",
                }
            chrom = str(chromosome).replace("chr", "")
            url = (
                f"{RGD_BASE}/genes/mapped/{chrom}/"
                f"{int(start)}/{int(stop)}/{int(map_key)}"
            )
            resp = self.session.get(url, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if not isinstance(data, list):
                data = [data] if data else []

            genes = []
            for entry in data[:100]:
                gene = entry.get("gene") or {}
                genes.append(
                    {
                        "rgd_id": gene.get("rgdId"),
                        "symbol": gene.get("symbol"),
                        "name": gene.get("name"),
                        "type": gene.get("type"),
                        "chromosome": entry.get("chromosome"),
                        "start": entry.get("start"),
                        "stop": entry.get("stop"),
                        "strand": entry.get("strand"),
                    }
                )

            return {
                "status": "success",
                "data": genes,
                "metadata": {
                    "mode": "region",
                    "chromosome": chrom,
                    "start": int(start),
                    "stop": int(stop),
                    "map_key": int(map_key),
                    "total_genes": len(data),
                    "returned": len(genes),
                    "source": "RGD",
                },
            }

        return {
            "status": "error",
            "error": (
                "Provide either 'symbol' (rat gene symbol) or a region "
                "('chromosome' + 'start' + 'stop' + 'map_key')."
            ),
        }
