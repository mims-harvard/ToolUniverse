# ebi_proteins_ext_tool.py
"""
EBI Proteins API Extended tool for ToolUniverse.

Extended endpoints for the EBI Proteins API covering mutagenesis data
and post-translational modification (PTM) proteomics evidence.

API: https://www.ebi.ac.uk/proteins/api/
No authentication required. Free public access.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

PROTEINS_API_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


@register_tool("EBIProteinsExtTool")
class EBIProteinsExtTool(BaseTool):
    """
    Extended tool for EBI Proteins API covering mutagenesis and PTM data.

    These endpoints provide detailed mutagenesis experiment results and
    mass spectrometry-based post-translational modification evidence
    mapped to UniProt protein sequences.

    Supports: mutagenesis data, proteomics PTM evidence.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "mutagenesis")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"EBI Proteins API timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {"status": "error", "error": "Failed to connect to EBI Proteins API"}
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"EBI Proteins API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying EBI Proteins API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "mutagenesis":
            return self._get_mutagenesis(arguments)
        elif self.endpoint == "proteomics_ptm":
            return self._get_proteomics_ptm(arguments)
        elif self.endpoint == "variation":
            return self._get_variation(arguments)
        elif self.endpoint == "features":
            return self._get_features(arguments)
        elif self.endpoint == "antigen":
            return self._get_antigen(arguments)
        elif self.endpoint == "coordinates":
            return self._get_coordinates(arguments)
        elif self.endpoint == "proteomics":
            return self._get_proteomics(arguments)
        elif self.endpoint == "rna_editing":
            return self._get_rna_editing(arguments)
        elif self.endpoint == "variation_dbsnp":
            return self._get_variation_by_dbsnp(arguments)
        elif self.endpoint == "variation_hgvs":
            return self._get_variation_by_hgvs(arguments)
        elif self.endpoint == "proteomics_hpp":
            return self._get_proteomics_hpp(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_mutagenesis(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get mutagenesis experiment data for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        url = f"{PROTEINS_API_BASE_URL}/mutagenesis/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        features = []
        for f in data.get("features", []):
            # Extract evidence details
            evidences = []
            for ev in f.get("evidences", []):
                src = ev.get("source", {})
                evidences.append(
                    {
                        "code": ev.get("code"),
                        "source_name": src.get("name"),
                        "source_id": src.get("id"),
                        "source_url": src.get("url"),
                    }
                )

            features.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "original_sequence": f.get("alternativeSequence"),
                    "description": f.get("description"),
                    "evidences": evidences[:5],
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "gene_name": None,
                "features": features[:100],
                "total_features": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - Mutagenesis",
                "accession": accession,
            },
        }

    def _get_proteomics_ptm(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get post-translational modification evidence from mass spec proteomics."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        url = f"{PROTEINS_API_BASE_URL}/proteomics-ptm/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        features = []
        for f in data.get("features", []):
            # Extract source databases
            evidences = []
            for ev in f.get("evidences", []):
                src = ev.get("source", {})
                props = src.get("properties", {})
                evidences.append(
                    {
                        "source": src.get("name"),
                        "id": src.get("id"),
                        "url": src.get("url"),
                        "properties": props,
                    }
                )

            features.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "description": f.get("description"),
                    "evidences": evidences[:5],
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "features": features[:100],
                "total_features": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - Proteomics PTM",
                "accession": accession,
            },
        }

    def _get_variation(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein sequence variants from multiple sources."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }
        source_type = arguments.get("source_type")
        disease_only = arguments.get("disease_only", False)

        url = f"{PROTEINS_API_BASE_URL}/variation/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        raw_features = data.get("features", [])

        # Filter by source type if specified
        if source_type:
            raw_features = [
                f for f in raw_features if f.get("sourceType") == source_type
            ]

        # Filter to disease-associated only
        if disease_only:
            raw_features = [
                f
                for f in raw_features
                if any(a.get("disease") for a in f.get("association", []))
            ]

        # Count by source
        source_counts = {}
        for f in data.get("features", []):
            src = f.get("sourceType", "unknown")
            source_counts[src] = source_counts.get(src, 0) + 1

        variants = []
        for f in raw_features[:100]:
            # Extract clinical significance
            clinical = []
            for cs in f.get("clinicalSignificances", []):
                clinical.append(
                    {
                        "type": cs.get("type"),
                        "sources": cs.get("sources", []),
                    }
                )

            # Extract disease associations
            associations = []
            for a in f.get("association", []):
                associations.append(
                    {
                        "name": a.get("name"),
                        "description": a.get("description"),
                        "is_disease": a.get("disease", False),
                    }
                )

            # Extract cross-references (first 3)
            xrefs = []
            for x in f.get("xrefs", [])[:3]:
                xrefs.append(
                    {
                        "database": x.get("name"),
                        "id": x.get("id"),
                        "url": x.get("url"),
                    }
                )

            variants.append(
                {
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "wild_type": f.get("wildType"),
                    "alternative": f.get("alternativeSequence"),
                    "source_type": f.get("sourceType"),
                    "clinical_significances": clinical if clinical else None,
                    "associations": associations if associations else None,
                    "xrefs": xrefs if xrefs else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "variants": variants,
                "total_variants": len(raw_features),
                "total_all_sources": len(data.get("features", [])),
                "source_counts": source_counts,
            },
            "metadata": {
                "source": "EBI Proteins API - Variation",
                "accession": accession,
            },
        }

    def _get_features(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein features filtered by category."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }
        category = arguments.get("category", "DOMAINS_AND_SITES")

        url = f"{PROTEINS_API_BASE_URL}/features/{accession}"
        params = {"categories": category}
        headers = {"Accept": "application/json"}
        response = requests.get(
            url, params=params, headers=headers, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        features = []
        for f in data.get("features", []):
            evidences = []
            for ev in f.get("evidences", [])[:3]:
                src = ev.get("source", {})
                evidences.append(
                    {
                        "code": ev.get("code"),
                        "source_name": src.get("name"),
                        "source_id": src.get("id"),
                    }
                )

            features.append(
                {
                    "type": f.get("type"),
                    "category": f.get("category"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "description": f.get("description"),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "sequence_length": len(data.get("sequence") or ""),
                "category_queried": category,
                "features": features[:100],
                "total_features": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - Features",
                "accession": accession,
            },
        }

    def _get_antigen(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get antigenic regions for a protein (useful for antibody design)."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        url = f"{PROTEINS_API_BASE_URL}/antigen/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        regions = []
        for f in data.get("features", []):
            evidences = []
            for ev in f.get("evidences", [])[:3]:
                src = ev.get("source", {})
                evidences.append(
                    {
                        "code": ev.get("code"),
                        "source_name": src.get("name"),
                        "source_id": src.get("id"),
                    }
                )

            regions.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "match_score": f.get("matchScore"),
                    "antigen_sequence": f.get("antigenSequence"),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "antigenic_regions": regions,
                "total_regions": len(regions),
            },
            "metadata": {
                "source": "EBI Proteins API - Antigen",
                "accession": accession,
            },
        }

    def _get_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genomic coordinates for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        url = f"{PROTEINS_API_BASE_URL}/coordinates/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        mappings = []
        for gc in data.get("gnCoordinate", []):
            gen_loc = gc.get("genomicLocation", {})
            exons = gen_loc.get("exon", [])
            mappings.append(
                {
                    "ensembl_gene_id": gc.get("ensemblGeneId"),
                    "ensembl_transcript_id": gc.get("ensemblTranscriptId"),
                    "chromosome": gen_loc.get("chromosome"),
                    "start": gen_loc.get("start"),
                    "end": gen_loc.get("end"),
                    "reverseStrand": gen_loc.get("reverseStrand"),
                    "num_exons": len(exons),
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "name": data.get("name"),
                "sequence_length": len(data.get("sequence", "")),
                "genomic_mappings": mappings,
                "total_mappings": len(mappings),
            },
            "metadata": {
                "source": "EBI Proteins API - Coordinates",
                "accession": accession,
            },
        }

    def _get_proteomics(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get proteomics peptide evidence for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }

        url = f"{PROTEINS_API_BASE_URL}/proteomics/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        peptides = []
        for f in data.get("features", []):
            evidences = []
            for ev in f.get("evidences", [])[:3]:
                src = ev.get("source", {})
                evidences.append(
                    {
                        "source": src.get("name"),
                        "id": src.get("id"),
                    }
                )

            peptides.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "peptide": f.get("peptide"),
                    "unique": f.get("unique"),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "peptides": peptides[:100],
                "total_peptides": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - Proteomics",
                "accession": accession,
            },
        }

    def _get_rna_editing(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get RNA editing annotations (A-to-I recoding sites) for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P42262 for GRIA2)",
            }
        accession = accession.strip()

        url = f"{PROTEINS_API_BASE_URL}/rna-editing/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        sites = []
        for f in data.get("features", []):
            vt = f.get("variantType") or {}
            loc = f.get("locationType") or {}
            position = (loc.get("position") or {}).get("position")
            variant_locations = []
            for vl in vt.get("variantLocation", []) or []:
                variant_locations.append(
                    {
                        "loc": vl.get("loc"),
                        "seq_id": vl.get("seqId"),
                        "source": vl.get("source"),
                    }
                )
            editing_info = f.get("rnaEditingInfo") or {}
            sites.append(
                {
                    "type": f.get("type"),
                    "position": position,
                    "genomic_location": vt.get("genomicLocation"),
                    "variant_locations": variant_locations
                    if variant_locations
                    else None,
                    "codon": vt.get("codon"),
                    "consequence_type": vt.get("consequenceType"),
                    "wild_type": vt.get("wildType"),
                    "mutated_type": vt.get("mutatedType"),
                    "somatic_status": vt.get("somaticStatus"),
                    "rna_editing_info": editing_info if editing_info else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "rna_editing_sites": sites,
                "total_sites": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - RNA Editing",
                "accession": accession,
            },
        }

    def _parse_variation_entries(self, data: Any) -> list:
        """Normalize variation-by-id responses (list of UniProt entries)."""
        if not isinstance(data, list):
            data = [data] if isinstance(data, dict) else []

        entries = []
        for e in data:
            if not isinstance(e, dict):
                continue
            features = []
            for f in e.get("features", []):
                xrefs = []
                for x in f.get("xrefs", [])[:5]:
                    xrefs.append(
                        {
                            "name": x.get("name"),
                            "id": x.get("id"),
                            "url": x.get("url"),
                        }
                    )
                clinical = [
                    cs.get("type") for cs in f.get("clinicalSignificances", []) or []
                ]
                features.append(
                    {
                        "type": f.get("type"),
                        "ft_id": f.get("ftId"),
                        "wild_type": f.get("wildType"),
                        "alternative_sequence": f.get("alternativeSequence"),
                        "begin": f.get("begin"),
                        "end": f.get("end"),
                        "genomic_location": f.get("genomicLocation"),
                        "consequence_type": f.get("consequenceType"),
                        "clinical_significances": clinical if clinical else None,
                        "xrefs": xrefs if xrefs else None,
                    }
                )
            entries.append(
                {
                    "accession": e.get("accession"),
                    "entry_name": e.get("entryName"),
                    "protein_name": e.get("proteinName"),
                    "gene_name": e.get("geneName"),
                    "taxid": e.get("taxid"),
                    "features": features,
                    "total_features": len(e.get("features", [])),
                }
            )
        return entries

    def _get_variation_by_dbsnp(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse variation lookup by dbSNP rsID -> UniProt proteins/positions."""
        dbsnp_id = arguments.get("dbsnp_id") or arguments.get("rsid") or ""
        if not dbsnp_id:
            return {
                "status": "error",
                "error": "dbsnp_id parameter is required (dbSNP rsID, e.g., 'rs1042522')",
            }
        dbsnp_id = str(dbsnp_id).strip()

        url = f"{PROTEINS_API_BASE_URL}/variation/dbsnp/{dbsnp_id}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = self._parse_variation_entries(data)
        return {
            "status": "success",
            "data": {
                "dbsnp_id": dbsnp_id,
                "entries": entries,
                "total_entries": len(entries),
            },
            "metadata": {
                "source": "EBI Proteins API - Variation by dbSNP",
                "dbsnp_id": dbsnp_id,
            },
        }

    def _get_variation_by_hgvs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse variation lookup by HGVS genomic expression -> UniProt entries."""
        hgvs = arguments.get("hgvs") or arguments.get("hgvs_expression") or ""
        if not hgvs:
            return {
                "status": "error",
                "error": "hgvs parameter is required (HGVS genomic expression, e.g., 'NC_000017.11:g.7676154G>A')",
            }
        hgvs = str(hgvs).strip()

        # requests handles URL-encoding of the '>' in the path segment.
        url = f"{PROTEINS_API_BASE_URL}/variation/hgvs/{hgvs}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        entries = self._parse_variation_entries(data)
        return {
            "status": "success",
            "data": {
                "hgvs": hgvs,
                "entries": entries,
                "total_entries": len(entries),
            },
            "metadata": {
                "source": "EBI Proteins API - Variation by HGVS",
                "hgvs": hgvs,
            },
        }

    def _get_proteomics_hpp(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get Human Proteome Project (HPP) peptide-level evidence for a protein."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P04637)",
            }
        accession = accession.strip()

        url = f"{PROTEINS_API_BASE_URL}/proteomics/hpp/{accession}"
        headers = {"Accept": "application/json"}
        response = requests.get(url, headers=headers, timeout=self.timeout)
        response.raise_for_status()
        data = response.json()

        peptides = []
        for f in data.get("features", []):
            evidences = []
            for ev in f.get("evidences", [])[:3]:
                src = ev.get("source", {}) or {}
                evidences.append(
                    {
                        "source": src.get("name"),
                        "id": src.get("id"),
                    }
                )
            peptides.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "peptide": f.get("peptide"),
                    "unique": f.get("unique"),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "peptides": peptides[:100],
                "total_peptides": len(data.get("features", [])),
            },
            "metadata": {
                "source": "EBI Proteins API - HPP Proteomics",
                "accession": accession,
            },
        }
