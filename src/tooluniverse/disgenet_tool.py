"""
DisGeNET API tool for ToolUniverse.

DisGeNET is one of the largest public collections of genes and variants
associated with human diseases, aggregating data from multiple sources.

API Documentation: https://api.disgenet.com/
Requires API key: Register at https://www.disgenet.com/

Note: the DisGeNET v1 API exposes gene/variant-disease associations through the
`/gda/summary` and `/vda/summary` endpoints using QUERY parameters
(`gene_symbol`, `gene_ncbi_id`, `disease`, `variant`), authenticated with an
`Authorization: <api_key>` header (no "Bearer " prefix). Academic API keys can
only access CURATED sources (CLINGEN, CLINVAR, ORPHANET, GENCC, UNIPROT, ...).
"""

import re
import requests
from typing import Dict, Any, List
from .base_tool import BaseTool
from .tool_registry import register_tool

# Base URL for DisGeNET API
DISGENET_API_URL = "https://api.disgenet.com/api/v1"

# A disease passed as a bare UMLS CUI looks like "C0006142".
_CUI_RE = re.compile(r"^C\d+$")

# Fix-R13B-2: DisGeNET's /summary endpoints emit one "warning" per
# *unset* optional filter param (e.g. "min_pli > The parameter value is
# unspecified or not a double number."), regardless of whether the
# caller ever intended to supply it. A plain gene-only query returns
# ~30 of these alongside the one warning that's actually actionable
# (the academic-key CURATED-sources-only note), burying it. These are
# recognizable by their fixed "unspecified" phrasing and are dropped;
# any other warning text (real data-quality notes) is kept.
_UNSET_PARAM_WARNING_RE = re.compile(
    r"is (?:empty / unspecified|unspecified or not an? [\w\s]+)\.?\s*$"
)


def _drop_unset_param_noise(warnings: List[str]) -> List[str]:
    return [w for w in warnings if not _UNSET_PARAM_WARNING_RE.search(w)]


