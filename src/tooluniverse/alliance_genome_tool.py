# alliance_genome_tool.py
"""
Alliance of Genome Resources REST API tool for ToolUniverse.

The Alliance of Genome Resources (AGR) integrates data from 7 model organism
databases (SGD, FlyBase, WormBase, ZFIN, RGD, MGI, Xenbase) plus human data.
It provides unified access to gene information, disease associations,
phenotypes, and cross-species search across all model organisms.

API: https://www.alliancegenome.org/api
No authentication required.
"""

import re
from html import unescape
from typing import Dict, Any

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

ALLIANCE_BASE = "https://www.alliancegenome.org/api"

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    """Strip inline HTML markup from an Alliance text field.

    Alliance phenotype/description fields embed markup (e.g. italicised gene
    symbols: 'anatomical structure <i>acta1a</i> expression decreased amount')
    that leaks literal <i>...</i> tags into the JSON a caller renders. Remove the
    tags and unescape entities so downstream consumers get clean plain text."""
    if not isinstance(text, str):
        return text
    # Unescape entities FIRST so an entity-encoded tag ('&lt;i&gt;') becomes a
    # real tag and is then removed too, not just literal '<i>' markup.
    return _HTML_TAG_RE.sub("", unescape(text)).strip()


def _display(value):
    """Alliance wraps names as {"displayText": ...}; return the text (or None)."""
    if isinstance(value, dict):
        return value.get("displayText") or value.get("name")
    return value


def _variant_consequence(node):
    """One predicted consequence of a variant, as Alliance reports it."""
    transcript = node.get("variantTranscript") or {}
    return {
        "transcript": transcript.get("name"),
        "transcript_type": (transcript.get("transcriptType") or {}).get("name"),
        "vep_impact": (node.get("vepImpact") or {}).get("name"),
        "vep_consequences": [
            c.get("name")
            for c in (node.get("vepConsequences") or [])
            if isinstance(c, dict) and c.get("name")
        ],
        "hgvs_coding": node.get("hgvsCodingNomenclature"),
        "sequence_feature": node.get("sequenceFeatureName"),
        "intron_exon_location": node.get("intronExonLocation"),
        "gene_level_consequence": node.get("geneLevelConsequence"),
        "amino_acid_reference": node.get("aminoAcidReference"),
        "amino_acid_variant": node.get("aminoAcidVariant"),
        "codon_reference": node.get("codonReference"),
        "codon_variant": node.get("codonVariant"),
    }


def _allele_variants(variant_list):
    """An allele's variants with their locations and predicted consequences."""
    out = []
    for variant in variant_list or []:
        if not isinstance(variant, dict):
            continue
        locations = []
        for loc in variant.get("curatedVariantGenomicLocations") or []:
            if not isinstance(loc, dict):
                continue
            locations.append(
                {
                    "start": loc.get("start"),
                    "end": loc.get("end"),
                    "hgvs": loc.get("hgvs"),
                    "hgvs_coding": loc.get("hgvsC"),
                    "reference_sequence": loc.get("referenceSequence"),
                    "variant_sequence": loc.get("variantSequence"),
                    "most_severe_consequence": _display(
                        loc.get("mostSevereConsequence")
                    ),
                    "predicted_consequences": [
                        _variant_consequence(pc)
                        for pc in (loc.get("predictedVariantConsequences") or [])
                        if isinstance(pc, dict)
                    ],
                }
            )
        out.append(
            {
                "variant_type": _display(variant.get("variantType"))
                or variant.get("type"),
                "nucleotide_change": variant.get("nucleotideChange"),
                "locations": locations,
            }
        )
    return out


def _allele_summary(record):
    """Flatten one /gene/{id}/alleles record.

    The API nests the allele under ``allele`` (``primaryExternalId`` and
    ``alleleSymbol.displayText`` for curated alleles such as zebrafish; only a
    ``curie`` for the variant-only records returned for fly, mouse, rat, worm, yeast
    and human) and lists variants under ``variantList``. The old code read ``id``,
    ``symbol`` and ``symbolText`` from the top level, so every allele came back with
    null identifiers.
    """
    allele = record.get("allele") or {}
    symbol = _display(allele.get("alleleSymbol")) or record.get("symbol")
    all_variants = record.get("variantList") or []
    variants = []
    for v in all_variants[:VARIANTS_PER_ALLELE]:
        locations = v.get("curatedVariantGenomicLocations") or []
        loc = locations[0] if locations else {}
        consequence = loc.get("mostSevereConsequence")
        variants.append(
            {
                "id": v.get("id") or v.get("primaryExternalId"),
                "name": loc.get("hgvs"),
                "type": _display(v.get("variantType")),
                "location": {
                    "chromosome": _display(
                        loc.get("variantGenomicLocationAssociationObject")
                    ),
                    "start": loc.get("start"),
                    "end": loc.get("end"),
                    "hgvs": loc.get("hgvs"),
                }
                if loc
                else None,
                "most_severe_consequence": _display(consequence),
            }
        )
    return {
        "id": allele.get("primaryExternalId")
        or allele.get("curie")
        or record.get("id"),
        # The curie Alliance's own endpoints take. For a curated allele
        # `primaryExternalId` wins the `or` above and the curie never reached
        # the caller, so the id in hand was not the one the next call wants.
        "alliance_curie": allele.get("curie"),
        "symbol": symbol,
        "symbol_text": symbol or record.get("symbolText"),
        "synonyms": [
            _display(x) for x in allele.get("alleleSynonyms") or [] if _display(x)
        ],
        "category": record.get("category"),
        "alteration_type": record.get("alterationType"),
        "has_disease": record.get("hasDisease"),
        "has_phenotype": record.get("hasPhenotype"),
        "variants": variants,
        # The variant list was cut to three with nothing said, which is the row
        # axis inside a record: an allele with 40 variants read as an allele
        # with 3.
        "variants_total": len(all_variants),
        "variants_returned": len(variants),
        "variants_truncated": len(variants) < len(all_variants),
    }


# How many variants of one allele are carried. Three was the existing cut and
# is kept; `variants_total` now says what it is a cut of.
VARIANTS_PER_ALLELE = 3


# How many publication curies a gene detail carries. The MGI record for a
# well-studied gene lists 4,461; returning all of them would make the
# literature list the response. `reference_curies_total` is the true count.
REFERENCE_CURIE_CAP = 50


def _mi_term(node):
    """An MI-ontology term as `{id, name}`, or None.

    Alliance answers these as `{curie, name, definition}`; the definition is a
    paragraph of ontology prose, so only the id and the name are carried.
    """
    if not isinstance(node, dict):
        return None
    curie = node.get("curie")
    name = node.get("name")
    if curie is None and name is None:
        return None
    return {"id": curie, "name": name}


def _alliance_references(evidence):
    """The publications behind an association, as Alliance reports them."""
    if not isinstance(evidence, list):
        return []
    out = []
    for item in evidence:
        if not isinstance(item, dict):
            continue
        out.append(
            {
                "agr_curie": item.get("curie"),
                "pubmed_id": item.get("referenceID"),
                "mod_id": item.get("pubModID"),
                "citation": item.get("shortCitation"),
                "cross_references": [
                    xref.get("referencedCurie")
                    for xref in (item.get("crossReferences") or [])
                    if isinstance(xref, dict) and xref.get("referencedCurie")
                ],
            }
        )
    return out


# Phenotype ontology terms per annotated row. MGI's Pax6 page carries one
# term on each of 125 annotations, so the cap only guards an outlier.
PHENOTYPE_TERMS_PER_ROW = 25
PHENOTYPE_DEFINITION_CHARACTERS = 400


