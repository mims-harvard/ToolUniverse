"""
MaveDB Tool - Multiplexed Assay of Variant Effect Database

MaveDB stores and distributes results from Multiplexed Assays of Variant Effect
(MAVEs), including deep mutational scanning experiments. Score sets contain
functional impact scores for thousands of variants in a single protein/gene.

API: https://api.mavedb.org/api/v1/
Reference: Esposito et al. (2019) Genome Research
"""

import csv
import io
import json
import re
from collections import Counter

import requests
from typing import Dict, Any, List, Optional, Tuple
from .base_tool import BaseTool
from .tool_registry import register_tool

MAVEDB_API = "https://api.mavedb.org/api/v1"

# A MaveDB publication can carry 21 authors and a score set can cite several
# papers. The author list is capped per publication with the count beside it.
AUTHORS_PER_PUBLICATION = 25
UNIPROT_API = "https://rest.uniprot.org/uniprotkb"

# Standard 20-amino-acid order (matches what every downstream skill expects)
_STANDARD_AAS = "ACDEFGHIKLMNPQRSTVWY"
_THREE_TO_ONE: Dict[str, str] = {
    "Ala": "A",
    "Arg": "R",
    "Asn": "N",
    "Asp": "D",
    "Cys": "C",
    "Gln": "Q",
    "Glu": "E",
    "Gly": "G",
    "His": "H",
    "Ile": "I",
    "Leu": "L",
    "Lys": "K",
    "Met": "M",
    "Phe": "F",
    "Pro": "P",
    "Ser": "S",
    "Thr": "T",
    "Trp": "W",
    "Tyr": "Y",
    "Val": "V",
}
_HGVS_SINGLE_MISSENSE_RE = re.compile(r"^p\.\(?([A-Z][a-z]{2})(\d+)([A-Z][a-z]{2})\)?$")


