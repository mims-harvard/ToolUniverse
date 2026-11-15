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
UNIPROT_REST_BASE_URL = "https://rest.uniprot.org"


# How many per-transcript feature mappings a coordinates response carries.
# P04637 answers about 1,500 on one transcript, so the whole list would be the
# response; `features_total` is the true count.
FEATURES_PER_TRANSCRIPT = 50


def _pos(node, outer, end):
    """`node[outer][end].position`, which is how the API nests a coordinate."""
    inner = (node.get(outer) or {}).get(end) or {}
    return inner.get("position")


def _status(node, outer, end):
    """The coordinate's certainty, which sits beside the position."""
    inner = (node.get(outer) or {}).get(end) or {}
    return inner.get("status")


def _peptide_evidence(feature):
    """Peptide evidence with the numbers that make it evidence.

    The Proteins API answers each peptide's source with a `properties` map
    holding the mass-spectrometry support -- "Best Probability": "1.000",
    "Times of observations": "2", and per source also Score, Number of PSMs
    and Number of sample. Only the source name and id were carried, so a
    caller was told that a peptide has HPP evidence and nothing about how
    strong it is, for a tool whose description calls this "the stringent HPP
    evidence set". The ECO code and the source URL were dropped the same way.
    """
    out = []
    for ev in feature.get("evidences") or []:
        if not isinstance(ev, dict):
            continue
        src = ev.get("source") or {}
        properties = src.get("properties") if isinstance(src, dict) else None
        out.append(
            {
                "code": ev.get("code"),
                "source": src.get("name"),
                "id": src.get("id"),
                "url": src.get("url"),
                "support": {
                    str(key).strip().lower().replace(" ", "_"): value
                    for key, value in (properties or {}).items()
                },
            }
        )
    return out


def _clinical_significances(node):
    """Clinical significance with the review status that qualifies it.

    `reviewStatus` is what separates a ClinVar assertion with criteria and
    multiple submitters from one unreviewed submission. Reporting the type
    alone presents both as the same claim.
    """
    out = []
    for cs in node.get("clinicalSignificances") or []:
        if not isinstance(cs, dict):
            continue
        out.append(
            {
                "type": cs.get("type"),
                "sources": cs.get("sources") or [],
                "review_status": cs.get("reviewStatus"),
            }
        )
    return out


def _variation_feature(feature):
    """The parts of a variation feature that are the variant.

    Written once because the two code paths that read these features had
    drifted apart: the by-accession lookup returned eight of the twenty-one
    fields and the by-rsID lookup a different nine, and neither carried the
    SIFT/PolyPhen predictions, the population frequencies, the somatic status
    or the per-transcript HGVS that sit in the same response. Measured on
    P04637: 3,662 features, every one with a `consequenceType` and a
    `somaticStatus`, 1,127 with predictions, 526 with frequencies.
    """
    return {
        "variant_id": feature.get("ftId"),
        "feature_type": feature.get("type"),
        "position_start": feature.get("begin"),
        "position_end": feature.get("end"),
        "wild_type": feature.get("wildType"),
        "alternative": feature.get("alternativeSequence"),
        "mutated_type": feature.get("mutatedType"),
        "source_type": feature.get("sourceType"),
        "consequence_type": feature.get("consequenceType"),
        "somatic_status": feature.get("somaticStatus"),
        "codon": feature.get("codon"),
        "descriptions": [
            {"value": entry.get("value"), "sources": entry.get("sources") or []}
            for entry in (feature.get("descriptions") or [])
            if isinstance(entry, dict)
        ],
        "genomic_location": feature.get("genomicLocation"),
        "cytogenetic_band": feature.get("cytogeneticBand"),
        "locations": [
            {
                "hgvs": loc.get("loc"),
                "sequence_id": loc.get("seqId"),
                "source": loc.get("source"),
            }
            for loc in (feature.get("locations") or [])
            if isinstance(loc, dict)
        ],
        "predictions": [
            {
                "algorithm": pred.get("predAlgorithmNameType"),
                "prediction": pred.get("predictionValType"),
                "score": pred.get("score"),
                "predictor_type": pred.get("predictorType"),
                "sources": pred.get("sources") or [],
            }
            for pred in (feature.get("predictions") or [])
            if isinstance(pred, dict)
        ],
        "population_frequencies": [
            {
                "population": freq.get("populationName"),
                "frequency": freq.get("frequency"),
                "source": freq.get("source"),
            }
            for freq in (feature.get("populationFrequencies") or [])
            if isinstance(freq, dict)
        ],
        "evidences": _peptide_evidence(feature),
        "clinical_significances": _clinical_significances(feature),
        "associations": [
            {
                "name": a.get("name"),
                "description": a.get("description"),
                "is_disease": a.get("disease", False),
                "evidences": _peptide_evidence(a),
                "clinical_significances": _clinical_significances(a),
                # The disease's own identifiers -- OMIM/MIM among them --
                # without which a disease NAME cannot be resolved to a record.
                "db_references": [
                    {
                        "database": ref.get("name"),
                        "id": ref.get("id"),
                        "url": ref.get("url"),
                    }
                    for ref in (a.get("dbReferences") or [])
                    if isinstance(ref, dict)
                ],
            }
            for a in (feature.get("association") or [])
            if isinstance(a, dict)
        ],
    }