def _phenotype_terms(annotations: list) -> list:
    """The ontology terms behind a phenotype statement.

    MGI_get_phenotypes says in its own description that it returns "Mammalian
    Phenotype (MP) ontology annotations", and the row returned
    `phenotype_statement` -- free text -- with no term and no id. Every one
    of the 125 annotations on MGI:97490 carries
    `{"curie": "MP:0005193", "name": "abnormal anterior eye segment
    morphology", "definition": ...}`, and the curie is the only thing that
    joins a phenotype to any ontology tool.
    """
    out, seen = [], set()
    for annotation in annotations:
        for term in annotation.get("phenotypeTerms") or []:
            if not isinstance(term, dict):
                continue
            curie = term.get("curie")
            key = curie or term.get("name")
            if not key or key in seen:
                continue
            seen.add(key)
            definition = (term.get("definition") or "").strip()
            truncated = len(definition) > PHENOTYPE_DEFINITION_CHARACTERS
            if truncated:
                definition = (
                    definition[:PHENOTYPE_DEFINITION_CHARACTERS].rstrip() + "..."
                )
            out.append(
                {
                    "curie": curie,
                    "name": term.get("name"),
                    "definition": definition or None,
                    "definition_truncated": truncated,
                    "descendant_count": term.get("descendantCount"),
                }
            )
            if len(out) >= PHENOTYPE_TERMS_PER_ROW:
                return out
    return out


def _evidence_codes(annotations: list) -> list:
    """Evidence codes as the identifiers they are cited by.

    Alliance sends `{"curie": "ECO:0000270", "name": "expression pattern
    evidence used in manual assertion", "abbreviation": "IEP"}` and the row
    kept only the name. IEP is what a paper writes and ECO:0000270 is what a
    machine reads; neither reached the caller.
    """
    out, seen = [], set()
    for annotation in annotations:
        for term in annotation.get("evidenceCodes") or []:
            if not isinstance(term, dict):
                continue
            curie = term.get("curie")
            key = curie or term.get("abbreviation") or term.get("name")
            if not key or key in seen:
                continue
            seen.add(key)
            out.append(
                {
                    "curie": curie,
                    "abbreviation": term.get("abbreviation"),
                    "name": term.get("name"),
                }
            )
    return out


def _expression_pattern(pattern: Any) -> dict:
    """The structured terms behind an expression annotation's two strings.

    `whereExpressed.anatomicalStructure` carries the SPECIES-specific
    ontology curie -- ZFA:0001162 for "anal fin" -- which is not among the
    UBERON slim ids in `termIds`, and `whenExpressed.stageUberonSlimTerms`
    carries the stage terms. The whole nested object is not returned: it
    repeats the strings the row already has and nests four levels deep.
    """
    if not isinstance(pattern, dict):
        return {
            "anatomical_structure": None,
            "anatomical_structure_curie": None,
            "stage_terms": [],
        }
    where = pattern.get("whereExpressed") or {}
    structure = (
        (where.get("anatomicalStructure") or {}) if isinstance(where, dict) else {}
    )
    when = pattern.get("whenExpressed") or {}
    stages = []
    if isinstance(when, dict):
        for term in when.get("stageUberonSlimTerms") or []:
            if isinstance(term, dict) and term.get("name"):
                stages.append(term["name"])
    return {
        "anatomical_structure": structure.get("name")
        if isinstance(structure, dict)
        else None,
        "anatomical_structure_curie": structure.get("curie")
        if isinstance(structure, dict)
        else None,
        "stage_terms": stages,
    }


def _cross_references(block: dict) -> list:
    """An annotation's source records, with the URL its template builds.

    ZFIN's expression annotations cite the FIGURE the call was made from --
    ZFIN:ZDB-FIG-140307-27 -- and carry the resolver template beside it, so
    the link is mechanical rather than guessed.
    """
    out = []
    for xref in block.get("crossReferences") or []:
        if not isinstance(xref, dict):
            continue
        curie = xref.get("referencedCurie")
        template = ((xref.get("resourceDescriptorPage") or {}).get("urlTemplate")) or ""
        url = None
        if curie and "[%s]" in template:
            url = template.replace("[%s]", curie.split(":", 1)[-1])
        out.append(
            {
                "curie": curie,
                "display_name": xref.get("displayName"),
                "url": url,
            }
        )
    return out


def _annotation_facet(annotations: list, path: tuple) -> list:
    """A de-duplicated facet across a row's annotations, nulls dropped."""
    out = []
    for annotation in annotations:
        value = annotation
        for key in path:
            value = (value or {}).get(key) if isinstance(value, dict) else None
        if value and value not in out:
            out.append(value)
    return out


RELATED_TERMS_PER_DISEASE = 100


def _xrefs(rows):
    """Cross-references to other vocabularies, with the URL where there is one.

    SNOMEDCT comes without a url while MESH, UMLS and ICD9CM carry one, so
    the url is optional and the curie is not.
    """
    out = []
    for row in rows or []:
        if not isinstance(row, dict) or not row.get("referencedCurie"):
            continue
        curie = row["referencedCurie"]
        out.append(
            {
                "curie": curie,
                "prefix": curie.split(":")[0] if ":" in curie else None,
                "url": row.get("url"),
            }
        )
    return out


def _related_terms(rows):
    """A parent or child term: enough to decide whether to follow it."""
    out = []
    for row in (rows or [])[:RELATED_TERMS_PER_DISEASE]:
        if not isinstance(row, dict):
            continue
        out.append(
            {
                "disease_id": row.get("curie"),
                "name": row.get("name"),
                "definition": row.get("definition"),
                "descendant_count": row.get("descendantCount"),
            }
        )
    return out