@register_tool("MaveDBTool")
class MaveDBTool(BaseTool):
    """Search MaveDB for variant effect score sets and retrieve details."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})
        self.required = self.parameter.get("required", [])
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    @staticmethod
    def _publication(pub: Dict[str, Any]) -> Dict[str, Any]:
        """One publication identifier, as MaveDB answers it.

        The tools returned the bare PubMed number. The same object carries the
        title, the journal, the year, the DOI, a formatted citation and the
        author list -- 21 authors on the UBE2I score set's paper -- so a
        caller had an id to resolve elsewhere instead of the citation it was
        already given.
        """
        authors = [a for a in (pub.get("authors") or []) if isinstance(a, dict)]
        return {
            "identifier": pub.get("identifier"),
            "db_name": pub.get("dbName"),
            "title": pub.get("title"),
            "journal": pub.get("publicationJournal"),
            "year": pub.get("publicationYear"),
            "doi": pub.get("doi"),
            "url": pub.get("url"),
            "citation": pub.get("referenceHtml"),
            "authors": [
                {"name": a.get("name"), "primary": a.get("primary")}
                for a in authors[:AUTHORS_PER_PUBLICATION]
            ],
            "author_count": len(authors),
            "authors_truncated": len(authors) > AUTHORS_PER_PUBLICATION,
        }

    @staticmethod
    def _keywords(record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """The controlled keywords an experiment is indexed under.

        MaveDB answers each as a {key, label, description} triple -- the
        assay, the phenotype measured, the delivery method -- and none of it
        reached the caller, who got a free-text title to guess from.
        """
        out = []
        for item in record.get("keywords") or []:
            if not isinstance(item, dict):
                continue
            keyword = item.get("keyword") or {}
            out.append(
                {
                    "key": keyword.get("key"),
                    "label": keyword.get("label"),
                    "description": keyword.get("description"),
                    "special": keyword.get("special"),
                    # The ontology the term comes from, where MaveDB records
                    # one, and the curator's own note on why this keyword
                    # applies to this experiment -- a different thing from the
                    # term's definition.
                    "system": keyword.get("system"),
                    "code": keyword.get("code"),
                    "version": keyword.get("version"),
                    "note": item.get("description"),
                }
            )
        return out

    @staticmethod
    def _target_gene(tg: Dict[str, Any]) -> Dict[str, Any]:
        """One target gene, with what it is and what organism it is from.

        `uniprot_id` was read from `targetSequence.uniprot`, which a target
        sequence does not carry, so it was None on every score set while the
        accession sat in `uniprotIdFromMappedMetadata` -- P63279 for UBE2I.
        `category` ("protein_coding"), the sequence type (dna or protein) and
        the taxonomy were dropped too, and a DMS score set read against the
        wrong organism is a different experiment.
        """
        sequence = tg.get("targetSequence") or {}
        taxonomy = sequence.get("taxonomy") or {}
        external = []
        for item in tg.get("externalIdentifiers") or []:
            if not isinstance(item, dict):
                continue
            identifier = item.get("identifier") or {}
            external.append(
                {
                    "db_name": identifier.get("dbName"),
                    "identifier": identifier.get("identifier"),
                    "url": identifier.get("url"),
                    "offset": item.get("offset"),
                }
            )
        text = sequence.get("sequence") or ""
        # A target is given either as a sequence or as an accession, and a
        # search row usually gives the accession with `targetSequence: null`.
        accession = tg.get("targetAccession") or {}
        return {
            "name": tg.get("name"),
            "category": tg.get("category"),
            "mapped_hgnc_name": tg.get("mappedHgncName"),
            "accession": accession.get("accession"),
            "accession_gene": accession.get("gene"),
            "accession_assembly": accession.get("assembly"),
            "is_base_editor": accession.get("isBaseEditor"),
            "uniprot_id": tg.get("uniprotIdFromMappedMetadata")
            or ((sequence.get("uniprot") or {}).get("identifier")),
            "external_identifiers": external,
            "sequence_type": sequence.get("sequenceType"),
            "sequence_length": len(text) or None,
            # The construct the assay was actually run on. Positions in a DMS
            # score set are numbered against this, so a caller checking a
            # variant's position has nothing to check it against without it.
            "sequence": text or None,
            "organism": taxonomy.get("organismName"),
            "taxon_id": taxonomy.get("code"),
            "common_name": taxonomy.get("commonName"),
            "taxon_rank": taxonomy.get("rank"),
            "taxon_url": taxonomy.get("url"),
            "taxon_reference": taxonomy.get("articleReference"),
            # MaveDB's internal numeric key. The urn is what its endpoints
            # take; this is here so the same target gene can be recognised
            # across responses.
            "record_id": tg.get("id"),
        }

    def _search(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB score sets by text query."""
        query = params.get("query", "")
        limit = max(1, int(params.get("limit", 20)))
        offset = max(0, int(params.get("offset", 0)))
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        resp = self.session.post(
            f"{MAVEDB_API}/score-sets/search",
            json={"text": query},
            timeout=30,
        )
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        data = resp.json()
        all_score_sets = data.get("scoreSets", [])
        score_sets = all_score_sets[offset : offset + limit]
        results = []
        for ss in score_sets:
            target_genes = [
                g.get("name")
                for g in (ss.get("targetGenes") or [])
                if isinstance(g, dict) and g.get("name")
            ]
            experiment = ss.get("experiment") or {}
            results.append(
                {
                    "urn": ss.get("urn"),
                    "title": ss.get("title"),
                    "short_description": ss.get("shortDescription"),
                    # Expose the target gene(s) so a full-text hit on a different
                    # gene (e.g. query "BRCA1" matching "BRCA1-Associated Protein
                    # 1"/BAP1) is visible rather than silently taken for the query.
                    "target_genes": target_genes,
                    "num_variants": ss.get("numVariants"),
                    "published_date": ss.get("publishedDate"),
                    # What the target actually is: the category, the accession
                    # or sequence it was measured against, and the organism.
                    # A search result naming "BAP1" does not say whether the
                    # assay was run on human protein or a yeast construct.
                    "target_gene_details": [
                        self._target_gene(g)
                        for g in (ss.get("targetGenes") or [])
                        if isinstance(g, dict)
                    ],
                    # The paper, so a search result can be judged without a
                    # second call per hit.
                    "publications": [
                        self._publication(pub)
                        for pub in ss.get("primaryPublicationIdentifiers") or []
                        if isinstance(pub, dict)
                    ],
                    # The assay the score set came from, and the controlled
                    # keywords it is indexed under -- which is what tells two
                    # score sets of the same gene apart.
                    "experiment_urn": experiment.get("urn"),
                    "experiment_title": experiment.get("title"),
                    "experiment_method": experiment.get("methodText"),
                    "experiment_set_urn": experiment.get("experimentSetUrn"),
                    "keywords": self._keywords(experiment),
                    "secondary_publications": [
                        self._publication(pub)
                        for pub in ss.get("secondaryPublicationIdentifiers") or []
                        if isinstance(pub, dict)
                    ],
                    "license": (ss.get("license") or {}).get("shortName"),
                    "license_name": (ss.get("license") or {}).get("longName"),
                    "license_url": (ss.get("license") or {}).get("link"),
                }
            )
        return {
            "status": "success",
            "data": results,
            "metadata": {
                # True number of matches (MaveDB returns them all in one page),
                # computed before truncation so callers know more may exist.
                "total_results": len(all_score_sets),
                "returned_results": len(results),
                "offset": offset,
                "limit": limit,
                "has_more": offset + len(results) < len(all_score_sets),
                "truncated": offset + len(results) < len(all_score_sets),
                "next_offset": offset + len(results)
                if offset + len(results) < len(all_score_sets)
                else None,
                "query": query,
            },
        }

    def _get_score_set(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get detailed information about a specific score set by URN."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        resp = self.session.get(f"{MAVEDB_API}/score-sets/{urn}", timeout=30)
        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        d = resp.json()
        target_genes = [
            self._target_gene(tg)
            for tg in d.get("targetGenes") or []
            if isinstance(tg, dict)
        ]
        experiment = d.get("experiment") or {}
        license_info = d.get("license") or {}

        result = {
            "urn": d.get("urn"),
            "title": d.get("title"),
            "short_description": d.get("shortDescription"),
            "abstract": d.get("abstractText"),
            "method": d.get("methodText"),
            "num_variants": d.get("numVariants"),
            "published_date": d.get("publishedDate"),
            "license": license_info.get("shortName"),
            "license_name": license_info.get("longName"),
            "license_url": license_info.get("link"),
            "target_genes": target_genes,
            "doi_identifiers": [
                doi.get("identifier") for doi in d.get("doiIdentifiers") or []
            ],
            # Kept as it was, and the same papers in full beside it.
            "primary_publications": [
                pub.get("identifier")
                for pub in d.get("primaryPublicationIdentifiers") or []
            ],
            "publications": [
                self._publication(pub)
                for pub in d.get("primaryPublicationIdentifiers") or []
                if isinstance(pub, dict)
            ],
            "secondary_publications": [
                self._publication(pub)
                for pub in d.get("secondaryPublicationIdentifiers") or []
                if isinstance(pub, dict)
            ],
            # What the scores look like. Without the range and the histogram a
            # caller has no way to choose a threshold or even to know which
            # direction is damaging: UBE2I runs -0.39 to 4.12 over 24 bins,
            # and `nullCount` says how many variants have no score at all.
            "score_distribution": d.get("scoreDistribution"),
            # Which columns the score table actually has -- score, sd, se,
            # exp.score, df, pred.score for UBE2I -- which is what decides
            # whether a per-variant query can ask for an error estimate.
            "dataset_columns": d.get("datasetColumns"),
            # The clinical calibration, where MaveDB has one: the score ranges
            # that map onto ACMG PS3/BS3 evidence strengths, with the number
            # of variants in each band and MaveDB's own research-use-only
            # flag. For a score set used to interpret a variant this is the
            # part that says what a score MEANS, and it was dropped whole.
            "score_calibrations": d.get("scoreCalibrations") or [],
            # The parent experiment: its own abstract and method text, the
            # keywords it is indexed under, and the other score sets derived
            # from the same assay.
            "experiment": {
                "urn": experiment.get("urn"),
                "title": experiment.get("title"),
                "short_description": experiment.get("shortDescription"),
                "abstract": experiment.get("abstractText"),
                "method": experiment.get("methodText"),
                "keywords": self._keywords(experiment),
                "score_set_urns": experiment.get("scoreSetUrns") or [],
                "num_score_sets": experiment.get("numScoreSets"),
                "publications": [
                    self._publication(pub)
                    for pub in experiment.get("primaryPublicationIdentifiers") or []
                    if isinstance(pub, dict)
                ],
            }
            if experiment
            else None,
            # Whether this score set has been mapped to genomic coordinates
            # yet. `mappingState: "incomplete"` is why a variant query can
            # come back with no VRS allele, and nothing said so.
            "mapping_state": d.get("mappingState"),
            "processing_state": d.get("processingState"),
            "meta_analyzes_score_set_urns": d.get("metaAnalyzesScoreSetUrns") or [],
            "meta_analyzed_by_score_set_urns": d.get("metaAnalyzedByScoreSetUrns")
            or [],
            "official_collections": d.get("officialCollections") or [],
            "external_links": d.get("externalLinks") or {},
        }
        return {
            "status": "success",
            "data": result,
            "metadata": {"urn": urn},
        }

    def _get_variant_scores(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get variant functional scores from a score set (CSV endpoint)."""
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        hgvs_filter = (params.get("hgvs_pro") or "").strip()
        # limit semantics: client-side truncation of the CSV returned by the
        # /scores endpoint (the endpoint itself returns every variant in one
        # call — there is no server-side pagination). limit=None / omitted /
        # 0 means "return all", which is what DMS workflows need on whole-
        # protein score sets (e.g. KRAS folding ΔΔG has ~2200 variants).
        raw_limit = params.get("limit")
        limit = None
        if raw_limit is not None:
            try:
                lv = int(raw_limit)
                limit = None if lv <= 0 else lv
            except (TypeError, ValueError):
                limit = None

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/scores",
                timeout=60,
                headers={"Accept": "text/csv"},
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        csv_text = resp.text
        if not csv_text.strip():
            return {
                "status": "error",
                "error": f"No scores available for '{urn}'",
            }

        reader = csv.DictReader(io.StringIO(csv_text))
        variants = []
        total_parsed = 0
        for row in reader:
            total_parsed += 1
            if hgvs_filter:
                hgvs_pro_val = row.get("hgvs_pro") or ""
                if hgvs_filter.lower() not in hgvs_pro_val.lower():
                    continue

            variant = {
                "hgvs_nt": row.get("hgvs_nt") or None,
                "hgvs_splice": row.get("hgvs_splice") or None,
                "hgvs_pro": row.get("hgvs_pro") or None,
            }
            for key, value in row.items():
                if key in ("accession", "hgvs_nt", "hgvs_splice", "hgvs_pro"):
                    continue
                if value and value != "NA":
                    try:
                        variant[key] = float(value)
                    except ValueError:
                        variant[key] = value

            variants.append(variant)
            if limit is not None and len(variants) >= limit:
                # Continue counting total_parsed so we can report the true total
                # in the response (let the user know more variants exist that
                # were truncated client-side).
                for _ in reader:
                    total_parsed += 1
                break

        truncated = (
            limit is not None and len(variants) >= limit and total_parsed > limit
        )
        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_variants_in_set": total_parsed,
                "returned": len(variants),
                "truncated": truncated,
                "limit_applied": limit,
                "hgvs_filter": hgvs_filter or None,
                "variants": variants,
            },
        }

    def _summarize_vrs_allele(
        self, allele: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Flatten a GA4GH VRS Allele into the few fields callers actually use.

        Pulls the SequenceLocation (genomic coordinates when postMapped) plus
        the literal state sequence and any hgvs.g expression. Returns None for a
        null / non-dict allele so missing maps don't crash downstream code.
        """
        if not isinstance(allele, dict):
            return None
        loc = allele.get("location") or {}
        seq_ref = loc.get("sequenceReference") or {}
        state = allele.get("state") or {}
        expressions = [
            e.get("value")
            for e in (allele.get("expressions") or [])
            if isinstance(e, dict) and e.get("value")
        ]
        return {
            "vrs_id": allele.get("id"),
            "sequence_reference_label": seq_ref.get("label"),
            "refget_accession": seq_ref.get("refgetAccession"),
            "start": loc.get("start"),
            "end": loc.get("end"),
            "state_sequence": state.get("sequence"),
            "hgvs_expressions": expressions or None,
        }

    @staticmethod
    def _parse_limit(raw_limit: Any) -> Optional[int]:
        """Coerce a user-supplied ``limit`` to a positive int, else None (no cap)."""
        if raw_limit is None:
            return None
        try:
            value = int(raw_limit)
        except (TypeError, ValueError):
            return None
        return None if value <= 0 else value

    @staticmethod
    def _apply_limit(items: list, limit: Optional[int]) -> Tuple[list, bool]:
        """Truncate ``items`` to ``limit`` rows, returning (rows, truncated)."""
        if limit is not None and len(items) > limit:
            return items[:limit], True
        return items, False

    @staticmethod
    def _parse_offset(raw_offset: Any) -> Optional[int]:
        """Coerce an offset to a non-negative integer, or return None."""
        if raw_offset is None:
            return 0
        if isinstance(raw_offset, bool):
            return None
        try:
            value = int(raw_offset)
        except (TypeError, ValueError):
            return None
        return value if value >= 0 else None

    @staticmethod
    def _paginate(
        items: list, limit: Optional[int], offset: int
    ) -> Tuple[list, bool, bool, Optional[int]]:
        """Return a recoverable local page over an upstream full-list response."""
        end = None if limit is None else offset + limit
        page = items[offset:end]
        has_more = offset + len(page) < len(items)
        truncated = offset > 0 or has_more
        next_offset = offset + len(page) if has_more else None
        return page, truncated, has_more, next_offset

    def _get_mapped_variants(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get genomically-mapped (GA4GH VRS / ClinGen Allele ID) coordinates.

        Reads ``/score-sets/{urn}/variant-details``. The older
        ``/mapped-variants`` route this operation used was retired upstream:
        since 2026-11-01 it answers HTTP 410 with the body "GET
        /score-sets/<urn>/mapped-variants has been removed. Use GET
        /score-sets/<urn>/variant-details instead", and MaveDB's own OpenAPI
        now documents it as "Removed; see GET /score-sets/{urn}/variant-details".

        The successor carries strictly more: the preMapped/postMapped VRS pair
        it always had, plus MaveDB's own cross-level projection (``mapped``),
        which is what finally makes the genomic coordinate readable without
        resolving a refget accession. Two fields the old route carried --
        ``vrsVersion`` and ``errorMessage`` -- have no successor in the new
        payload and are not emitted as perpetual nulls. ``alignmentLevel``
        becomes ``assay_level``, which is the level the assay itself scored
        (protein / cdna / genomic), not the level the mapping reached.

        The response is newline-delimited JSON, one record per variant, and the
        route takes no page-size parameter: a 784-variant score set is 11.4 MB.
        limit/offset remain a recoverable local page over the full download.
        """
        urn = (params.get("urn") or "").strip()
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        limit = self._parse_limit(params.get("limit"))
        offset = self._parse_offset(params.get("offset", 0))
        if offset is None:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/variant-details", timeout=120
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code == 410:
            # The route we now call is itself the replacement for a retired
            # one. If MaveDB retires it too, its 410 body names the successor,
            # so pass that through instead of a bare status code.
            detail = ""
            try:
                detail = (resp.json() or {}).get("detail") or ""
            except ValueError:
                detail = (resp.text or "")[:300]
            return {
                "status": "error",
                "error": (
                    "MaveDB has retired the variant-details route this tool "
                    f"calls (HTTP 410). Upstream says: {detail}"
                    if detail
                    else "MaveDB has retired the variant-details route this "
                    "tool calls (HTTP 410)."
                ),
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        raw, parse_error = self._parse_ndjson(resp.text)
        if parse_error:
            return {"status": "error", "error": parse_error}

        mapped = []
        n_with_genomic = 0
        n_with_clingen = 0
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            post = self._summarize_vrs_allele(entry.get("postMapped"))
            pre = self._summarize_vrs_allele(entry.get("preMapped"))
            clingen = entry.get("clingenAlleleId")
            projections = entry.get("mapped")
            if not isinstance(projections, dict):
                projections = {}
            genomic = projections.get("genomic")
            if not isinstance(genomic, dict):
                genomic = {}
            cdna = projections.get("cdna")
            if not isinstance(cdna, dict):
                cdna = {}
            protein = projections.get("protein")
            if not isinstance(protein, dict):
                protein = {}
            if genomic.get("hgvs"):
                n_with_genomic += 1
            if clingen:
                n_with_clingen += 1
            mapped.append(
                {
                    "variant_urn": entry.get("urn"),
                    "clingen_allele_id": clingen,
                    "assay_level": entry.get("assayLevel"),
                    "mapping_mode": entry.get("mode"),
                    "current": entry.get("isCurrent"),
                    "superseded_by_score_set": entry.get("supersededByScoreSet"),
                    "target_hgvs": entry.get("targetHgvs"),
                    "reference_hgvs": entry.get("referenceHgvs"),
                    "genomic_hgvs": genomic.get("hgvs"),
                    "cdna_hgvs": cdna.get("hgvs"),
                    "protein_hgvs": protein.get("hgvs"),
                    "post_mapped": post,
                    "pre_mapped": pre,
                }
            )

        total = len(mapped)
        mapped, truncated, has_more, next_offset = self._paginate(mapped, limit, offset)

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_mapped_variants": total,
                "returned": len(mapped),
                "truncated": truncated,
                "offset": offset,
                "limit_applied": limit,
                "has_more": has_more,
                "next_offset": next_offset,
                "result_set_complete": not truncated,
                "n_with_genomic_location": n_with_genomic,
                "n_with_clingen_allele_id": n_with_clingen,
                "mapped_variants": mapped,
            },
            "metadata": {
                "source": (
                    "MaveDB variant-details (GA4GH VRS + Cat-VRS + ClinGen "
                    "Allele Registry)"
                ),
                "note": (
                    "genomic_hgvs is MaveDB's own projection of the scored "
                    "variant onto the genome (NC_ accession) and is the field "
                    "to join on; it is null for a score set MaveDB could not "
                    "project. post_mapped/pre_mapped are the VRS Alleles at "
                    "the level the assay scored, whose sequenceReference "
                    "carries a refget accession and no label, so a genomic "
                    "variant is counted from genomic_hgvs, not from the "
                    "accession. clingen_allele_id links scores to "
                    "ClinVar/dbSNP."
                ),
            },
        }

    @staticmethod
    def _parse_ndjson(body: str) -> Tuple[List[Dict[str, Any]], Optional[str]]:
        """Parse newline-delimited JSON, tolerating a single JSON array.

        MaveDB's variant-details route streams one object per line. A plain
        ``resp.json()`` on that body raises "Extra data: line 2 column 1", and
        the old route this replaced did return a single array, so accept both
        rather than make the format a hard dependency.
        """
        text = (body or "").strip()
        if not text:
            return [], None
        if text[0] == "[":
            try:
                parsed = json.loads(text)
            except ValueError as e:
                return [], f"Invalid JSON from MaveDB: {e}"
            if isinstance(parsed, list):
                return parsed, None
            return [parsed], None
        records: List[Dict[str, Any]] = []
        for lineno, line in enumerate(text.split("\n"), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except ValueError as e:
                return (
                    [],
                    "MaveDB returned a line that is not JSON "
                    f"(line {lineno} of its newline-delimited response): {e}",
                )
        return records, None

    def _get_clinical_controls(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get ClinVar clinical-control variants overlapping a score set.

        Returns the ClinVar pathogenic/benign/VUS variants that overlap the
        score set's mapped variants — the reference set used to calibrate MAVE
        functional scores into clinically-interpretable thresholds.
        """
        urn = (params.get("urn") or "").strip()
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        sig_filter = (params.get("clinical_significance") or "").strip().lower()
        limit = self._parse_limit(params.get("limit"))
        offset = self._parse_offset(params.get("offset", 0))
        if offset is None:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/clinical-controls", timeout=30
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        try:
            raw = resp.json()
        except ValueError as e:
            return {"status": "error", "error": f"Invalid JSON from MaveDB: {e}"}
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        controls = []
        sig_counts: Counter = Counter()
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            significance = entry.get("clinicalSignificance")
            if sig_filter and (significance or "").lower() != sig_filter:
                continue
            sig_counts[significance or "Unknown"] += 1
            # The link back to the score set's own variant. A clinical
            # control answers "ClinVar calls 65709 in BRCA2 Pathogenic"; the
            # link is what connects that to the measured score, which is the
            # whole reason the endpoint exists. It arrives under
            # `clinvarLinks` and was read from `mappedVariants`, a key the
            # response does not carry, so `mapped_variant_urns` was empty on
            # all 2,122 controls of urn:mavedb:00001263-a-2.
            links = [
                link
                for link in (
                    entry.get("clinvarLinks") or entry.get("mappedVariants") or []
                )
                if isinstance(link, dict)
            ]
            mapped_urns = [
                link.get("variantUrn") for link in links if link.get("variantUrn")
            ]
            controls.append(
                {
                    "db_name": entry.get("dbName"),
                    "db_identifier": entry.get("dbIdentifier"),
                    "db_version": entry.get("dbVersion"),
                    "gene_symbol": entry.get("geneSymbol"),
                    "clinical_significance": significance,
                    "clinical_review_status": entry.get("clinicalReviewStatus"),
                    "record_id": entry.get("id"),
                    "mapped_variant_urns": mapped_urns,
                    # Each link with the allele digest it was matched on, so a
                    # control that maps to one variant through two different
                    # alleles is visible as that rather than as a duplicate.
                    "variant_links": [
                        {
                            "variant_urn": link.get("variantUrn"),
                            "allele_digest": link.get("alleleDigest"),
                        }
                        for link in links
                    ],
                }
            )

        total = len(controls)
        controls, truncated, has_more, next_offset = self._paginate(
            controls, limit, offset
        )

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_clinical_controls": total,
                "returned": len(controls),
                "truncated": truncated,
                "offset": offset,
                "limit_applied": limit,
                "has_more": has_more,
                "next_offset": next_offset,
                "result_set_complete": not truncated,
                "significance_filter": sig_filter or None,
                "significance_breakdown": dict(sig_counts),
                "clinical_controls": controls,
            },
            "metadata": {
                "source": "MaveDB clinical-controls (ClinVar overlap)",
                "note": (
                    "ClinVar pathogenic/benign/VUS variants overlapping the "
                    "score set, used to calibrate functional scores. Each entry's "
                    "mapped_variant_urns point to the MaveDB variant(s) with the "
                    "same genomic coordinate."
                ),
            },
        }

    def _get_gnomad_variants(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get gnomAD population-frequency variants observed within a score set.

        Returns gnomAD variants (allele count / number / frequency) that fall
        within the score set, each linked to the MaveDB mapped variant via a
        postMapped VRS Allele — lets you cross population frequency with the
        measured functional score.
        """
        urn = (params.get("urn") or "").strip()
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        limit = self._parse_limit(params.get("limit"))
        offset = self._parse_offset(params.get("offset", 0))
        if offset is None:
            return {
                "status": "error",
                "error": "offset must be a non-negative integer",
            }

        try:
            resp = self.session.get(
                f"{MAVEDB_API}/score-sets/{urn}/gnomad-variants", timeout=30
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code == 404:
            return {
                "status": "error",
                "error": f"Score set '{urn}' not found in MaveDB",
            }
        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB request failed: HTTP {resp.status_code}",
            }

        try:
            raw = resp.json()
        except ValueError as e:
            return {"status": "error", "error": f"Invalid JSON from MaveDB: {e}"}
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        variants = []
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            mapped_post = []
            for mv in entry.get("mappedVariants") or []:
                if isinstance(mv, dict):
                    summary = self._summarize_vrs_allele(mv.get("postMapped"))
                    if summary:
                        mapped_post.append(summary)
            variants.append(
                {
                    "db_name": entry.get("dbName"),
                    "db_identifier": entry.get("dbIdentifier"),
                    "db_version": entry.get("dbVersion"),
                    "record_id": entry.get("id"),
                    "allele_count": entry.get("alleleCount"),
                    "allele_number": entry.get("alleleNumber"),
                    "allele_frequency": entry.get("alleleFrequency"),
                    # The filtering allele frequency: the 95% confidence upper
                    # bound in the ancestry group where it is highest. This,
                    # not the raw alleleFrequency, is what ACMG BA1/BS1
                    # thresholds are read against, and gnomAD publishes it for
                    # exactly that reason.
                    "faf95_max": entry.get("faf95Max"),
                    "faf95_max_ancestry": entry.get("faf95MaxAncestry"),
                    # Which rows of THIS score set the variant was observed in.
                    # The tool exists to connect a score set to gnomAD, and
                    # that connection is the join key.
                    "score_set_variants": [
                        {
                            "variant_urn": link.get("variantUrn"),
                            "allele_digest": link.get("alleleDigest"),
                        }
                        for link in (entry.get("variantLinks") or [])
                        if isinstance(link, dict)
                    ],
                    "mapped_genomic_alleles": mapped_post,
                }
            )

        total = len(variants)
        variants, truncated, has_more, next_offset = self._paginate(
            variants, limit, offset
        )

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "total_gnomad_variants": total,
                "returned": len(variants),
                "truncated": truncated,
                "offset": offset,
                "limit_applied": limit,
                "has_more": has_more,
                "next_offset": next_offset,
                "result_set_complete": not truncated,
                "gnomad_variants": variants,
            },
            "metadata": {
                "source": "MaveDB gnomAD-variants (population frequency overlap)",
                "note": (
                    "gnomAD variants observed within the score set. Cross "
                    "allele_frequency with the MAVE functional score: rare "
                    "high-impact variants are candidate disease alleles."
                ),
            },
        }

    def _search_experiments(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search MaveDB experiments by text query."""
        query = params.get("query", "")
        if not query:
            return {"status": "error", "error": "query parameter is required"}

        try:
            resp = self.session.post(
                f"{MAVEDB_API}/experiments/search",
                json={"text": query},
                timeout=30,
            )
        except requests.exceptions.RequestException as e:
            return {"status": "error", "error": f"MaveDB API error: {e}"}

        if resp.status_code != 200:
            return {
                "status": "error",
                "error": f"MaveDB search failed: HTTP {resp.status_code}",
            }

        raw = resp.json()
        if not isinstance(raw, list):
            raw = [raw] if raw else []

        experiments = []
        for exp in raw:
            urn = exp.get("urn", "")
            if urn.startswith("tmp:"):
                continue

            pubs = [
                self._publication(pub)
                for pub in exp.get("primaryPublicationIdentifiers") or []
                if isinstance(pub, dict)
            ]
            score_set_urns = exp.get("scoreSetUrns") or []
            experiments.append(
                {
                    "urn": urn,
                    "title": exp.get("title"),
                    "short_description": exp.get("shortDescription"),
                    "published_date": exp.get("publishedDate"),
                    "score_set_urns": score_set_urns,
                    "num_score_sets": len(score_set_urns),
                    "publications": pubs,
                    # An experiment IS its method. The response carries the
                    # abstract and the method text -- how the library was
                    # made, how the phenotype was read -- and the row carried
                    # a title and a one-line description, so two experiments
                    # on the same gene were indistinguishable.
                    "abstract": exp.get("abstractText"),
                    "method": exp.get("methodText"),
                    "keywords": self._keywords(exp),
                    "experiment_set_urn": exp.get("experimentSetUrn"),
                    # Who deposited it. MaveDB records ORCIDs, which is the
                    # attribution the depositor asked for.
                    "contributors": [
                        {
                            "orcid_id": c.get("orcidId"),
                            "given_name": c.get("givenName"),
                            "family_name": c.get("familyName"),
                        }
                        for c in (exp.get("contributors") or [])
                        if isinstance(c, dict)
                    ],
                    "secondary_publications": [
                        self._publication(pub)
                        for pub in exp.get("secondaryPublicationIdentifiers") or []
                        if isinstance(pub, dict)
                    ],
                    "raw_read_identifiers": exp.get("rawReadIdentifiers") or [],
                    "doi_identifiers": [
                        {"identifier": doi.get("identifier"), "url": doi.get("url")}
                        for doi in exp.get("doiIdentifiers") or []
                        if isinstance(doi, dict)
                    ],
                }
            )

        return {
            "status": "success",
            "data": {
                "query": query,
                "total_experiments": len(experiments),
                "experiments": experiments,
            },
        }

    def _get_effect_matrix(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Fetch DMS score set and return ready-to-analyze effect matrix.

        Hides the parsing pipeline that every consuming skill used to inline:
          1. Fetch all variants (uses _get_variant_scores with no limit)
          2. Parse HGVS protein notation → (ref_aa, position, alt_aa)
          3. Filter to single missense (drop synonymous/nonsense/indels/multi)
          4. Optional: verify position numbering against UniProt canonical
          5. Reshape to (20 amino acids × n_positions) matrix in standard
             AA order ('ACDEFGHIKLMNPQRSTVWY')
        """
        urn = params.get("urn", "")
        if not urn:
            return {"status": "error", "error": "urn parameter is required"}

        uniprot_id: Optional[str] = params.get("uniprot_id")
        score_field: Optional[str] = params.get("score_field")

        # 1) Pull all variants via the existing helper (it uses the same session)
        raw = self._get_variant_scores({"urn": urn, "limit": 0})
        if raw.get("status") != "success":
            return raw

        variants = raw["data"].get("variants", [])
        total_in_set = raw["data"].get("total_variants_in_set", len(variants))

        # 2-3) parse HGVS + filter to single missense
        parsed: List[Tuple[str, int, str, float]] = []
        n_dropped = 0
        score_field_counter: Counter = Counter()
        for row in variants:
            hgvs = row.get("hgvs_pro") or ""
            m = _HGVS_SINGLE_MISSENSE_RE.match(hgvs)
            if not m:
                n_dropped += 1
                continue
            ref3, pos_str, alt3 = m.group(1), m.group(2), m.group(3)
            if ref3 not in _THREE_TO_ONE or alt3 not in _THREE_TO_ONE:
                n_dropped += 1
                continue
            # Pick a score field — explicit > 'score' > 'ddG' > 'fitness' > first numeric
            score: Optional[float] = None
            if score_field and score_field in row:
                try:
                    score = float(row[score_field])
                    score_field_counter[score_field] += 1
                except (TypeError, ValueError):
                    pass
            else:
                for cand in ("score", "ddG", "fitness"):
                    if row.get(cand) is None:
                        continue
                    try:
                        score = float(row[cand])
                        score_field_counter[cand] += 1
                        break
                    except (TypeError, ValueError):
                        continue
                if score is None:
                    for k, v in row.items():
                        if k.startswith("hgvs") or k == "accession":
                            continue
                        try:
                            score = float(v)
                            score_field_counter[k] += 1
                            break
                        except (TypeError, ValueError):
                            continue
            if score is None or (isinstance(score, float) and (score != score)):
                n_dropped += 1
                continue
            parsed.append(
                (_THREE_TO_ONE[ref3], int(pos_str), _THREE_TO_ONE[alt3], score)
            )

        if not parsed:
            return {
                "status": "error",
                "error": (
                    f"No usable single-missense variants found in '{urn}' "
                    f"({total_in_set} rows, {n_dropped} dropped — check that the "
                    f"score set uses HGVS protein notation and has numeric scores)."
                ),
            }

        score_field_used = (
            score_field_counter.most_common(1)[0][0] if score_field_counter else None
        )

        # 4) optional numbering verification against UniProt canonical
        numbering_offset: Optional[int] = None
        landmark_check: Optional[Dict[str, Any]] = None
        if uniprot_id:
            try:
                resp = self.session.get(f"{UNIPROT_API}/{uniprot_id}.fasta", timeout=30)
                if resp.status_code == 200:
                    seq_lines = resp.text.strip().splitlines()
                    canonical_seq = "".join(seq_lines[1:])
                    # Use the most-common parsed position as the landmark
                    position_counts = Counter(p[1] for p in parsed)
                    landmark_pos = position_counts.most_common(1)[0][0]
                    landmark_ref = next(p[0] for p in parsed if p[1] == landmark_pos)
                    seq_idx = landmark_pos - 1
                    if 0 <= seq_idx < len(canonical_seq):
                        uniprot_aa = canonical_seq[seq_idx]
                        if uniprot_aa == landmark_ref:
                            numbering_offset = 0
                            landmark_check = {
                                "position": landmark_pos,
                                "mavedb_ref": landmark_ref,
                                "uniprot_aa": uniprot_aa,
                                "match": True,
                            }
                        else:
                            # Try common offsets to detect the shift
                            offset_detected = None
                            for offset in range(-10, 11):
                                target_idx = seq_idx + offset
                                if (
                                    0 <= target_idx < len(canonical_seq)
                                    and canonical_seq[target_idx] == landmark_ref
                                ):
                                    offset_detected = offset
                                    break
                            landmark_check = {
                                "position": landmark_pos,
                                "mavedb_ref": landmark_ref,
                                "uniprot_aa": uniprot_aa,
                                "match": False,
                                "detected_offset": offset_detected,
                                "warning": (
                                    f"MaveDB position {landmark_pos} has ref_aa "
                                    f"{landmark_ref} but UniProt {uniprot_id} "
                                    f"position {landmark_pos} is {uniprot_aa}."
                                    + (
                                        f" Likely offset = {offset_detected}."
                                        if offset_detected is not None
                                        else ""
                                    )
                                ),
                            }
                            numbering_offset = offset_detected
                else:
                    landmark_check = {
                        "warning": f"UniProt {uniprot_id} lookup HTTP {resp.status_code}"
                    }
            except requests.exceptions.RequestException as exc:
                landmark_check = {"warning": f"UniProt verification failed: {exc}"}

        # 5) reshape into (20 × n_positions)
        positions = sorted({p[1] for p in parsed})
        pos_index = {p: i for i, p in enumerate(positions)}
        aa_index = {a: i for i, a in enumerate(_STANDARD_AAS)}

        matrix: List[List[Optional[float]]] = [
            [None] * len(positions) for _ in range(20)
        ]
        for ref_aa, pos, alt_aa, score in parsed:
            if alt_aa not in aa_index:
                continue
            matrix[aa_index[alt_aa]][pos_index[pos]] = score

        return {
            "status": "success",
            "data": {
                "urn": urn,
                "matrix": matrix,
                "positions": positions,
                "amino_acid_order": _STANDARD_AAS,
                "shape": [20, len(positions)],
                "n_parsed_single_missense": len(parsed),
                "n_dropped": n_dropped,
                "n_total_rows": total_in_set,
                "score_field_used": score_field_used,
                "numbering_check": landmark_check,
                "numbering_offset": numbering_offset,
            },
            "metadata": {
                "source": "MaveDB",
                "matrix_layout": (
                    "rows = 20 amino acids in 'ACDEFGHIKLMNPQRSTVWY' order; "
                    "columns = positions (1-based canonical, see positions field); "
                    "cells = score (None for unmeasured / WT-diagonal)"
                ),
                "note": (
                    "WT diagonal cells are None (the MaveDB API doesn't "
                    "include 'X→X' rows). Downstream skills should treat None "
                    "as missing data."
                ),
            },
        }

    def run(self, params: Dict[str, Any]) -> Dict[str, Any]:
        operation = self.tool_config.get("fields", {}).get("operation", "")
        dispatch = {
            "search": self._search,
            "get_score_set": self._get_score_set,
            "get_variant_scores": self._get_variant_scores,
            "search_experiments": self._search_experiments,
            "get_effect_matrix": self._get_effect_matrix,
            "get_mapped_variants": self._get_mapped_variants,
            "get_clinical_controls": self._get_clinical_controls,
            "get_gnomad_variants": self._get_gnomad_variants,
        }
        handler = dispatch.get(operation)
        if handler:
            return handler(params)
        return {"status": "error", "error": f"Unknown operation: {operation}"}