def _feature_xrefs(feature):
    """The feature's cross-references, with the properties each one carries.

    An antigen xref's `properties` hold the source's "gene ID" and "protein
    sequence ID"; a PTM's hold the Pubmed ID, the Universal Spectrum Id and the
    ProForma string. Those are the identifiers the cross-reference exists to
    give, so a name and an id without them is half the reference.
    """
    out = []
    for x in feature.get("xrefs") or []:
        if not isinstance(x, dict):
            continue
        out.append(
            {
                "name": x.get("name"),
                "id": x.get("id"),
                "url": x.get("url"),
                "properties": {
                    str(key).strip().lower().replace(" ", "_"): value
                    for key, value in (x.get("properties") or {}).items()
                },
            }
        )
    return out


def _paginate(items, arguments: Dict[str, Any], default_limit: int = 100):
    """Return one local page plus explicit collection completeness metadata."""
    limit = int(arguments.get("limit", default_limit))
    offset = int(arguments.get("offset", 0))
    page = items[offset : offset + limit]
    next_offset = offset + len(page)
    has_more = next_offset < len(items)
    return page, {
        "returned": len(page),
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "truncated": has_more,
        "next_offset": next_offset if has_more else None,
    }


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

        raw_features = data.get("features", [])
        page_features, paging = _paginate(raw_features, arguments)
        features = []
        for f in page_features:
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
                    "xrefs": _feature_xrefs(f),
                    "evidences": evidences,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "gene_name": None,
                "features": features,
                "total_features": len(raw_features),
                **paging,
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

        raw_features = data.get("features", [])
        page_features, paging = _paginate(raw_features, arguments)
        features = []
        for f in page_features:
            evidences = _peptide_evidence(f)

            features.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "description": f.get("description"),
                    "xrefs": _feature_xrefs(f),
                    # The modifications themselves. The response nests each
                    # PTM under `ptms` with its name, the residue it sits on
                    # and its own references -- the Pubmed ID, the Universal
                    # Spectrum Id and the ProForma string that let a site be
                    # traced back to a spectrum. A row that gives the feature
                    # span and no PTM has not answered the question.
                    "ptms": [
                        {
                            "name": ptm.get("name"),
                            "position": ptm.get("position"),
                            "sources": ptm.get("sources") or [],
                            "db_references": [
                                {
                                    "database": ref.get("name"),
                                    "id": ref.get("id"),
                                    "url": ref.get("url"),
                                    "properties": {
                                        str(key).strip().lower().replace(" ", "_"): val
                                        for key, val in (
                                            ref.get("properties") or {}
                                        ).items()
                                    },
                                }
                                for ref in (ptm.get("dbReferences") or [])
                                if isinstance(ref, dict)
                            ],
                        }
                        for ptm in (f.get("ptms") or [])
                        if isinstance(ptm, dict)
                    ],
                    "evidences": evidences,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "features": features,
                "total_features": len(raw_features),
                **paging,
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

        page_features, paging = _paginate(raw_features, arguments)
        variants = []
        for f in page_features:
            # Preserve all cross-references. A real TP53 response contains up
            # to 43 references for a single variant; keeping only three made
            # ClinVar/COSMIC/dbSNP support disappear without warning.
            xrefs = [
                {"database": x.get("name"), "id": x.get("id"), "url": x.get("url")}
                for x in (f.get("xrefs") or [])
                if isinstance(x, dict)
            ]
            variants.append({**_variation_feature(f), "xrefs": xrefs or None})

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "variants": variants,
                "total_variants": len(raw_features),
                "total_all_sources": len(data.get("features", [])),
                "source_counts": source_counts,
                **paging,
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

        raw_features = data.get("features", [])
        page_features, paging = _paginate(raw_features, arguments)
        features = []
        for f in page_features:
            evidences = _peptide_evidence(f)

            ligand = f.get("ligand") or {}
            features.append(
                {
                    "type": f.get("type"),
                    "category": f.get("category"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "description": f.get("description"),
                    # For a binding site, WHAT binds there. A
                    # DOMAINS_AND_SITES feature that says "Binding site" at
                    # position 175 and not which ligand has named the location
                    # and not the fact.
                    "ligand": {
                        "name": ligand.get("name"),
                        "id": (ligand.get("dbReference") or {}).get("id"),
                        "database": (ligand.get("dbReference") or {}).get("name"),
                        "label": ligand.get("label"),
                        "note": ligand.get("note"),
                    }
                    if ligand
                    else None,
                    "ligand_part": f.get("ligandPart"),
                    "xrefs": _feature_xrefs(f),
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
                "features": features,
                "total_features": len(raw_features),
                **paging,
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
            # The evidence list was cut to three with nothing said. The cut
            # stays, since an antigenic region can carry many, but the row now
            # says what it is a cut of.
            all_evidences = _peptide_evidence(f)
            evidences = all_evidences[:3]

            regions.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "match_score": f.get("matchScore"),
                    "antigen_sequence": f.get("antigenSequence"),
                    # Which antibody or construct the region came from. The
                    # xrefs carry the source's gene and protein sequence ids,
                    # and without them a region is a span with no provenance.
                    "xrefs": _feature_xrefs(f),
                    "evidences": evidences if evidences else None,
                    "evidences_total": len(all_evidences),
                    "evidences_truncated": len(evidences) < len(all_evidences),
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
            features = gc.get("feature") or []
            mappings.append(
                {
                    "ensembl_gene_id": gc.get("ensemblGeneId"),
                    "ensembl_transcript_id": gc.get("ensemblTranscriptId"),
                    "ensembl_translation_id": gc.get("ensemblTranslationId"),
                    "chromosome": gen_loc.get("chromosome"),
                    "start": gen_loc.get("start"),
                    "end": gen_loc.get("end"),
                    "reverseStrand": gen_loc.get("reverseStrand"),
                    "assembly_name": gen_loc.get("assemblyName"),
                    "nucleotide_id": gen_loc.get("nucleotideId"),
                    "num_exons": len(exons),
                    # The exons themselves. A tool named for coordinates
                    # answered `num_exons: 11` -- the count -- and dropped
                    # every exon's protein span, genomic span and Ensembl id,
                    # which is the mapping the caller came for.
                    "exons": [
                        {
                            "exon_id": exon.get("id"),
                            "protein_start": _pos(exon, "proteinLocation", "begin"),
                            "protein_end": _pos(exon, "proteinLocation", "end"),
                            "genome_start": _pos(exon, "genomeLocation", "begin"),
                            "genome_end": _pos(exon, "genomeLocation", "end"),
                        }
                        for exon in exons
                        if isinstance(exon, dict)
                    ],
                    # Where each annotated feature of the protein lands on the
                    # genome. Capped, because P04637 answers 1,500 of them on
                    # one transcript, and disclosed per the row-axis
                    # convention.
                    "features": [
                        {
                            "feature_id": feat.get("id"),
                            "type": feat.get("type"),
                            "description": feat.get("description"),
                            "original": feat.get("original"),
                            "variation": feat.get("variation") or [],
                            "genome_start": _pos(feat, "genomeLocation", "begin"),
                            "genome_end": _pos(feat, "genomeLocation", "end"),
                            # "certain" or "uncertain". A coordinate whose
                            # status the caller cannot see reads as exact.
                            "genome_start_status": _status(
                                feat, "genomeLocation", "begin"
                            ),
                            "genome_end_status": _status(feat, "genomeLocation", "end"),
                            "protein_position": (
                                (feat.get("location") or {}).get("position") or {}
                            ).get("position"),
                            "evidence": [
                                {
                                    "code": ev.get("code"),
                                    "database": (ev.get("dbReference") or {}).get(
                                        "name"
                                    ),
                                    "id": (ev.get("dbReference") or {}).get("id"),
                                }
                                for ev in (feat.get("evidence") or [])
                                if isinstance(ev, dict)
                            ],
                        }
                        for feat in features[:FEATURES_PER_TRANSCRIPT]
                        if isinstance(feat, dict)
                    ],
                    "features_total": len(features),
                    "features_truncated": FEATURES_PER_TRANSCRIPT < len(features),
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

        raw_features = data.get("features", [])
        page_features, paging = _paginate(raw_features, arguments)
        peptides = []
        for f in page_features:
            evidences = _peptide_evidence(f)
            peptides.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "peptide": f.get("peptide"),
                    "unique": f.get("unique"),
                    "xrefs": _feature_xrefs(f),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "peptides": peptides,
                "total_peptides": len(raw_features),
                **paging,
            },
            "metadata": {
                "source": "EBI Proteins API - Proteomics",
                "accession": accession,
            },
        }

    def _get_rna_editing(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """RNA editing (A-to-I recoding) sites for a protein, read from UniProt.

        Not from the Proteins API, although it documents the endpoint this used
        to call. /rna-editing serves nothing: ?offset=0&size=1&taxid=<tx>
        returns 0 records for human, mouse, rat and fly alike, and
        /rna-editing/P42262 answers 404 "Can not find Features for accession"
        for GRIA2, the textbook Q/R site. Both URL shapes are in the API's own
        openapi.json, so the tool was calling it correctly -- the dataset is
        empty.

        UniProtKB has the annotation: P42262 position 607 with PubMed:7523595,
        and P28335 (5HT2C) positions 156, 158 and 160 with PubMed:9928237. So
        this reads cc_rna_editing from the UniProt REST entry instead. The
        fields UniProt curates are the position, its evidence and the curator's
        note; codon, genomic location and consequence type were in the Proteins
        API's feature shape and have no UniProt equivalent, so they are gone
        from the output rather than reported as permanently null.
        """
        accession = arguments.get("accession", "")
        if not accession:
            return {
                "status": "error",
                "error": "accession parameter is required (UniProt accession, e.g., P42262 for GRIA2)",
            }
        accession = accession.strip()

        url = f"{UNIPROT_REST_BASE_URL}/uniprotkb/{accession}.json"
        try:
            response = requests.get(
                url,
                params={"fields": "cc_rna_editing,accession,id"},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
        except requests.exceptions.RequestException as exc:
            return {
                "status": "error",
                "error": f"UniProt request failed: {exc}",
                "url": url,
            }
        if response.status_code in (400, 404):
            # 404 for a well-formed accession UniProt does not hold, 400 for
            # one it cannot parse at all. Both mean the same thing to a caller.
            return {
                "status": "error",
                "error": (
                    f"UniProt has no entry for accession '{accession}' "
                    "(expected a UniProt accession such as P42262)"
                ),
                "url": url,
            }
        if response.status_code != 200:
            return {
                "status": "error",
                "error": f"UniProt returned HTTP {response.status_code}",
                "url": url,
            }
        try:
            data = response.json()
        except ValueError:
            return {
                "status": "error",
                "error": "UniProt returned a response that is not JSON",
                "url": url,
            }

        def _evidences(node):
            out = []
            for ev in node.get("evidences") or []:
                out.append(
                    {
                        "code": ev.get("evidenceCode"),
                        "source": ev.get("source"),
                        "id": ev.get("id"),
                    }
                )
            return out or None

        sites = []
        notes = []
        location_types = []
        for comment in data.get("comments") or []:
            if not (comment.get("commentType") or "").upper().startswith("RNA EDIT"):
                continue
            if comment.get("locationType"):
                location_types.append(comment["locationType"])
            for position in comment.get("positions") or []:
                raw = position.get("position")
                try:
                    parsed = int(raw)
                except (TypeError, ValueError):
                    parsed = None
                sites.append(
                    {
                        "type": "RNA editing",
                        "position": parsed,
                        "evidences": _evidences(position),
                    }
                )
            for text in (comment.get("note") or {}).get("texts") or []:
                notes.append({"text": text.get("value"), "evidences": _evidences(text)})

        return {
            "status": "success",
            "data": {
                "accession": data.get("primaryAccession") or accession,
                "entry_name": data.get("uniProtkbId"),
                "rna_editing_sites": sites,
                "total_sites": len(sites),
                # "Known", "Not_applicable" or "Undetermined" -- UniProt says
                # how precisely the edited positions are known, which is not
                # the same as there being none.
                "location_type": location_types[0] if location_types else None,
                "notes": notes or None,
            },
            "metadata": {
                "source": "UniProtKB REST (cc_rna_editing)",
                "accession": accession,
                "source_note": (
                    "The EBI Proteins API /rna-editing endpoint still exists but "
                    "serves no records for any taxon, so this reads UniProtKB"
                ),
            },
        }

    def _parse_variation_entries(self, data: Any, arguments: Dict[str, Any]) -> list:
        """Normalize variation-by-id responses (list of UniProt entries)."""
        if not isinstance(data, list):
            data = [data] if isinstance(data, dict) else []
        xref_offset = max(int(arguments.get("xref_offset") or 0), 0)
        xref_limit = min(max(int(arguments.get("xref_limit") or 5), 1), 500)

        entries = []
        for e in data:
            if not isinstance(e, dict):
                continue
            features = []
            for f in e.get("features", []):
                all_xrefs = f.get("xrefs", [])
                xref_page = all_xrefs[xref_offset : xref_offset + xref_limit]
                xrefs = []
                for x in xref_page:
                    xrefs.append(
                        {
                            "name": x.get("name"),
                            "id": x.get("id"),
                            "url": x.get("url"),
                        }
                    )
                features.append(
                    {
                        **_variation_feature(f),
                        # Kept for callers that read the pre-existing names.
                        "type": f.get("type"),
                        "ft_id": f.get("ftId"),
                        "alternative_sequence": f.get("alternativeSequence"),
                        "begin": f.get("begin"),
                        "end": f.get("end"),
                        "xrefs": xrefs if xrefs else None,
                        "xrefs_total": len(all_xrefs),
                        "xrefs_returned": len(xref_page),
                        "xrefs_truncated": (
                            xref_offset + len(xref_page) < len(all_xrefs)
                        ),
                        "next_xref_offset": (
                            xref_offset + len(xref_page)
                            if xref_offset + len(xref_page) < len(all_xrefs)
                            else None
                        ),
                    }
                )
            entries.append(
                {
                    "accession": e.get("accession"),
                    "entry_name": e.get("entryName"),
                    "protein_name": e.get("proteinName"),
                    "gene_name": e.get("geneName"),
                    "taxid": e.get("taxid"),
                    # Which species the entry is. A reverse lookup by rsID
                    # answers several UniProt entries and the taxid alone made
                    # telling the human one from an ortholog a second call.
                    "organism_name": e.get("organismName"),
                    "protein_existence": e.get("proteinExistence"),
                    "sequence": e.get("sequence"),
                    "sequence_checksum": e.get("sequenceChecksum"),
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

        entries = self._parse_variation_entries(data, arguments)
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

        entries = self._parse_variation_entries(data, arguments)
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

        raw_features = data.get("features", [])
        page_features, paging = _paginate(raw_features, arguments)
        peptides = []
        for f in page_features:
            evidences = _peptide_evidence(f)
            peptides.append(
                {
                    "type": f.get("type"),
                    "position_start": f.get("begin"),
                    "position_end": f.get("end"),
                    "peptide": f.get("peptide"),
                    "unique": f.get("unique"),
                    "xrefs": _feature_xrefs(f),
                    "evidences": evidences if evidences else None,
                }
            )

        return {
            "status": "success",
            "data": {
                "accession": data.get("accession"),
                "entry_name": data.get("entryName"),
                "peptides": peptides,
                "total_peptides": len(raw_features),
                **paging,
            },
            "metadata": {
                "source": "EBI Proteins API - HPP Proteomics",
                "accession": accession,
            },
        }