@register_tool("AllianceGenomeTool")
class AllianceGenomeTool(BaseTool):
    """
    Tool for querying the Alliance of Genome Resources API.

    Provides cross-species gene information across 7 model organisms
    (yeast, fly, worm, zebrafish, rat, mouse, frog) plus human.
    Supports gene detail, disease associations, phenotypes, and search.

    No authentication required.
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout = tool_config.get("timeout", 30)
        self.endpoint_type = tool_config.get("fields", {}).get(
            "endpoint_type", "gene_detail"
        )

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the Alliance of Genome Resources API call."""
        try:
            return self._query(arguments)
        except requests.exceptions.Timeout:
            return {
                "status": "error",
                "error": f"Alliance API request timed out after {self.timeout}s",
            }
        except requests.exceptions.ConnectionError:
            return {
                "status": "error",
                "error": "Failed to connect to Alliance API. Check network connectivity.",
            }
        except requests.exceptions.HTTPError as e:
            return {
                "status": "error",
                "error": f"Alliance API HTTP error: {e.response.status_code}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error querying Alliance API: {str(e)}",
            }

    def _query(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Route to the appropriate Alliance endpoint."""
        endpoint_type = self.endpoint_type

        if endpoint_type == "gene_detail":
            return self._get_gene_detail(arguments)
        elif endpoint_type == "search_genes":
            return self._search_genes(arguments)
        elif endpoint_type == "gene_phenotypes":
            return self._get_gene_phenotypes(arguments)
        elif endpoint_type == "disease_genes":
            return self._get_disease_genes(arguments)
        elif endpoint_type == "disease_detail":
            return self._get_disease_detail(arguments)
        elif endpoint_type == "gene_orthologs":
            return self._get_gene_orthologs(arguments)
        elif endpoint_type == "gene_alleles":
            return self._get_gene_alleles(arguments)
        elif endpoint_type == "gene_expression_summary":
            return self._get_gene_expression_summary(arguments)
        elif endpoint_type == "gene_interactions":
            return self._get_gene_interactions(arguments)
        elif endpoint_type == "gene_disease_models":
            return self._get_gene_disease_models(arguments)
        elif endpoint_type == "gene_orthologs_paralogs":
            return self._get_gene_orthologs_paralogs(arguments)
        elif endpoint_type == "gene_molecular_interactions":
            return self._get_gene_molecular_interactions(arguments)
        elif endpoint_type == "gene_alleles_and_models":
            return self._get_gene_alleles_and_models(arguments)
        elif endpoint_type == "allele_detail":
            return self._get_allele_detail(arguments)
        elif endpoint_type == "zfin_search":
            return self._search_genes_by_species(
                arguments, species_prefix="ZFIN:", species_name="Danio rerio"
            )
        elif endpoint_type == "mgi_search":
            return self._search_genes_by_species(
                arguments, species_prefix="MGI:", species_name="Mus musculus"
            )
        elif endpoint_type == "flybase_search":
            return self._search_genes_by_species(
                arguments, species_prefix="FB:", species_name="Drosophila melanogaster"
            )
        elif endpoint_type == "wormbase_search":
            return self._search_genes_by_species(
                arguments, species_prefix="WB:", species_name="Caenorhabditis elegans"
            )
        else:
            return {
                "status": "error",
                "error": f"Unknown endpoint type: {endpoint_type}",
            }

    @staticmethod
    def _page_parameters(arguments: Dict[str, Any]) -> tuple[int, int]:
        """Validate the Alliance API's one-based page pagination."""
        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 100
        ):
            raise ValueError("limit must be an integer from 1 to 100")
        if isinstance(page, bool) or not isinstance(page, int) or page < 1:
            raise ValueError("page must be a positive integer")
        return limit, page

    @staticmethod
    def _page_metadata(
        total: int, returned: int, limit: int, page: int
    ) -> Dict[str, Any]:
        total_pages = (total + limit - 1) // limit if total else 0
        has_more = page < total_pages
        return {
            "total_results": total,
            "returned": returned,
            "limit": limit,
            "page": page,
            "total_pages": total_pages,
            "has_more": has_more,
            "next_page": page + 1 if has_more else None,
            "result_set_complete": page == 1 and returned == total,
        }

    @staticmethod
    def _normalize_gene_id(gene_id: str) -> str:
        """Auto-add required namespace prefix if missing."""
        if not gene_id:
            return gene_id
        # Already has a known prefix
        for prefix in (
            "FB:",
            "ZFIN:",
            "MGI:",
            "WB:",
            "RGD:",
            "SGD:",
            "HGNC:",
            "Xenbase:",
        ):
            if gene_id.startswith(prefix):
                return gene_id
        # FlyBase bare IDs (FBgn, FBtr, FBpp, FBgn...)
        if (
            gene_id.startswith("FBgn")
            or gene_id.startswith("FBtr")
            or gene_id.startswith("FBpp")
        ):
            return f"FB:{gene_id}"
        # ZFIN bare IDs (ZDB-GENE-...)
        if gene_id.startswith("ZDB-"):
            return f"ZFIN:{gene_id}"
        # WormBase bare IDs (WBGene...)
        if gene_id.startswith("WBGene"):
            return f"WB:{gene_id}"
        # MGI bare numeric IDs (e.g. "98834")
        if gene_id.isdigit() and len(gene_id) >= 5:
            return f"MGI:{gene_id}"
        return gene_id

    def _get_gene_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed gene information from Alliance."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {
                "status": "error",
                "error": "gene_id parameter is required (e.g., 'HGNC:6081', 'MGI:98834', 'FB:FBgn0003996')",
            }

        url = f"{ALLIANCE_BASE}/gene/{gene_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        payload = response.json()

        # The Alliance API nests the gene record under a top-level "gene" key.
        # Fall back to the payload itself for resilience against schema drift.
        data = payload.get("gene") or payload

        def _text(obj):
            """Alliance wraps labels as {formatText, displayText}; unwrap them."""
            if isinstance(obj, dict):
                return obj.get("displayText") or obj.get("formatText")
            return obj

        taxon = data.get("taxon") or {}
        taxon_species = taxon.get("species") or {}
        # genomic location moved to geneGenomicLocationAssociations
        locations = (
            data.get("geneGenomicLocationAssociations")
            or data.get("genomeLocations")
            or []
        )
        loc_info = locations[0] if locations else {}

        synonyms = [
            _text(s) for s in (data.get("geneSynonyms") or data.get("synonyms") or [])
        ]

        # cross-references: new schema is a flat list of {referencedCurie, displayName}
        cross_refs = data.get("crossReferences")
        if cross_refs is None:
            cross_refs = (data.get("crossReferenceMap") or {}).get("other", [])
        xref_offset = max(int(arguments.get("xref_offset") or 0), 0)
        xref_limit = min(max(int(arguments.get("xref_limit") or 10), 1), 500)
        xref_page = cross_refs[xref_offset : xref_offset + xref_limit]
        xref_list = [
            {
                "name": x.get("displayName") or x.get("name"),
                "curie": x.get("referencedCurie"),
                "url": x.get("crossRefCompleteUrl"),
            }
            for x in xref_page
        ]
        xrefs_truncated = xref_offset + len(xref_page) < len(cross_refs)

        gene_type = data.get("geneType") or data.get("soTerm") or {}

        # The literature about the gene. Alliance answers `referenceCuries` as
        # a flat list of publication curies -- 2,172 for FlyBase dpp, 4,461 for
        # the MGI record -- and none of them reached the caller, so a gene
        # detail carried no way to read anything about the gene. Capped and
        # disclosed the way the cross-references beside it already are,
        # because the full list would otherwise be the whole response.
        reference_curies = data.get("referenceCuries") or []
        ref_page = reference_curies[:REFERENCE_CURIE_CAP]
        # Curator notes, which on a FlyBase gene are 102 free-text statements
        # the model-organism database wrote about it.
        notes = [
            {
                "note_type": (note.get("noteType") or {}).get("name"),
                "text": note.get("freeText"),
            }
            for note in (data.get("relatedNotes") or [])
            if isinstance(note, dict)
        ]
        # Retired accessions. A gene renamed or merged is cited in the older
        # literature under the secondary id, and nothing else recovers it.
        secondary_ids = [
            sid.get("secondaryId")
            for sid in (data.get("geneSecondaryIds") or [])
            if isinstance(sid, dict) and sid.get("secondaryId")
        ]

        return {
            "status": "success",
            "data": {
                "id": data.get("primaryExternalId") or data.get("id"),
                "secondary_ids": secondary_ids,
                "symbol": _text(data.get("geneSymbol")) or data.get("symbol"),
                "name": _text(data.get("geneFullName")) or data.get("name"),
                "species": {
                    "name": taxon.get("name") or taxon_species.get("fullName"),
                    "short_name": taxon_species.get("displayName")
                    or taxon_species.get("abbreviation"),
                    "taxon_id": taxon.get("curie") or taxon.get("taxonId"),
                    "data_provider": (data.get("dataProvider") or {}).get(
                        "abbreviation"
                    )
                    if isinstance(data.get("dataProvider"), dict)
                    else data.get("dataProvider"),
                },
                "gene_synopsis": data.get("geneSynopsis"),
                "automated_gene_synopsis": data.get("automatedGeneSynopsis"),
                "synonyms": synonyms,
                "so_term": gene_type.get("name"),
                "genomic_location": {
                    "chromosome": loc_info.get("chromosome"),
                    "start": loc_info.get("start"),
                    "end": loc_info.get("end"),
                    "assembly": loc_info.get("assembly"),
                    "strand": loc_info.get("strand"),
                },
                "cross_references": xref_list,
                "cross_references_total": len(cross_refs),
                "xref_offset": xref_offset,
                "cross_references_returned": len(xref_page),
                "cross_references_truncated": xrefs_truncated,
                "next_xref_offset": (
                    xref_offset + len(xref_page) if xrefs_truncated else None
                ),
                "notes": notes,
                "reference_curies": ref_page,
                "reference_curies_total": len(reference_curies),
                "reference_curies_returned": len(ref_page),
                "reference_curies_truncated": len(ref_page) < len(reference_curies),
            },
            "metadata": {
                "query_gene_id": gene_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _search_genes(
        self,
        arguments: Dict[str, Any],
        species_prefix: str = "",
        species_name: str = "",
    ) -> Dict[str, Any]:
        """Search genes via Alliance autocomplete, optionally filtered to one species."""
        query = arguments.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        limit = arguments.get("limit", 10)
        offset = arguments.get("offset", 0)
        if (
            isinstance(limit, bool)
            or not isinstance(limit, int)
            or not 1 <= limit <= 50
        ):
            return {
                "status": "error",
                "error": "limit must be an integer from 1 to 50",
            }
        if isinstance(offset, bool) or not isinstance(offset, int) or offset < 0:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        # Autocomplete ignores limit/offset and always returns ten mixed hits.
        # Full search exposes exact totals and real offset pagination.
        params: Dict[str, Any] = {
            "q": query,
            "category": "gene_search_result",
            "limit": limit,
            "offset": offset,
        }
        if species_name:
            params["species"] = species_name

        response = requests.get(
            f"{ALLIANCE_BASE}/search",
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        raw_results = payload.get("results", [])

        # Keep only gene hits (autocomplete also returns diseases, GO terms,
        # datasets, …).
        gene_results = [
            r for r in raw_results if r.get("category") == "gene_search_result"
        ]

        if species_prefix and not species_name:
            gene_results = [
                r
                for r in gene_results
                if str(r.get("curie", "")).startswith(species_prefix)
            ]

        genes = [
            {
                "symbol": r.get("symbol"),
                "name": r.get("name"),
                "gene_id": r.get("curie"),
                "category": "gene",
                "species": r.get("species"),
                # What the hit is known for. A gene search returned symbol,
                # name and species while the same rows carried 141 disease
                # names and Alliance's own one-line description of the gene --
                # the two things that let a caller pick among hits without a
                # follow-up call each.
                "diseases": [
                    d for d in (r.get("diseases") or []) if isinstance(d, str)
                ],
                "automated_description": r.get("automatedGeneDescription"),
                "synonyms": [
                    x for x in (r.get("synonyms") or []) if isinstance(x, str)
                ],
                "gene_synopsis": r.get("geneSynopsis"),
                # The order the hits come back in, and what the hit is.
                "search_score": r.get("score"),
                "so_term": r.get("soTermName"),
                # How much of each kind of evidence the gene has, which is how
                # a caller picks a hit worth following up without a call each.
                "related_data_counts": {
                    item["targetField"]: item.get("count")
                    for item in (r.get("relatedData") or [])
                    if isinstance(item, dict) and item.get("targetField")
                },
            }
            for r in gene_results
        ]

        total_results = payload.get("total")
        if not isinstance(total_results, int):
            total_results = len(genes)
        next_offset = offset + len(genes)
        has_more = next_offset < total_results

        metadata: Dict[str, Any] = {
            "total_results": total_results,
            "returned": len(genes),
            "offset": offset,
            "limit": limit,
            "has_more": has_more,
            "next_offset": next_offset if has_more else None,
            "result_set_complete": offset == 0 and len(genes) == total_results,
            "query": query,
            "source": "Alliance of Genome Resources",
        }
        if species_name:
            metadata["species"] = species_name

        # Preserve an actionable note for legacy/mocked mixed-category payloads.
        if not genes and raw_results:
            other = sorted(
                {
                    str(r.get("category", "")).replace("_search_result", "")
                    for r in raw_results
                }
            )
            metadata["note"] = (
                f"No gene matched '{query}'. The Alliance response instead "
                f"matched: {', '.join(c for c in other if c)}. Try the official gene "
                "symbol (e.g. 'INS' for insulin)."
            )
        elif not genes and total_results == 0:
            metadata["note"] = (
                f"No Alliance gene matched '{query}'. Try an official gene symbol, "
                "synonym, or a less restrictive term."
            )

        return {"status": "success", "data": genes, "metadata": metadata}

    def _search_genes_by_species(
        self, arguments: Dict[str, Any], species_prefix: str, species_name: str
    ) -> Dict[str, Any]:
        return self._search_genes(
            arguments, species_prefix=species_prefix, species_name=species_name
        )

    def _get_gene_phenotypes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get phenotype annotations for a gene."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit, page = self._page_parameters(arguments)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/phenotypes"
        params = {"limit": limit, "page": page}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        phenotypes = []
        for r in results:
            subject = r.get("subject", {})
            # subject.geneSymbol is now a {formatText, displayText} object, not
            # a plain `symbol` string — unwrap it (was returning null).
            gene_symbol_obj = subject.get("geneSymbol")
            gene_symbol = (
                gene_symbol_obj.get("displayText") or gene_symbol_obj.get("formatText")
                if isinstance(gene_symbol_obj, dict)
                else subject.get("symbol")
            )
            annotations = [
                a for a in (r.get("primaryAnnotations") or []) if isinstance(a, dict)
            ]
            phenotypes.append(
                {
                    "gene_symbol": gene_symbol,
                    "gene_id": subject.get("primaryExternalId"),
                    "phenotype_statement": _strip_html(r.get("phenotypeStatement")),
                    # A phenotype statement with no citation cannot be
                    # checked, and the response carries one per annotation:
                    # 168 reference cross-references on the ZFIN record alone.
                    "references": _alliance_references(r.get("references")),
                    # Which allele the phenotype was observed in, and under
                    # what conditions. "standard conditions" versus a chemical
                    # or temperature treatment changes what the statement
                    # means.
                    "inferred_allele": _display(
                        (annotations[0].get("inferredAllele") or {}).get("alleleSymbol")
                    )
                    if annotations
                    else None,
                    "inferred_allele_synonyms": sorted(
                        {
                            _display(syn)
                            for annotation in annotations
                            for syn in (
                                (annotation.get("inferredAllele") or {}).get(
                                    "alleleSynonyms"
                                )
                                or []
                            )
                            if _display(syn)
                        }
                    ),
                    "conditions": sorted(
                        {
                            cond.get("conditionSummary")
                            for annotation in annotations
                            for relation in (annotation.get("conditionRelations") or [])
                            if isinstance(relation, dict)
                            for cond in (relation.get("conditions") or [])
                            if isinstance(cond, dict) and cond.get("conditionSummary")
                        }
                    ),
                    "pubmed_publications": [
                        pub.get("curie") or pub.get("referenceID")
                        for pub in (r.get("pubmedPublications") or [])
                        if isinstance(pub, dict)
                    ],
                    # The ontology term the statement paraphrases, and its id.
                    "phenotype_terms": _phenotype_terms(annotations),
                    # The row's own relation is "is_implicated_in" while each
                    # annotation's is "has_phenotype"; they are different
                    # claims and both were dropped.
                    "relation": (r.get("relation") or {}).get("name"),
                    "annotation_relations": _annotation_facet(
                        annotations, ("relation", "name")
                    ),
                    # Which Alliance member asserted it. The Alliance
                    # aggregates several, and the row did not say which.
                    "data_providers": _annotation_facet(
                        annotations, ("dataProvider", "abbreviation")
                    ),
                    "annotation_types": _annotation_facet(annotations, ("type",)),
                    # The genotype or model the phenotype was seen in, which
                    # is not the queried gene: MGI:2170872 against MGI:97490.
                    "annotation_subjects": _annotation_facet(
                        annotations, ("phenotypeAnnotationSubject", "primaryExternalId")
                    ),
                    "annotation_count": len(annotations),
                }
            )

        return {
            "status": "success",
            "data": phenotypes,
            "metadata": {
                **self._page_metadata(total, len(phenotypes), limit, page),
                "query_gene_id": gene_id,
                "source": "Alliance of Genome Resources",
                "phenotype_terms_per_row": PHENOTYPE_TERMS_PER_ROW,
            },
        }

    def _get_disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get genes associated with a disease by Disease Ontology ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., 'DOID:162' for cancer)",
            }

        limit, page = self._page_parameters(arguments)
        url = f"{ALLIANCE_BASE}/disease/{disease_id}/genes"
        params = {"limit": limit, "page": page}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        genes = []
        for r in results:
            subject = r.get("subject", {})
            species = subject.get("taxon", {})
            disease_obj = r.get("object", {})
            genes.append(
                {
                    "gene_symbol": subject.get("symbol")
                    or subject.get("geneSymbol", {}).get("displayText"),
                    "gene_id": subject.get("primaryExternalId") or subject.get("curie"),
                    "species": species.get("curie"),
                    "disease_name": disease_obj.get("name"),
                    "disease_id": disease_obj.get("curie"),
                    "association_type": r.get("associationType"),
                    # The papers behind the association, and the evidence codes
                    # Alliance assigned. 38 reference cross-references on the
                    # first page alone, and a gene-disease link with neither is
                    # not usable as evidence.
                    "references": _alliance_references(r.get("references")),
                    "evidence_codes": sorted(
                        {
                            code
                            for annotation in (r.get("primaryAnnotations") or [])
                            if isinstance(annotation, dict)
                            for code in (
                                _display(term)
                                for term in (annotation.get("evidenceCodes") or [])
                            )
                            if code
                        }
                    ),
                    # The same codes as the identifiers the field is normally
                    # cited by: IAGP, IEP, IMP, and the ECO curie behind each.
                    # The row carried only the long prose name.
                    "evidence_code_details": _evidence_codes(
                        [
                            a
                            for a in (r.get("primaryAnnotations") or [])
                            if isinstance(a, dict)
                        ]
                    ),
                    # "is_implicated_in" against "is_marker_for" -- 35 and 23
                    # on one page of DOID:162 -- are different claims about a
                    # gene-disease link, and neither was reported.
                    "annotation_relations": _annotation_facet(
                        [
                            a
                            for a in (r.get("primaryAnnotations") or [])
                            if isinstance(a, dict)
                        ],
                        ("relation", "name"),
                    ),
                    "data_providers": _annotation_facet(
                        [
                            a
                            for a in (r.get("primaryAnnotations") or [])
                            if isinstance(a, dict)
                        ],
                        ("dataProvider", "abbreviation"),
                    ),
                    # A NOT annotation: the gene is curated as NOT associated.
                    # None of the 58 annotations measured on DOID:162 is
                    # negated, so this is latent here -- but the same field on
                    # GO associations was returning genes curated against the
                    # function they were listed under.
                    "negated_annotations": sum(
                        1
                        for a in (r.get("primaryAnnotations") or [])
                        if isinstance(a, dict) and a.get("negated")
                    ),
                }
            )

        return {
            "status": "success",
            "data": genes,
            "metadata": {
                **self._page_metadata(total, len(genes), limit, page),
                "query_disease_id": disease_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_disease_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get disease summary information by Disease Ontology ID."""
        disease_id = arguments.get("disease_id", "")
        if not disease_id:
            return {
                "status": "error",
                "error": "disease_id parameter is required (e.g., 'DOID:162' for cancer)",
            }

        url = f"{ALLIANCE_BASE}/disease/{disease_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        do_term = data.get("doTerm", {})
        synonyms = do_term.get("synonyms", [])
        synonym_names = [s.get("name") for s in synonyms if s.get("name")]

        return {
            "status": "success",
            "data": {
                "disease_id": do_term.get("curie"),
                "name": do_term.get("name"),
                "definition": do_term.get("definition"),
                "synonyms": synonym_names,
                "category": data.get("category"),
                # Everything below sits at the top level of the response, not
                # inside doTerm, which is why reading doTerm alone returned a
                # disease ontology term with no mappings and no hierarchy.
                #
                # The cross-references are how a disease term joins anything
                # else: DOID:162 is MESH:D009369, UMLS_CUI:C0006826,
                # ICD9CM:199 and SNOMEDCT 269513004, each with a resolvable
                # URL where the API has one.
                "cross_references": _xrefs(data.get("crossReferenceLinkUrls")),
                # Where each model-organism database records its annotations
                # for this disease -- RGD, MGI, ZFIN, FlyBase. In a tool whose
                # subject is the Alliance of Genome Resources, this is the
                # point of the record.
                "source_links": [
                    {"source": r.get("source"), "url": r.get("url")}
                    for r in (data.get("sourceReferenceLinkUrls") or [])
                    if isinstance(r, dict)
                ],
                "parents": _related_terms(data.get("parents")),
                "children": _related_terms(data.get("children")),
                "ancestor_ids": data.get("parentClosureIDs") or [],
                "descendant_count": do_term.get("descendantCount"),
                # Which curated slims the term belongs to, e.g. DO_cancer_slim.
                "subsets": do_term.get("subsets") or [],
                "definition_urls": do_term.get("definitionUrls") or [],
                "url": data.get("diseaseURL"),
            },
            "metadata": {
                "query_disease_id": disease_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_orthologs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get ortholog genes across species for a given gene."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        stringency = arguments.get("stringency", "stringent")
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/orthologs"
        params = {
            "limit": min(int(limit), 100),
            "page": int(page),
            "filter.stringency": stringency,
        }

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        orthologs = []
        for r in results:
            # /orthologs answers two kinds of row and the handler read one.
            # `category` says which: "gene_to_gene_orthology" carries the
            # relationship under `geneToGeneOrthologyGenerated`, and a
            # paralogy row carries it under `geneToGeneParalogy`. Reading
            # only the first meant a paralogy row became a row of nulls --
            # subject_gene_id None, ortholog_symbol None, methods [] -- and
            # was still listed as an ortholog. Rows with neither branch are
            # skipped rather than emitted blank.
            orth = r.get("geneToGeneOrthologyGenerated") or {}
            paralogy = r.get("geneToGeneParalogy") or {}
            relationship = r.get("category")
            if not orth and paralogy:
                orth = paralogy
            if not orth:
                continue
            subject = orth.get("subjectGene", {})
            obj_gene = orth.get("objectGene", {})
            methods = orth.get("predictionMethodsMatched", [])
            orthologs.append(
                {
                    "relationship": relationship,
                    "is_paralogy": bool(paralogy)
                    and not r.get("geneToGeneOrthologyGenerated"),
                    # Present on a paralogy row, which reports sequence
                    # similarity rather than prediction methods.
                    "similarity": paralogy.get("similarity") if paralogy else None,
                    "identity": paralogy.get("identity") if paralogy else None,
                    "alignment_length": paralogy.get("length") if paralogy else None,
                    "subject_gene_id": subject.get("primaryExternalId"),
                    "subject_symbol": subject.get("geneSymbol", {}).get("displayText"),
                    "subject_species": subject.get("taxon", {}).get("name"),
                    "ortholog_gene_id": obj_gene.get("primaryExternalId"),
                    "ortholog_symbol": obj_gene.get("geneSymbol", {}).get(
                        "displayText"
                    ),
                    "ortholog_species": obj_gene.get("taxon", {}).get("name"),
                    "is_best_score": orth.get("isBestScore", {}).get("name"),
                    "is_best_score_reverse": orth.get("isBestScoreReverse", {}).get(
                        "name"
                    ),
                    "methods": [m.get("name") for m in methods],
                    "method_count": len(methods),
                    "methods_not_matched": [
                        m.get("name")
                        for m in (orth.get("predictionMethodsNotMatched") or [])
                        if isinstance(m, dict) and m.get("name")
                    ],
                    # Which stringency band this row satisfies. The parameter
                    # asks for a stringency and the answer never said what each
                    # row met, so a "stringent" and a "moderate" call returned
                    # rows that looked identical.
                    "stringency": r.get("stringencyFilter"),
                    "subject_taxon_id": (subject.get("taxon") or {}).get("curie"),
                    "ortholog_taxon_id": (obj_gene.get("taxon") or {}).get("curie"),
                    "confidence": _display(orth.get("confidence")),
                }
            )

        return {
            "status": "success",
            "data": orthologs,
            "metadata": {
                "total_results": total,
                "returned": len(orthologs),
                "query_gene_id": gene_id,
                "stringency": stringency,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_alleles(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get alleles and variants for a gene."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/alleles"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        alleles = [_allele_summary(r) for r in results]

        return {
            "status": "success",
            "data": alleles,
            "metadata": {
                "total_results": total,
                "returned": len(alleles),
                "query_gene_id": gene_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_expression_summary(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get expression annotations for a gene.

        Alliance retired the per-gene ``/gene/{id}/expression-summary`` ribbon
        endpoint (now 404). Expression is served from ``POST /api/expression``
        with a bare JSON array of gene curies; it returns per-annotation records
        (developmental stage + anatomical location).
        """
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        try:
            limit = int(arguments.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 100))
        try:
            page = max(1, int(arguments.get("page", 1)))
        except (TypeError, ValueError):
            page = 1

        url = f"{ALLIANCE_BASE}/expression"
        response = requests.post(
            url,
            json=[gene_id],
            params={"limit": limit, "page": page},
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        results = data.get("results", []) or []
        annotations = []
        for r in results:
            ann = r.get("geneExpressionAnnotation", r) if isinstance(r, dict) else {}
            provider = ann.get("dataProvider") or {}
            evidence = ann.get("evidenceItem") or {}
            assay = ann.get("expressionAssayUsed") or {}
            term_ids = [t for t in (r.get("termIds") or []) if t]
            uberon_term_ids = [t for t in (r.get("uberonTermIds") or []) if t]
            annotations.append(
                {
                    "stage": ann.get("whenExpressedStageName"),
                    "location": ann.get("whereExpressedStatement"),
                    # The ontology ids behind those two strings. "anal fin"
                    # cannot be joined to an anatomy ontology; UBERON:0000026
                    # can. The stage term travels in the same list.
                    "term_ids": term_ids,
                    "uberon_term_ids": uberon_term_ids,
                    # HOW the call was made. "RNA in situ" (MMO:0000658) is a
                    # different weight of evidence from a sequencing assay,
                    # and the row said neither.
                    "assay": assay.get("name") if isinstance(assay, dict) else None,
                    "assay_curie": (
                        assay.get("curie") if isinstance(assay, dict) else None
                    ),
                    # The species-specific anatomy term, which is NOT in
                    # termIds: those are the UBERON slim ids, and
                    # expressionPattern carries ZFA:0001162 for "anal fin".
                    **_expression_pattern(ann.get("expressionPattern")),
                    "data_provider": provider.get("abbreviation")
                    if isinstance(provider, dict)
                    else provider,
                    "reference": evidence.get("curie")
                    if isinstance(evidence, dict)
                    else None,
                    # The figure the annotation was read off.
                    "cross_references": _cross_references(ann),
                    "category": r.get("category") if isinstance(r, dict) else None,
                }
            )

        total = data.get("total", len(annotations))
        total_pages = (total + limit - 1) // limit if total else 0
        has_more = page < total_pages
        return {
            "status": "success",
            "data": {
                "total_annotations": total,
                "returned": len(annotations),
                "limit": limit,
                "page": page,
                "total_pages": total_pages,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "result_set_complete": page == 1 and len(annotations) == total,
                "annotations": annotations,
            },
            "metadata": {
                "query_gene_id": gene_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_interactions(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get molecular or genetic interactions for a gene."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        interaction_type = arguments.get("interaction_type", "molecular")
        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)

        if interaction_type == "genetic":
            url = f"{ALLIANCE_BASE}/gene/{gene_id}/genetic-interactions"
        else:
            url = f"{ALLIANCE_BASE}/gene/{gene_id}/molecular-interactions"

        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        interactions = []
        for r in results:
            if interaction_type == "genetic":
                gi = r.get("geneGeneticInteraction", {})
                subject = gi.get("geneAssociationSubject", {})
                obj = gi.get("geneGeneAssociationObject", {})
                int_type = gi.get("interactionType", {}).get("name")
            else:
                gi = r.get("geneMolecularInteraction", {})
                subject = gi.get("geneAssociationSubject", {})
                obj = gi.get("geneGeneAssociationObject", {})
                int_type = (
                    gi.get("interactionType", {}).get("name")
                    if gi.get("interactionType")
                    else None
                )

            interactions.append(
                {
                    "subject_gene_id": subject.get("primaryExternalId"),
                    "subject_symbol": subject.get("geneSymbol", {}).get("displayText"),
                    "interactor_gene_id": obj.get("primaryExternalId") if obj else None,
                    "interactor_symbol": obj.get("geneSymbol", {}).get("displayText")
                    if obj
                    else None,
                    "interactor_species": obj.get("taxon", {}).get("name")
                    if obj
                    else None,
                    "interaction_type": int_type,
                    "relation": (gi.get("relation") or {}).get("name"),
                    # Which gene plays which part. Alliance answers
                    # interactorARole "suppressed gene" and interactorBRole
                    # "suppressor gene"; without them "genetic suppression"
                    # names a pair but not a direction, and direction is the
                    # whole content of a suppression or enhancement result.
                    "subject_role": _mi_term(gi.get("interactorARole")),
                    "interactor_role": _mi_term(gi.get("interactorBRole")),
                    "subject_type": _mi_term(gi.get("interactorAType")),
                    "interactor_type": _mi_term(gi.get("interactorBType")),
                    # Which database asserted it, and the paper behind it. An
                    # interaction with no reference cannot be cited or checked.
                    "interaction_source": _mi_term(gi.get("interactionSource")),
                    "references": _alliance_references(gi.get("evidence")),
                }
            )

        return {
            "status": "success",
            "data": interactions,
            "metadata": {
                "total_results": total,
                "returned": len(interactions),
                "query_gene_id": gene_id,
                "interaction_type": interaction_type,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_disease_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get disease models involving a gene."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = arguments.get("limit", 20)
        page = arguments.get("page", 1)
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/models"
        params = {"limit": min(int(limit), 100), "page": int(page)}

        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        data = response.json()

        total = data.get("total", 0)
        results = data.get("results", [])
        models = []
        for r in results:
            model = r.get("model", {})
            gene = r.get("gene", {})
            disease_models = r.get("diseaseModels", [])
            diseases = []
            for dm in disease_models:
                # Alliance nests the disease under two keys and fills only
                # one. On every one of the 25 dpp model rows measured, the
                # `disease` object is EMPTY and the name is in `diseaseModel`:
                #     {"disease": {}, "associationType": "IS_MODEL_OF",
                #      "diseaseModel": "amyotrophic lateral sclerosis type 15"}
                # Reading `disease.name` alone returned null for the one thing
                # this tool's description promises, on a row that otherwise
                # looked complete.
                disease = dm.get("disease") or {}
                diseases.append(
                    {
                        "disease_name": disease.get("name") or dm.get("diseaseModel"),
                        "disease_id": disease.get("curie"),
                        "association_type": dm.get("associationType"),
                    }
                )
            models.append(
                {
                    "model_id": model.get("primaryExternalId"),
                    "model_name": model.get("agmFullName", {}).get("displayText")
                    if isinstance(model.get("agmFullName"), dict)
                    else model.get("name"),
                    "gene_symbol": gene.get("geneSymbol", {}).get("displayText"),
                    "gene_id": gene.get("primaryExternalId"),
                    "data_provider": r.get("dataProvider"),
                    "diseases": diseases,
                    # In which directions the model's phenotype is modified by
                    # other alleles. Both 'ameliorated_by' and
                    # 'exacerbated_by' are present on all 25 measured rows,
                    # and they are what a modifier screen on the model looks
                    # for.
                    "modifier_relationship_types": r.get("modifierRelationshipTypes"),
                    # Whether the model carries disease annotations, phenotype
                    # annotations, or both. A model with no disease annotation
                    # is in this list for its phenotype alone.
                    "has_disease_annotations": r.get("hasDiseaseAnnotations"),
                    "has_phenotype_annotations": r.get("hasPhenotypeAnnotations"),
                }
            )

        return {
            "status": "success",
            "data": models,
            "metadata": {
                "total_results": total,
                "returned": len(models),
                "query_gene_id": gene_id,
                "page": int(page),
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_allele_detail(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific allele."""
        allele_id = arguments.get("allele_id", "")
        if not allele_id:
            return {"status": "error", "error": "allele_id parameter is required"}

        url = f"{ALLIANCE_BASE}/allele/{allele_id}"
        response = requests.get(
            url, headers={"Accept": "application/json"}, timeout=self.timeout
        )
        response.raise_for_status()
        data = response.json()

        allele = data.get("allele", {})
        allele_of_gene = data.get("alleleOfGene", {})
        synonyms = allele.get("alleleSynonyms", [])
        synonym_list = [s.get("displayText") for s in synonyms if s.get("displayText")]

        return {
            "status": "success",
            "data": {
                "id": allele.get("primaryExternalId"),
                "symbol": allele.get("alleleSymbol", {}).get("displayText"),
                "species": allele.get("taxon", {}).get("name"),
                "alteration_type": data.get("alterationType"),
                "gene_id": allele_of_gene.get("primaryExternalId"),
                "gene_symbol": allele_of_gene.get("geneSymbol", {}).get("displayText"),
                "synonyms": synonym_list,
                "has_phenotype": data.get("hasPhenotype"),
                "has_disease": data.get("hasDisease"),
                # What the allele actually does. An allele detail returned the
                # allele's name, species and gene and nothing about the
                # variant: no HGVS, no VEP impact, no transcript. For
                # ZFIN:ZDB-ALT-980203-1091 the response carries
                # "XM_073919248.1:c.396+1G>A", vepImpact HIGH and
                # splice_donor_variant, which is the whole content of the
                # record.
                "variants": _allele_variants(data.get("variantList")),
            },
            "metadata": {
                "query_allele_id": allele_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _alliance_get(self, gene_id: str, path: str, params: Dict[str, Any]) -> Dict:
        """Helper: GET an Alliance gene sub-endpoint and return parsed JSON."""
        url = f"{ALLIANCE_BASE}/gene/{gene_id}/{path}"
        response = requests.get(
            url,
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    def _get_gene_orthologs_paralogs(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get orthologs and paralogs of a gene across model organisms."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = min(max(1, int(arguments.get("limit", 20))), 100)
        page = max(1, int(arguments.get("page", 1)))
        stringency = arguments.get("stringency", "stringent")

        orth_data = self._alliance_get(
            gene_id,
            "orthologs",
            {"limit": limit, "page": page, "filter.stringency": stringency},
        )
        orthologs = []
        for r in orth_data.get("results", []):
            orth = r.get("geneToGeneOrthologyGenerated", {})
            obj_gene = orth.get("objectGene", {})
            annotations = r.get("geneAnnotationsMap", {})
            obj_id = obj_gene.get("primaryExternalId")
            ann = annotations.get(obj_id, {}) if isinstance(annotations, dict) else {}
            orthologs.append(
                {
                    "ortholog_gene_id": obj_id,
                    "ortholog_symbol": (obj_gene.get("geneSymbol") or {}).get(
                        "displayText"
                    ),
                    "ortholog_species": (obj_gene.get("taxon") or {}).get("name"),
                    "stringency": r.get("stringencyFilter"),
                    "has_disease_annotations": ann.get("hasDiseaseAnnotations"),
                    "has_expression_annotations": ann.get("hasExpressionAnnotations"),
                    "methods": [
                        m.get("name")
                        for m in orth.get("predictionMethodsMatched", [])
                        if isinstance(m, dict)
                    ],
                }
            )

        para_data = self._alliance_get(
            gene_id, "paralogs", {"limit": limit, "page": page}
        )
        paralogs = []
        for r in para_data.get("results", []):
            para = r.get("geneToGeneParalogy", {})
            obj_gene = para.get("objectGene", {})
            paralogs.append(
                {
                    "paralog_gene_id": obj_gene.get("primaryExternalId"),
                    "paralog_symbol": (obj_gene.get("geneSymbol") or {}).get(
                        "displayText"
                    ),
                    "paralog_species": (obj_gene.get("taxon") or {}).get("name"),
                    "methods": [
                        m.get("name")
                        for m in para.get("predictionMethodsMatched", [])
                        if isinstance(m, dict)
                    ],
                    # What makes it a paralog rather than which tools agree it
                    # is one. Alliance quantifies a paralogy relationship by
                    # sequence: Pax6's first paralog is 50% similar, 38%
                    # identical over 473 aligned residues, and ranked 1 of 42.
                    # The row carried the symbol and the method names, so two
                    # paralogs predicted by the same three tools looked the
                    # same whether they shared 38% or 90% of their residues.
                    "similarity_percent": para.get("similarity"),
                    "identity_percent": para.get("identity"),
                    "alignment_length": para.get("length"),
                    "rank": para.get("rank"),
                    "methods_not_matched": [
                        m.get("name")
                        for m in (para.get("predictionMethodsNotMatched") or [])
                        if isinstance(m, dict) and m.get("name")
                    ],
                    "methods_not_called": [
                        m.get("name")
                        for m in (para.get("predictionMethodsNotCalled") or [])
                        if isinstance(m, dict) and m.get("name")
                    ],
                }
            )

        ortholog_total = orth_data.get("total", len(orthologs))
        paralog_total = para_data.get("total", len(paralogs))
        ortholog_has_more = page * limit < ortholog_total
        paralog_has_more = page * limit < paralog_total
        has_more = ortholog_has_more or paralog_has_more

        return {
            "status": "success",
            "data": {
                "ortholog_count": ortholog_total,
                "orthologs": orthologs,
                "paralog_count": paralog_total,
                "paralogs": paralogs,
            },
            "metadata": {
                "query_gene_id": gene_id,
                "stringency": stringency,
                "page": page,
                "limit": limit,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "categories": {
                    "orthologs": {
                        "total": ortholog_total,
                        "returned": len(orthologs),
                        "has_more": ortholog_has_more,
                    },
                    "paralogs": {
                        "total": paralog_total,
                        "returned": len(paralogs),
                        "has_more": paralog_has_more,
                    },
                },
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_molecular_interactions(
        self, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Get molecular (physical) interactions for a gene with evidence refs."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit, page = self._page_parameters(arguments)

        data = self._alliance_get(
            gene_id, "molecular-interactions", {"limit": limit, "page": page}
        )

        interactions = []
        for r in data.get("results", []):
            gmi = r.get("geneMolecularInteraction", {})
            subject = gmi.get("geneAssociationSubject", {})
            obj = gmi.get("geneGeneAssociationObject", {}) or {}
            int_type = gmi.get("interactionType") or {}
            interactions.append(
                {
                    "subject_gene_id": subject.get("primaryExternalId"),
                    "subject_symbol": (subject.get("geneSymbol") or {}).get(
                        "displayText"
                    ),
                    "interactor_gene_id": obj.get("primaryExternalId"),
                    "interactor_symbol": (obj.get("geneSymbol") or {}).get(
                        "displayText"
                    ),
                    "interactor_species": (obj.get("taxon") or {}).get("name"),
                    "interaction_type": int_type.get("name")
                    if isinstance(int_type, dict)
                    else None,
                    "relation": (gmi.get("relation") or {}).get("name"),
                    # Bait and prey. Which molecule was treated and which was
                    # captured is the direction of the experiment, and a
                    # pull-down reported without it names a pair only.
                    "subject_role": _mi_term(gmi.get("interactorARole")),
                    "interactor_role": _mi_term(gmi.get("interactorBRole")),
                    "subject_type": _mi_term(gmi.get("interactorAType")),
                    "interactor_type": _mi_term(gmi.get("interactorBType")),
                    # How the interaction was detected -- MI:0096 "pull down",
                    # MI:0018 "two hybrid", MI:0019 "coimmunoprecipitation".
                    # This is what separates physical evidence from a screen
                    # artefact, and it was the one field neither this method
                    # nor its richer sibling carried.
                    "detection_method": _mi_term(gmi.get("detectionMethod")),
                    "interaction_source": _mi_term(gmi.get("interactionSource")),
                    # The schema declares these as objects with the pubmed id
                    # and the citation; the previous code emitted bare strings,
                    # so a caller following the declaration found the wrong type.
                    "references": _alliance_references(gmi.get("evidence")),
                }
            )

        return {
            "status": "success",
            "data": interactions,
            "metadata": {
                **self._page_metadata(
                    data.get("total", len(interactions)),
                    len(interactions),
                    limit,
                    page,
                ),
                "query_gene_id": gene_id,
                "source": "Alliance of Genome Resources",
            },
        }

    def _get_gene_alleles_and_models(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get alleles/variants and affected genomic models (mutant strains)."""
        gene_id = self._normalize_gene_id(arguments.get("gene_id", ""))
        if not gene_id:
            return {"status": "error", "error": "gene_id parameter is required"}

        limit = min(max(1, int(arguments.get("limit", 20))), 100)
        page = max(1, int(arguments.get("page", 1)))

        allele_data = self._alliance_get(
            gene_id, "alleles", {"limit": limit, "page": page}
        )
        alleles = []
        for r in allele_data.get("results", []):
            summary = _allele_summary(r)
            variant_list = r.get("variantList") or []
            variant_locs = []
            for v in variant_list[:3]:
                for loc in v.get("curatedVariantGenomicLocations", [])[:1]:
                    variant_locs.append(loc.get("hgvs"))
            alleles.append(
                {
                    "allele_id": summary["id"],
                    "symbol": summary["symbol"],
                    "category": r.get("category"),
                    "alteration_type": r.get("alterationType"),
                    "has_disease": r.get("hasDisease"),
                    "has_phenotype": r.get("hasPhenotype"),
                    # `variant_locations` kept only each variant's HGVS and
                    # dropped its coordinates and type. The allele's own
                    # variant records carry both.
                    "variant_locations": [v for v in variant_locs if v],
                    "variants": _allele_variants(variant_list),
                    "variants_total": len(variant_list),
                }
            )

        model_data = self._alliance_get(
            gene_id, "models", {"limit": limit, "page": page}
        )
        models = []
        for r in model_data.get("results", []):
            model = r.get("model") or {}
            full_name = model.get("agmFullName") or {}
            models.append(
                {
                    "model_id": model.get("primaryExternalId"),
                    "model_curie": model.get("curie"),
                    "model_name": full_name.get("displayText")
                    if isinstance(full_name, dict)
                    else model.get("name"),
                    "subtype": (model.get("subtype") or {}).get("name"),
                    "data_provider": (model.get("dataProvider") or {}).get(
                        "abbreviation"
                    ),
                    # What is actually wrong with the mutant strain. The
                    # response lists them per model -- "microphthalmia",
                    # "cornea opacity", "abnormal iris morphology" for MGI
                    # Pax6 models -- and the row carried the strain's name and
                    # nothing it does. `hasPhenotypeAnnotations: true` beside
                    # no phenotypes is the same shape as a success beside no
                    # data.
                    "phenotypes": [
                        ph
                        for ph in (r.get("associatedPhenotype") or [])
                        if isinstance(ph, str)
                    ],
                    "modifier_relationship_types": r.get("modifierRelationshipTypes")
                    or [],
                    "diseases": [
                        {
                            "name": (dm.get("disease") or {}).get("name"),
                            "id": (dm.get("disease") or {}).get("curie"),
                            "association_type": dm.get("associationType"),
                        }
                        for dm in (r.get("diseaseModels") or [])
                        if isinstance(dm, dict)
                    ],
                    "has_disease_annotations": r.get("hasDiseaseAnnotations"),
                    "has_phenotype_annotations": r.get("hasPhenotypeAnnotations"),
                }
            )

        # The models endpoint names the gene on every row -- its curie, its
        # external id and its display symbol -- and a caller who passed
        # "MGI:97490" got back `query_gene_id: MGI:97490` and never the word
        # "Pax6". The symbol belongs once in the metadata rather than on every
        # row, because the row's gene is fixed by the request.
        gene_reference = {}
        for row in model_data.get("results", []):
            gene = row.get("gene") if isinstance(row, dict) else None
            if not isinstance(gene, dict) or not gene:
                continue
            symbol = gene.get("geneSymbol") or {}
            gene_reference = {
                "curie": gene.get("curie"),
                "primary_external_id": gene.get("primaryExternalId"),
                "symbol": symbol.get("displayText") or symbol.get("formatText")
                if isinstance(symbol, dict)
                else symbol,
                "full_name": (gene.get("geneFullName") or {}).get("displayText")
                if isinstance(gene.get("geneFullName"), dict)
                else gene.get("geneFullName"),
            }
            break

        allele_total = allele_data.get("total", len(alleles))
        model_total = model_data.get("total", len(models))
        allele_has_more = page * limit < allele_total
        model_has_more = page * limit < model_total
        has_more = allele_has_more or model_has_more

        return {
            "status": "success",
            "data": {
                "allele_count": allele_total,
                "alleles": alleles,
                "model_count": model_total,
                "models": models,
            },
            "metadata": {
                "query_gene_id": gene_id,
                "gene": gene_reference,
                "page": page,
                "limit": limit,
                "has_more": has_more,
                "next_page": page + 1 if has_more else None,
                "categories": {
                    "alleles": {
                        "total": allele_total,
                        "returned": len(alleles),
                        "has_more": allele_has_more,
                    },
                    "models": {
                        "total": model_total,
                        "returned": len(models),
                        "has_more": model_has_more,
                    },
                },
                "source": "Alliance of Genome Resources",
            },
        }
