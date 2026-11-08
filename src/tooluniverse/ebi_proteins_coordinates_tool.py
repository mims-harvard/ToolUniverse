# ebi_proteins_coordinates_tool.py
"""
EBI Proteins Coordinates tool for ToolUniverse.

The EBI Proteins API Coordinates endpoint maps UniProt protein positions to
genomic coordinates at exon-level resolution. This enables translation between
protein residue numbering and chromosomal positions, essential for connecting
variant-level information across protein and genome databases.

API: https://www.ebi.ac.uk/proteins/api/coordinates/
No authentication required.
"""

import requests
from typing import Dict, Any
from .base_tool import BaseTool
from .tool_registry import register_tool

EBI_PROTEINS_BASE_URL = "https://www.ebi.ac.uk/proteins/api"


# The coordinates endpoint attaches UniProt's whole feature table to each
# transcript mapping, already projected onto the genome: TP53's first
# transcript carries 1,514 of them, 16,654 across its eleven transcripts, and
# none reached the caller. They are paged like the exons, with the count, the
# per-type breakdown and the cut reported.
FEATURES_PER_MAPPING = 50


def _position(node: Any) -> Any:
    """A UniProt location node, which is `position` or `begin`/`end`."""
    if not isinstance(node, dict):
        return None
    for key in ("position", "begin", "end"):
        value = node.get(key)
        if isinstance(value, dict) and value.get("position") is not None:
            return value.get("position")
    return None


def _evidence(feature: Dict[str, Any]) -> list:
    """The evidence behind one annotation, under either of the two names.

    This endpoint answers `evidence`; `/proteins/api/features` answers
    `evidences`. Reading only the plural made `evidence_count` 0 for all 264
    features of 17:7676154, of which 154 carry evidence -- ECO:0000269 with
    the PubMed ids that assert it. A count of zero reads as "no evidence",
    not as "not looked at", which is why this is reported as the records
    rather than a number.
    """
    rows = []
    for item in feature.get("evidence") or feature.get("evidences") or []:
        if not isinstance(item, dict):
            continue
        reference = item.get("dbReference") or item.get("source") or {}
        rows.append(
            {
                "code": item.get("code"),
                "source_database": reference.get("type"),
                "source_id": reference.get("id"),
            }
        )
    return rows


def _feature_row(feature: Dict[str, Any]) -> Dict[str, Any]:
    """One annotation with both coordinate systems it was mapped between."""
    location = feature.get("location") or {}
    genome = feature.get("genomeLocation") or {}
    begin = location.get("begin") or {}
    end = location.get("end") or {}
    position = location.get("position") or {}
    variations = feature.get("variation")
    if isinstance(variations, str):
        variations = [variations]
    return {
        "type": feature.get("type"),
        "id": feature.get("id"),
        "description": feature.get("description"),
        "original": feature.get("original"),
        "variation": [v for v in (variations or []) if v],
        "protein_position": position.get("position"),
        "protein_start": begin.get("position"),
        "protein_end": end.get("position"),
        "genome_start": (genome.get("begin") or {}).get("position"),
        "genome_end": (genome.get("end") or {}).get("position"),
        # The ECO codes and the publications that assert the annotation.
        "evidence": _evidence(feature),
        "evidence_count": len(_evidence(feature)),
    }


def _feature_page(features: Any, offset: int, limit: int) -> Dict[str, Any]:
    """The requested page of features, the full count, and the breakdown."""
    if isinstance(features, dict):
        features = [features]
    if not isinstance(features, list):
        features = []
    features = [f for f in features if isinstance(f, dict)]
    counts: Dict[str, int] = {}
    for feature in features:
        key = feature.get("type") or "unknown"
        counts[key] = counts.get(key, 0) + 1
    page = features[offset : offset + limit]
    truncated = offset + len(page) < len(features)
    return {
        "features": [_feature_row(f) for f in page],
        "feature_count": len(features),
        "feature_type_counts": dict(sorted(counts.items())),
        "feature_offset": offset,
        "features_returned": len(page),
        "features_truncated": truncated,
        "next_feature_offset": offset + len(page) if truncated else None,
    }