def _or_none(value):
    """DisGeNET writes an unknown string attribute as "", not as null."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


# gnomAD frequencies arrive as -1.0 where the allele was never observed, and
# -1.0 read as a frequency is a hundred million times too large.
_NO_OBSERVATION = -1.0


def _freqs(values):
    return [None if v == _NO_OBSERVATION else v for v in values or []]


@register_tool("DisGeNETTool")
class DisGeNETTool(BaseTool):
    """
    Tool for querying DisGeNET gene-disease association database.

    Supports:
    - Gene-disease associations (GDAs)
    - Variant-disease associations (VDAs)
    - Disease -> associated genes

    Requires API key via DISGENET_API_KEY environment variable.
    Register for free at https://www.disgenet.com/
    """

    def __init__(self, tool_config: Dict[str, Any]):
        super().__init__(tool_config)
        self.timeout: int = tool_config.get("timeout", 30)
        self.parameter = tool_config.get("parameter", {})

    @property
    def api_key(self) -> str:
        """Resolve the DisGeNET key for the active request."""
        return self.credential("DISGENET_API_KEY") or ""

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with authentication.

        The DisGeNET v1 API expects the raw key in the Authorization header
        (NOT an OAuth "Bearer <key>" form).
        """
        headers = {
            "Accept": "application/json",
            "User-Agent": "ToolUniverse/DisGeNET",
        }
        if self.api_key:
            headers["Authorization"] = self.api_key
        return headers

    # ------------------------------------------------------------------ helpers

    @staticmethod
    def _normalize_disease(disease: str):
        """Return a DisGeNET-acceptable disease code, or None if the input is a
        free-text name (which the summary endpoint does not accept)."""
        d = (disease or "").strip()
        if not d:
            return None
        if d.upper().startswith("UMLS_"):
            return "UMLS_" + d[5:]
        if _CUI_RE.match(d):
            return "UMLS_" + d
        # Already a vocabulary-prefixed code (e.g. MONDO_..., DO_..., HPO_...)
        if "_" in d and d.split("_", 1)[0].isupper():
            return d
        return None

    @staticmethod
    def _cui_format_error(disease: str) -> Dict[str, Any]:
        """Feature-14C-01: shared by every '{disease}' is not a UMLS CUI'
        error path. 'C0006142' is a fixed format example (breast cancer),
        never a resolution of the caller's own input -- state that
        explicitly so it can't be mistaken for a dynamically-resolved CUI."""
        return {
            "status": "error",
            "error": (
                f"'{disease}' is not a UMLS CUI. Resolve '{disease}' to its "
                f"own CUI via umls_search_concepts -- 'C0006142' (breast "
                f"cancer) is only a format example and unrelated to "
                f"'{disease}'."
            ),
        }

    def _query_summary(self, kind: str, query: Dict[str, Any]):
        """Call /{gda,vda}/summary with query params. Returns (payload, warnings).
        Raises requests exceptions on HTTP error (handled by callers)."""
        params = {"page_number": 0}
        params.update({k: v for k, v in query.items() if v not in (None, "")})
        response = requests.get(
            f"{DISGENET_API_URL}/{kind}/summary",
            params=params,
            headers=self._get_headers(),
            timeout=self.timeout,
        )
        response.raise_for_status()
        body = response.json()
        payload = body.get("payload") or []
        warnings = _drop_unset_param_noise(body.get("warnings") or [])
        return payload, warnings

    @staticmethod
    def _common_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """The parts of a DisGeNET summary row shared by gene and variant hits.

        A summary row carries 37 fields and seven were read. Three groups
        mattered and are carried now:

        * the disease's other identifiers. `diseaseUMLSCUI` alone pins the
          disease in one vocabulary; `diseaseVocabularies` is where the MONDO,
          DO, MeSH, ORDO and NCI ids are, and without them an association
          cannot be joined to anything else.
        * the evidence counts. The tool's own description promises "evidence
          counts" and returned only the PMID count, while the same row states
          how many clinical trials and dbSNP records support the association,
          and over what years.
        * what the score is made of. `scoreBreakdown` names the sources behind
          each component and their weights, so a 1.25 can be read as five
          curated sources at weight 0.7 plus one clinical at 0.1 rather than
          taken on faith.
        """
        return {
            "assoc_id": row.get("assocID"),
            "disease_name": row.get("diseaseName"),
            "disease_umls_cui": row.get("diseaseUMLSCUI"),
            "disease_type": row.get("diseaseType"),
            "disease_vocabularies": row.get("diseaseVocabularies") or [],
            "disease_classes": {
                "mesh": row.get("diseaseClasses_MSH") or [],
                "do": row.get("diseaseClasses_DO") or [],
                "hpo": row.get("diseaseClasses_HPO") or [],
                "umls_semantic_type": row.get("diseaseClasses_UMLS_ST") or [],
            },
            "score": row.get("score"),
            "normalized_score": row.get("normalized_score"),
            "score_breakdown": row.get("scoreBreakdown") or [],
            "n_pmids": row.get("numPMIDs"),
            "n_clinical_trials": row.get("numCTsupportingAssociation"),
            "n_dbsnps": row.get("numDBSNPsupportingAssociation"),
            # The chemicals named in the evidence are a dimension of their own
            # -- BRCA1 alone answers 727 of them with 3,206 cross-references --
            # so the count is reported and the list is not. Query DisGeNET's
            # chemical endpoints with `assoc_id` for the list itself.
            "n_chemicals_in_evidence": row.get("numChemsIncludedInEvidences"),
            "year_first": row.get("yearInitial"),
            "year_last": row.get("yearFinal"),
            "ei": row.get("ei"),
            "el": row.get("el"),
            # The disease's own Orphanet attributes, on the same row. How a
            # disease is inherited decides what a gene-disease association
            # means for a family, and the prevalence says whether a "rare"
            # label is 1 in 2,000 or 1 in a million. 10 of the 53 rows of a
            # NOD2 query carry an inheritance mode; DisGeNET writes the rest
            # as "" rather than null, which is why they are normalised here.
            "disease_inheritance": _or_none(row.get("disease_inheritance")),
            "disease_prevalence_class": _or_none(row.get("disease_prevalence_class")),
            "disease_prevalence_type": _or_none(row.get("disease_prevalence_type")),
            "disease_prevalence_geo_area": _or_none(
                row.get("disease_prevalence_geo_area")
            ),
        }

    @staticmethod
    def _gene_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """The gene's own identifiers and DisGeNET's gene-level indices.

        A /vda/summary row names its gene under different keys from a
        /gda/summary row -- `geneSymbol_keyword` and `geneNcbiIDs`, both
        lists, where a GDA row has the scalars `symbolOfGene` and
        `geneNcbiID`. Reading only the GDA spelling returned
        `gene_symbol: null` on every variant-disease association, from a row
        that said "KRAS": a variant tool that could not answer which gene the
        variant is in. Both spellings are read now, and the list form is kept
        because a variant can sit in more than one gene.
        """
        symbols = row.get("geneSymbol_keyword") or []
        if isinstance(symbols, str):
            symbols = [symbols]
        if not symbols and row.get("symbolOfGene"):
            symbols = [row["symbolOfGene"]]
        ncbi_ids = row.get("geneNcbiIDs") or []
        if not isinstance(ncbi_ids, list):
            ncbi_ids = [ncbi_ids]
        if not ncbi_ids and row.get("geneNcbiID") is not None:
            ncbi_ids = [row["geneNcbiID"]]
        class_ids = row.get("geneProteinClassIDs") or []
        class_names = row.get("geneProteinClassNames") or []
        return {
            "gene_symbol": symbols[0] if symbols else None,
            "gene_symbols": symbols,
            "gene_ncbi_id": ncbi_ids[0] if ncbi_ids else None,
            "gene_ncbi_ids": ncbi_ids,
            "gene_ensembl_ids": row.get("geneEnsemblIDs") or [],
            "gene_ncbi_type": row.get("geneNcbiType"),
            "gene_uniprot_ids": row.get("geneProteinStrIDs") or [],
            "gene_dsi": row.get("geneDSI"),
            "gene_dpi": row.get("geneDPI"),
            "gene_pli": row.get("genepLI"),
            # What kind of protein the gene codes for -- "Enzyme",
            # "Transcription factor", "GPCR" -- which is the first thing asked
            # of a candidate gene and is on all 53 rows of a NOD2 query. The
            # names drive the list rather than zip(), so a short id list
            # cannot silently drop a class that was named.
            "gene_protein_classes": [
                {"id": class_ids[i] if i < len(class_ids) else None, "name": name}
                for i, name in enumerate(class_names)
            ],
        }

    @classmethod
    def _fmt_gda(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        return {**cls._gene_fields(row), **cls._common_fields(row)}

    @staticmethod
    def _variant_fields(row: Dict[str, Any]) -> Dict[str, Any]:
        """What the variant IS, which a /vda/summary row answers in full.

        The tool returned the rsID and the disease and nothing between them:
        no position, no consequence, no HGVS, no population frequency and
        neither of the two pathogenicity predictions the same row carries.

        Three of these lists must not be zipped together, which is why they
        are reported as they arrive:

        * `alleleFreqExome` / `alleleFreqGenome` run parallel to
          `alleles_alt` on every variant checked (rs1801133's 0.3227 is the
          first alternate allele, C677T; rs113488022's 1.37e-06 is the third,
          V600E), so those are paired with the allele and -1.0 -- gnomAD
          never observed it -- becomes null.
        * `hgvsc` / `hgvsp` can be SHORTER than `alleles_alt`: rs1801133 has
          three alternate alleles and two HGVS strings. Pairing them by
          position would attach one allele's notation to another.
        * `oneletterID` / `threeletterID` enumerate every transcript's
          numbering of every allele, sorted and of a different length
          again -- 12 labels for rs113488022's 3 alleles, naming V157, V299,
          V600 and V640 for the same substitution. They are a set of names
          for the variant, not a per-allele list.
        """
        alts = row.get("alleles_alt") or []
        if isinstance(alts, str):
            alts = [alts]
        freq_exome = _freqs(row.get("alleleFreqExome"))
        freq_genome = _freqs(row.get("alleleFreqGenome"))
        per_allele = None
        if alts and len(freq_exome) == len(alts) and len(freq_genome) == len(alts):
            per_allele = [
                {
                    "allele": allele,
                    "frequency_exome": exome,
                    "frequency_genome": genome,
                }
                for allele, exome, genome in zip(alts, freq_exome, freq_genome)
            ]
        return {
            "variant": row.get("variantStrID"),
            "chromosome": row.get("chromosome"),
            "position": row.get("coord"),
            "reference_allele": row.get("alleles_ref"),
            "alternate_alleles": alts,
            "most_severe_consequence": row.get("mostSevereConsequences"),
            "hgvs_c": row.get("hgvsc") or [],
            "hgvs_p": row.get("hgvsp") or [],
            "protein_changes": row.get("oneletterID") or [],
            "protein_changes_three_letter": row.get("threeletterID") or [],
            "allele_frequencies": per_allele,
            "allele_frequency_exome": freq_exome,
            "allele_frequency_genome": freq_genome,
            "sift_score": row.get("sift_score"),
            "polyphen_score": row.get("polyphen_score"),
            "variant_dsi": row.get("variantDSI"),
            "variant_dpi": row.get("variantDPI"),
        }

    @classmethod
    def _fmt_vda(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **cls._variant_fields(row),
            **cls._gene_fields(row),
            **cls._common_fields(row),
        }

    @staticmethod
    def _apply_filters(rows: List[Dict[str, Any]], min_score, limit):
        if min_score is not None:
            rows = [
                r
                for r in rows
                if (r.get("score") is not None and r["score"] >= min_score)
            ]
        if limit:
            rows = rows[: int(limit)]
        return rows

    def _declared_limit_default(self, fallback):
        # _gene_disease and _disease_genes each back 2 registered tool names
        # (e.g. DisGeNET_search_gene default=10 vs DisGeNET_get_gda
        # default=25, both routed through _gene_disease). Read the
        # per-instance declared default instead of hardcoding one limit for
        # both, or the tool with the smaller declared default silently
        # returns more rows than documented whenever `limit` is omitted.
        return (
            self.tool_config.get("parameter", {})
            .get("properties", {})
            .get("limit", {})
            .get("default", fallback)
        )

    def _err(self, e) -> Dict[str, Any]:
        if isinstance(e, requests.exceptions.HTTPError) and e.response is not None:
            code = e.response.status_code
            if code in (401, 403):
                return {
                    "status": "error",
                    "error": "DisGeNET API key invalid or unauthorized for this resource (academic keys only access CURATED sources).",
                }
            return {"status": "error", "error": f"DisGeNET HTTP error: {code}"}
        return {"status": "error", "error": f"DisGeNET request failed: {str(e)}"}

    # --------------------------------------------------------------- dispatch

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute DisGeNET API call based on operation type."""
        if not self.api_key:
            return {
                "status": "error",
                "error": "DisGeNET API key required. Provide DISGENET_API_KEY as a request credential or environment variable. Register at https://www.disgenet.com/",
            }

        operation = arguments.get("operation", "")
        if not operation:
            operation = self.get_schema_const_operation()

        if operation in ("search_gene", "get_gda"):
            return self._gene_disease(arguments)
        elif operation in ("search_disease", "get_disease_genes"):
            return self._disease_genes(arguments)
        elif operation == "get_vda":
            return self._variant_disease(arguments)
        else:
            return {
                "status": "error",
                "error": f"Unknown operation: {operation}. Supported: search_gene, search_disease, get_gda, get_vda, get_disease_genes",
            }

    # ---------------------------------------------------------------- operations

    def _gene_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Gene-disease associations by gene symbol (or NCBI gene id)."""
        gene = (arguments.get("gene") or "").strip()
        disease = (arguments.get("disease") or "").strip()
        if not gene and not disease:
            return {
                "status": "error",
                "error": "Provide 'gene' (symbol or NCBI id) or 'disease' (UMLS CUI).",
            }

        query: Dict[str, Any] = {}
        if gene:
            if gene.isdigit():
                query["gene_ncbi_id"] = gene
            else:
                query["gene_symbol"] = gene
        if disease:
            code = self._normalize_disease(disease)
            if code is None:
                return self._cui_format_error(disease)
            query["disease"] = code
        if arguments.get("source"):
            query["source"] = arguments["source"]

        try:
            payload, warnings = self._query_summary("gda", query)
        except Exception as e:  # noqa: BLE001 - never raise out of run()
            return self._err(e)

        rows = self._apply_filters(
            [self._fmt_gda(r) for r in payload],
            arguments.get("min_score"),
            arguments.get("limit", self._declared_limit_default(25)),
        )
        metadata: Dict[str, Any] = {
            "source": "DisGeNET GDA",
            "warnings": warnings,
            "note": "Academic keys return CURATED sources only.",
        }
        # Fix-R13B-2: DisGeNET matches gene_symbol exactly, so a legacy/
        # alias symbol (e.g. 'CARD15', the old official symbol for NOD2)
        # silently returns an empty list with no hint that a symbol
        # mismatch -- not a real absence of associations -- is the cause.
        # Confirmed live: gene='CARD15' -> 0 associations, gene='NOD2' ->
        # real Crohn/Blau-syndrome associations. We can't safely
        # auto-resolve the alias ourselves (that needs a maintained
        # gene-symbol synonym table we don't have), so just flag the
        # ambiguity instead of leaving an empty result unexplained.
        if gene and not rows and not gene.isdigit():
            metadata["note"] += (
                f" No associations found for gene symbol '{gene}'. DisGeNET "
                "matches the current HGNC-approved symbol only, not older "
                "aliases -- if this might be a legacy/alias symbol, resolve "
                "it to its current official symbol first (e.g. via "
                "NCBIGene_search or HGNC) and retry."
            )
        return {
            "status": "success",
            "data": {
                "gene": gene or None,
                "disease": disease or None,
                "associations": rows,
                "count": len(rows),
            },
            "metadata": metadata,
        }

    def _disease_genes(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """All genes associated with a disease (UMLS CUI)."""
        disease = (arguments.get("disease") or "").strip()
        if not disease:
            return {
                "status": "error",
                "error": "Missing required parameter: disease (UMLS CUI, e.g. 'C0006142' for breast cancer -- an example format, not a default value).",
            }
        code = self._normalize_disease(disease)
        if code is None:
            return {
                "status": "error",
                "error": f"'{disease}' is not a UMLS CUI. Resolve '{disease}' to its own CUI via umls_search_concepts -- 'C0006142' (breast cancer) is only a format example and unrelated to '{disease}'.",
            }

        query: Dict[str, Any] = {"disease": code}
        if arguments.get("source"):
            query["source"] = arguments["source"]
        try:
            payload, warnings = self._query_summary("gda", query)
        except Exception as e:  # noqa: BLE001
            return self._err(e)

        genes, seen = [], set()
        for row in payload:
            sym = row.get("symbolOfGene")
            if sym and sym not in seen:
                seen.add(sym)
                genes.append(
                    {
                        "symbol": sym,
                        "ncbi_id": row.get("geneNcbiID"),
                        "score": row.get("score"),
                        "n_pmids": row.get("numPMIDs"),
                        # Same row, same gap: the specificity indices are what
                        # say whether a gene on a disease's list is specific to
                        # it or associated with hundreds of diseases, and the
                        # trial and dbSNP counts are evidence counts too.
                        "ensembl_ids": row.get("geneEnsemblIDs") or [],
                        "ncbi_type": row.get("geneNcbiType"),
                        "dsi": row.get("geneDSI"),
                        "dpi": row.get("geneDPI"),
                        "pli": row.get("genepLI"),
                        "n_clinical_trials": row.get("numCTsupportingAssociation"),
                        "n_dbsnps": row.get("numDBSNPsupportingAssociation"),
                        # The same three things the gene->disease direction
                        # already carries, dropped only because this handler
                        # built its own row: the association id needed to ask
                        # DisGeNET anything further about it, the UniProt
                        # accessions, the protein class, and what the score
                        # is made of. A disease's gene list ranked by a score
                        # whose composition is not shown cannot be triaged:
                        # 0.8 from two curated sources and 0.8 from text
                        # mining are not the same claim.
                        "assoc_id": row.get("assocID"),
                        "uniprot_ids": row.get("geneProteinStrIDs") or [],
                        "protein_classes": row.get("geneProteinClassNames") or [],
                        "score_breakdown": row.get("scoreBreakdown") or [],
                        # When the association was first and last published.
                        # A gene supported by 2,248 papers whose last one is
                        # from 1998 is a different candidate from one whose
                        # last is from this year, and the count alone cannot
                        # tell them apart.
                        "year_first": row.get("yearInitial"),
                        "year_last": row.get("yearFinal"),
                    }
                )
        genes = self._apply_filters(
            genes,
            arguments.get("min_score"),
            arguments.get("limit", self._declared_limit_default(50)),
        )
        # The disease the code resolved to. Every row names it, and the tool
        # echoed back only the code the caller already had -- so a caller who
        # passed the wrong CUI got a gene list with nothing in it to say so.
        first = payload[0] if payload else {}
        return {
            "status": "success",
            "data": {
                "disease": disease,
                "disease_code": code,
                "disease_name": first.get("diseaseName"),
                "disease_type": first.get("diseaseType"),
                "disease_vocabularies": first.get("diseaseVocabularies") or [],
                "disease_classes": {
                    "mesh": first.get("diseaseClasses_MSH") or [],
                    "do": first.get("diseaseClasses_DO") or [],
                    "hpo": first.get("diseaseClasses_HPO") or [],
                    "umls_semantic_type": first.get("diseaseClasses_UMLS_ST") or [],
                },
                "disease_inheritance": _or_none(first.get("disease_inheritance")),
                "genes": genes,
                "gene_count": len(genes),
            },
            "metadata": {
                "source": "DisGeNET",
                "warnings": warnings,
                "note": "Academic keys return CURATED sources only.",
            },
        }

    def _variant_disease(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Variant-disease associations by variant rsID or gene symbol."""
        variant = (arguments.get("variant") or "").strip()
        gene = (arguments.get("gene") or "").strip()
        if not variant and not gene:
            return {
                "status": "error",
                "error": "Provide 'variant' (rsID) or 'gene' (symbol).",
            }
        query: Dict[str, Any] = {}
        if variant:
            query["variant"] = variant
        elif gene:
            query["gene_symbol"] = gene
        try:
            payload, warnings = self._query_summary("vda", query)
        except Exception as e:  # noqa: BLE001
            return self._err(e)
        rows = self._apply_filters(
            [self._fmt_vda(r) for r in payload],
            arguments.get("min_score"),
            arguments.get("limit", 25),
        )
        return {
            "status": "success",
            "data": {
                "variant": variant or None,
                "gene": gene or None,
                "associations": rows,
                "count": len(rows),
            },
            "metadata": {
                "source": "DisGeNET VDA",
                "warnings": warnings,
                "note": "Academic keys return CURATED sources only.",
            },
        }