@register_tool("EBIProteinsCoordinatesTool")
class EBIProteinsCoordinatesTool(BaseTool):
    """
    Tool for querying EBI Proteins API coordinate mappings.

    Supports:
    - Map protein positions to genomic coordinates (exon-level)
    - Get protein-to-genome coordinate mappings for a UniProt accession

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        fields = tool_config.get("fields", {})
        self.endpoint = fields.get("endpoint", "get_coordinates")

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the EBI Proteins Coordinates API call."""
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
            status = e.response.status_code if e.response is not None else "unknown"
            if status == 404:
                return {
                    "status": "error",
                    "error": "Protein not found. Provide a valid UniProt accession (e.g., 'P04637' for TP53).",
                }
            if status == 400:
                return {
                    "status": "error",
                    "error": "Bad request. Check the UniProt accession format.",
                }
            return {"status": "error", "error": f"EBI Proteins API HTTP {status}"}
        except Exception as e:
            return {"status": "error", "error": f"Unexpected error: {str(e)}"}

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to appropriate endpoint."""
        if self.endpoint == "get_coordinates":
            return self._get_coordinates(arguments)
        elif self.endpoint == "glocation":
            return self._get_proteins_by_genomic_loc(arguments)
        else:
            return {"status": "error", "error": f"Unknown endpoint: {self.endpoint}"}

    def _get_coordinates(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get protein-to-genomic coordinate mappings."""
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession is required (UniProt accession, e.g., 'P04637' for TP53, 'P00533' for EGFR).",
            }

        accession = accession.strip()
        url = f"{EBI_PROTEINS_BASE_URL}/coordinates/{accession}"
        response = requests.get(
            url, timeout=self.timeout, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        # Extract gene info
        gene_info = []
        for g in data.get("gene", []):
            gene_info.append(
                {
                    "value": g.get("value"),
                    "type": g.get("type"),
                }
            )

        # Extract genomic coordinates
        gn_coordinates = data.get("gnCoordinate", [])
        coordinate_offset = max(int(arguments.get("coordinate_offset") or 0), 0)
        coordinate_limit = min(
            max(int(arguments.get("coordinate_limit") or 10), 1), 500
        )
        exon_offset = max(int(arguments.get("exon_offset") or 0), 0)
        exon_limit = min(max(int(arguments.get("exon_limit") or 20), 1), 1000)
        feature_offset = max(int(arguments.get("feature_offset") or 0), 0)
        feature_limit = min(
            max(int(arguments.get("feature_limit") or FEATURES_PER_MAPPING), 1), 1000
        )
        coordinate_page = gn_coordinates[
            coordinate_offset : coordinate_offset + coordinate_limit
        ]
        mappings = []
        for gc in coordinate_page:
            genomic_loc = gc.get("genomicLocation", {})
            exons = genomic_loc.get("exon", [])
            exon_page = exons[exon_offset : exon_offset + exon_limit]

            exon_mappings = []
            for exon in exon_page:
                prot_loc = exon.get("proteinLocation", {})
                genome_loc = exon.get("genomeLocation", {})
                exon_mappings.append(
                    {
                        "exon_id": exon.get("id"),
                        "protein_start": prot_loc.get("begin", {}).get("position"),
                        "protein_end": prot_loc.get("end", {}).get("position"),
                        "genome_start": genome_loc.get("begin", {}).get("position"),
                        "genome_end": genome_loc.get("end", {}).get("position"),
                    }
                )

            mappings.append(
                {
                    "ensembl_gene_id": gc.get("ensemblGeneId"),
                    "ensembl_transcript_id": gc.get("ensemblTranscriptId"),
                    "ensembl_translation_id": gc.get("ensemblTranslationId"),
                    "chromosome": genomic_loc.get("chromosome"),
                    "start": genomic_loc.get("start"),
                    "end": genomic_loc.get("end"),
                    "reverse_strand": genomic_loc.get("reverseStrand"),
                    # Which assembly the genome positions are against, and the
                    # nucleotide record they came from. A coordinate without
                    # its assembly is not a coordinate.
                    "assembly_name": genomic_loc.get("assemblyName"),
                    "nucleotide_id": genomic_loc.get("nucleotideId"),
                    "num_exons": len(exons),
                    "exon_offset": exon_offset,
                    "exons_returned": len(exon_page),
                    "exons_truncated": exon_offset + len(exon_page) < len(exons),
                    "next_exon_offset": (
                        exon_offset + len(exon_page)
                        if exon_offset + len(exon_page) < len(exons)
                        else None
                    ),
                    "exons": exon_mappings,
                    **_feature_page(
                        gc.get("feature"), feature_offset, feature_limit
                    ),
                }
            )

        mappings_truncated = coordinate_offset + len(coordinate_page) < len(
            gn_coordinates
        )
        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "protein_name": data.get("name"),
                # `name` is the UniProt entry name (P53_HUMAN); the recommended
                # protein name is a separate field and was dropped.
                "protein": data.get("protein"),
                # `sequence` is a bare string on this endpoint and an object
                # on others; the length is what a coordinate caller needs.
                "sequence_length": (
                    len(data["sequence"])
                    if isinstance(data.get("sequence"), str)
                    else len((data.get("sequence") or {}).get("sequence", "")) or None
                    if isinstance(data.get("sequence"), dict)
                    else None
                ),
                "taxid": data.get("taxid"),
                "gene": gene_info,
                "coordinate_mappings": mappings,
                "total_coordinate_mappings": len(gn_coordinates),
                "coordinate_offset": coordinate_offset,
                "coordinate_mappings_returned": len(coordinate_page),
                "coordinate_mappings_truncated": mappings_truncated,
                "next_coordinate_offset": (
                    coordinate_offset + len(coordinate_page)
                    if mappings_truncated
                    else None
                ),
            },
            "metadata": {
                "source": "EBI Proteins API (ebi.ac.uk/proteins/api)",
                "total_transcript_mappings": len(gn_coordinates),
                "returned_mappings": len(mappings),
                "coordinate_offset": coordinate_offset,
            },
        }

    def _get_proteins_by_genomic_loc(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Reverse genome->protein lookup: genomic position -> overlapping proteins."""
        taxonomy = arguments.get("taxonomy") or arguments.get("taxid") or "9606"
        chromosome = arguments.get("chromosome")
        position = arguments.get("position")
        location = arguments.get("location")

        # Accept either a combined "17:7676154" location string, or separate
        # chromosome + position arguments.
        if not location:
            if chromosome is None or position is None:
                return {
                    "status": "error",
                    "error": (
                        "Provide 'location' (e.g., '17:7676154') or both "
                        "'chromosome' and 'position' (e.g., chromosome='17', position=7676154)."
                    ),
                }
            location = f"{str(chromosome).strip()}:{str(position).strip()}"
        location = str(location).strip()
        feature_offset = max(int(arguments.get("feature_offset") or 0), 0)
        feature_limit = min(
            max(int(arguments.get("feature_limit") or FEATURES_PER_MAPPING), 1), 1000
        )

        url = f"{EBI_PROTEINS_BASE_URL}/coordinates/glocation/{str(taxonomy).strip()}/{location}"
        response = requests.get(
            url, timeout=self.timeout, headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = [data] if isinstance(data, dict) else []

        entries = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            for loc in entry.get("locations", []):
                if not isinstance(loc, dict):
                    continue
                entries.append(
                    {
                        "accession": loc.get("accession"),
                        "entry_type": loc.get("entryType"),
                        "taxid": loc.get("taxid"),
                        "ensembl_gene_id": loc.get("ensemblGeneId"),
                        "ensembl_transcript_id": loc.get("ensemblTranscriptId"),
                        "ensembl_translation_id": loc.get("ensemblTranslationId"),
                        "protein_start": loc.get("proteinStart"),
                        "protein_end": loc.get("proteinEnd"),
                        "amino_acids": loc.get("aminoAcids"),
                        "chromosome": loc.get("chromosome"),
                        "gene_start": loc.get("geneStart"),
                        "gene_end": loc.get("geneEnd"),
                        "reverse_strand": loc.get("reverseStrand"),
                        "assembly_name": loc.get("assemblyName"),
                        "nucleotide_id": loc.get("nucleotideId"),
                        # The annotations at the position asked about, which is
                        # what a genome-to-protein lookup is for. 264 of them
                        # came back for 17:7676154 and none was reported.
                        **_feature_page(
                            loc.get("features"), feature_offset, feature_limit
                        ),
                    }
                )

        return {
            "status": "success",
            "data": {
                "taxonomy": str(taxonomy).strip(),
                "location": location,
                "proteins": entries,
                "total_proteins": len(entries),
            },
            "metadata": {
                "source": "EBI Proteins API - Genomic Location",
                "url": url,
            },
        }
