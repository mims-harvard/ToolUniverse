"""Compound tool: annotate a variant from multiple sources in one call.

Queries ClinVar, gnomAD, CIViC, and UniProt for a given variant,
cross-references results, and returns a unified annotation with
pathogenicity classification, population frequencies, and clinical evidence.
"""

import re
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .tool_registry import register_tool

_AA_1TO3 = {
    "A": "Ala",
    "R": "Arg",
    "N": "Asn",
    "D": "Asp",
    "C": "Cys",
    "E": "Glu",
    "Q": "Gln",
    "G": "Gly",
    "H": "His",
    "I": "Ile",
    "L": "Leu",
    "K": "Lys",
    "M": "Met",
    "F": "Phe",
    "P": "Pro",
    "S": "Ser",
    "T": "Thr",
    "W": "Trp",
    "Y": "Tyr",
    "V": "Val",
    "X": "Ter",
    "*": "Ter",
}
_AA_3TO1 = {v.upper(): k for k, v in _AA_1TO3.items()}

# Genes whose historically-established variant nomenclature numbers residues
# from the mature protein (after post-translational cleavage of the
# initiator Met), one less than RefSeq's precursor-based protein HGVS
# numbering. Confirmed live for HBB via rs334, the sickle-cell mutation:
# dbSNP and ClinVar both report "p.Glu7Val" (NP_000509.1, Met-inclusive)
# while CIViC and essentially all clinical/scientific literature call it
# "Glu6Val"/"E6V" (mature-protein numbering, predating RefSeq by decades).
# Without this offset, an rsid-only query for this gene's best-known variant
# can never report exact_match=True even when CIViC's sole HBB entry IS that
# exact variant.
_MATURE_PROTEIN_OFFSET_GENES = {"HBB"}


# ClinVar clinical-significance terms ranked most→least clinically significant.
# Used to pick the headline classification when a query matches several ClinVar
# variants (e.g. a multi-allelic rsid whose alleles carry different
# classifications): the most severe must surface, never merely the first in the
# list — reporting a VUS while a Pathogenic allele is hidden is dangerous.
_CLINVAR_SEVERITY_ORDER = [
    "pathogenic",
    "pathogenic/likely pathogenic",
    "likely pathogenic",
    "established risk allele",
    "likely risk allele",
    "uncertain risk allele",
    "drug response",
    "conflicting classifications of pathogenicity",
    "conflicting interpretations of pathogenicity",
    "uncertain significance",
    "likely benign",
    "benign/likely benign",
    "benign",
]
_CLINVAR_SEVERITY_RANK = {term: i for i, term in enumerate(_CLINVAR_SEVERITY_ORDER)}


def _clinvar_severity_key(classification: str) -> int:
    """Sort key: lower = more clinically significant. Unknown terms sort after
    all pathogenic/risk terms but before benign, so a recognized Pathogenic
    always wins over an unrecognized label."""
    norm = str(classification or "").strip().lower()
    return _CLINVAR_SEVERITY_RANK.get(norm, len(_CLINVAR_SEVERITY_ORDER) - 3)


def _offset_protein_tokens(tokens: List[str], gene: Optional[str]) -> List[str]:
    """For genes in _MATURE_PROTEIN_OFFSET_GENES, add a position-1 candidate
    for each RefSeq-numbered token so mature-protein-numbered records (like
    CIViC's) can still match."""
    if gene not in _MATURE_PROTEIN_OFFSET_GENES:
        return tokens
    offset_tokens = []
    for tok in tokens:
        m = re.fullmatch(r"([A-Za-z]{3})(\d+)([A-Za-z]{3})", tok)
        if m:
            ref, pos, alt = m.group(1), m.group(2), m.group(3)
            offset_tokens.append(f"{ref}{int(pos) - 1}{alt}")
    return list(dict.fromkeys(tokens + offset_tokens))


def _variant_match_forms(token: str) -> List[str]:
    """Expand a protein change to every form that appears in records: 1-letter
    short form ('V600E', CIViC's convention) and HGVS 3-letter form
    ('Val600Glu', ClinVar's convention) -- converting whichever form the input
    is in to the other, so a token derived from either source (an explicit
    'variant' arg, typically short-form, or dbSNP's hgvs_notation, always
    3-letter form) matches titles in both conventions."""
    forms = [token.lower()]
    stripped = token.strip()
    m1 = re.fullmatch(r"([A-Za-z])(\d+)([A-Za-z*])", stripped)
    if m1:
        ref, pos, alt = m1.group(1).upper(), m1.group(2), m1.group(3).upper()
        if ref in _AA_1TO3 and alt in _AA_1TO3:
            forms.append(f"{_AA_1TO3[ref]}{pos}{_AA_1TO3[alt]}".lower())
    m3 = re.fullmatch(r"([A-Za-z]{3})(\d+)([A-Za-z]{3})", stripped)
    if m3:
        ref, pos, alt = m3.group(1).upper(), m3.group(2), m3.group(3).upper()
        if ref in _AA_3TO1 and alt in _AA_3TO1:
            forms.append(f"{_AA_3TO1[ref]}{pos}{_AA_3TO1[alt]}".lower())
    return forms


def _title_matches(name: str, token) -> bool:
    """token may be a single string or a list of candidate strings -- a
    multi-allelic rsid (e.g. a SNP with both A>C and A>G alternates at the
    same position) yields several distinct protein-change candidates from
    dbSNP's hgvs_notation, only one of which is the actual queried allele, so
    every candidate must be tried rather than assuming the first is right."""
    tokens = token if isinstance(token, list) else [token]
    low = str(name).lower()
    return any(f in low for t in tokens for f in _variant_match_forms(t))


@register_tool("CompoundVariantAnnotationTool")
class CompoundVariantAnnotationTool(BaseTool):
    """Annotate a variant from ClinVar, gnomAD, CIViC, and UniProt in one call."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        variant = arguments.get("variant")
        gene = arguments.get("gene") or arguments.get("gene_symbol")
        rsid = arguments.get("rsid")

        if not variant and not gene and not rsid:
            return {
                "status": "error",
                "error": "At least one of 'variant', 'gene', or 'rsid' is required.",
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        annotations: Dict[str, Any] = {}
        sources_failed: List[str] = []

        # Resolve the gene up front: ClinVar/CIViC/gnomAD/UniProt are all queried by
        # gene, NOT by a bare protein change like "V600E" (which matches nothing in
        # ClinVar). Derive the gene from the explicit arg, the variant, or (Fix-R31B-1)
        # dbSNP's rsid lookup when only an rsid was given -- ClinVar's own tools have
        # no direct rsid parameter (variant_id is ClinVar's own internal numeric id,
        # not a dbSNP rsid; confirmed live both "query"/"variant_id" set to "rs671"
        # return 0 results), so resolving to a gene first is the only way to use
        # ClinVar/CIViC/UniProt at all for an rsid-only query.
        gene_for_gnomad = gene
        if not gene_for_gnomad and variant:
            parts = variant.split()
            if parts:
                gene_for_gnomad = parts[0]
        # The protein-change token (e.g. "V600E") used to filter gene-level hits.
        variant_token = None
        if variant:
            toks = variant.split()
            variant_token = toks[-1] if toks else variant
        # Confirmed live for rs334+gene="HBB" (the sickle-cell mutation) given
        # together: the old "not gene_for_gnomad and rsid" guard skipped this
        # resolution entirely whenever gene was explicit, so variant_token
        # stayed None and CIViC/ClinVar matching silently never ran even
        # though CIViC's sole HBB entry IS the queried variant. Resolve from
        # rsid whenever a token is still missing, not only when gene is also
        # missing -- keep the explicit gene if one was given rather than
        # letting the resolved gene override it.
        if rsid and not variant_token:
            resolved_gene, rsid_variant_token = self._resolve_gene_from_rsid(
                tu, rsid, sources_failed
            )
            if not gene_for_gnomad:
                gene_for_gnomad = resolved_gene
            variant_token = rsid_variant_token

        # 1. ClinVar -- Fix-R31D-4/R31A-3: "query" is documented as an alias for
        # "condition" (a disease/phenotype free-text search), not a gene or rsid
        # lookup -- confirmed live that querying by gene name via "query" only
        # coincidentally matched conditions whose name happens to contain the gene
        # symbol (40 rows for HOXB13 vs the real 1943 via the dedicated "gene"
        # param). Use "gene" directly; a bare protein change with no resolvable
        # gene still can't be searched and is skipped, same as before.
        if gene_for_gnomad:
            try:
                # Fix-R78B-1: ClinVar_search_variants now supports a targeted
                # variant_name search (ClinVar's own [Variant name] field tag)
                # -- try that FIRST when we have candidate protein-change
                # token(s), since it's an exact server-side lookup rather than
                # a capped, arbitrarily-ordered gene-level browse. Confirmed
                # live this is necessary, not just nicer: rs334/HBB's
                # canonical sickle-cell record (VCV 15333, Pathogenic) has a
                # low/old variant ID and isn't within the first 100 -- or even
                # the first 425 clinical_significance=Pathogenic-filtered --
                # gene-level rows, so the old gene-level-only fetch always
                # reported "no exact ClinVar match" for one of the best-known
                # pathogenic variants in human genetics.
                parsed = None
                if variant_token:
                    tr = tu.run_one_function(
                        {
                            "name": "ClinVar_search_variants",
                            "arguments": {
                                "gene": gene_for_gnomad,
                                "variant_name": variant_token,
                                "limit": 20,
                            },
                        }
                    )
                    if not self._sub_call_error(tr):
                        candidate = self._parse_clinvar(tr, variant_token)
                        if candidate.get("exact_match"):
                            parsed = candidate

                # limit=100 (ClinVar_search_variants' own max) rather than 20:
                # fallback for when no variant_token was resolvable, or the
                # targeted variant_name search above didn't confirm a match
                # (e.g. a token whose nomenclature ClinVar's index doesn't
                # recognize) -- browse as many gene-level rows as possible and
                # filter client-side in _parse_clinvar, same as before this fix.
                if parsed is None:
                    r = tu.run_one_function(
                        {
                            "name": "ClinVar_search_variants",
                            "arguments": {"gene": gene_for_gnomad, "limit": 100},
                        }
                    )
                    error = self._sub_call_error(r)
                else:
                    r, error = None, None

                if error:
                    sources_failed.append(f"ClinVar: {error[:100]}")
                elif parsed is not None:
                    annotations["clinvar"] = parsed
                else:
                    annotations["clinvar"] = self._parse_clinvar(r, variant_token)
            except Exception as e:
                sources_failed.append(f"ClinVar: {str(e)[:100]}")

        # 2. gnomAD
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "gnomad_get_gene",
                        "arguments": {"gene_symbol": gene_for_gnomad},
                    }
                )
                error = self._sub_call_error(r)
                if error:
                    sources_failed.append(f"gnomAD: {error[:100]}")
                else:
                    annotations["gnomad"] = self._parse_gnomad(r)
            except Exception as e:
                sources_failed.append(f"gnomAD: {str(e)[:100]}")

        # 3. CIViC
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "civic_get_variants_by_gene",
                        "arguments": {"gene_symbol": gene_for_gnomad},
                    }
                )
                error = self._sub_call_error(r)
                if error:
                    sources_failed.append(f"CIViC: {error[:100]}")
                else:
                    annotations["civic"] = self._parse_civic(r, variant_token)
            except Exception as e:
                sources_failed.append(f"CIViC: {str(e)[:100]}")

        # 4. UniProt
        if gene_for_gnomad:
            try:
                r = tu.run_one_function(
                    {
                        "name": "UniProt_search",
                        "arguments": {
                            "query": gene_for_gnomad,
                            "organism": "human",
                            # Fix-R62A-2: bumped 3->5 so a correct match
                            # ranked below UniProt's top few relevance hits
                            # (see _parse_uniprot) is still in the fetched
                            # set to select from.
                            "limit": 5,
                        },
                    }
                )
                error = self._sub_call_error(r)
                if error:
                    sources_failed.append(f"UniProt: {error[:100]}")
                else:
                    annotations["uniprot"] = self._parse_uniprot(r, gene_for_gnomad)
            except Exception as e:
                sources_failed.append(f"UniProt: {str(e)[:100]}")

        # Build summary
        summary = self._build_summary(annotations, variant, gene_for_gnomad, rsid)

        return {
            "status": "success",
            "data": {
                "query": {"variant": variant, "gene": gene, "rsid": rsid},
                "sources_queried": list(annotations.keys()),
                "sources_failed": sources_failed,
                "summary": summary,
                "annotations": annotations,
            },
        }

    def _sub_call_error(self, result: Any) -> Optional[str]:
        """Fix-R2B-003: sub-tool calls signal failure by returning a
        {"status": "error", ...} dict, not by raising — the try/except around
        each call only catches raised exceptions, so an upstream failure was
        silently parsed as "zero variants found" instead of being recorded in
        sources_failed. Detect that shape here so callers can distinguish a
        genuine empty result from a failed call."""
        if isinstance(result, dict) and result.get("status") == "error":
            return str(result.get("error", "unknown error"))
        return None

    def _resolve_gene_from_rsid(
        self, tu, rsid: str, sources_failed: List[str]
    ) -> "tuple[Optional[str], Optional[List[str]]]":
        """Resolve an rsid to its gene symbol via dbSNP, so ClinVar/CIViC/gnomAD/
        UniProt (all gene-keyed, none rsid-keyed) can still be queried for an
        rsid-only request. dbSNP's esummary response has no dedicated gene field --
        the symbol is embedded in hgvs_notation as "...|GENE=SYMBOL:geneid" -- so
        extract it from there.

        Also extracts protein-change token candidates (e.g. "Lys329Glu") from
        the same hgvs_notation string when present -- without this, an
        rsid-only query's ClinVar cross-reference could never report
        exact_match=True even when the exact variant IS in ClinVar's results,
        since variant_token (used by _parse_clinvar/_parse_civic's substring
        match) was previously only ever derived from an explicit 'variant'
        argument, never from 'rsid'. Confirmed live for rs77931234 (ACADM
        p.Lys329Glu, a ClinVar Pathogenic/Likely pathogenic MCAD-deficiency
        founder variant): without this, exact_match stayed False and the
        summary reported "no exact ClinVar match" despite the variant being
        VCV000003586 in ClinVar's own database. Returns a list, not a single
        token: a multi-allelic site (like this one, which also has an A>C
        alternate at the same position) lists one protein change per allele,
        and only the one matching the actually-queried allele will hit."""
        try:
            r = tu.run_one_function(
                {"name": "dbsnp_get_variant_by_rsid", "arguments": {"rsid": rsid}}
            )
            error = self._sub_call_error(r)
            if error:
                sources_failed.append(f"dbSNP (rsid->gene): {error[:100]}")
                return None, None
            hgvs = str((r.get("data") or {}).get("hgvs_notation", ""))
            m = re.search(r"GENE=([A-Za-z0-9\-]+):", hgvs)
            if not m:
                sources_failed.append(
                    f"dbSNP (rsid->gene): no gene found in hgvs_notation for {rsid}"
                )
                return None, None
            gene = m.group(1)
            # A multi-allelic position (this rsid's site has both A>C and A>G
            # alternates) lists a protein change per allele -- collect every
            # distinct one; only the one matching the actual queried allele
            # will hit in ClinVar/CIViC's title text, the rest are no-ops.
            variant_tokens = list(
                dict.fromkeys(re.findall(r"p\.([A-Za-z]{3}\d+[A-Za-z]{3})", hgvs))
            )
            variant_tokens = _offset_protein_tokens(variant_tokens, gene)
            return gene, (variant_tokens or None)
        except Exception as e:
            sources_failed.append(f"dbSNP (rsid->gene): {str(e)[:100]}")
            return None, None

    def _parse_clinvar(self, result: Any, variant_token: str = None) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        data = result.get("data", {})
        variants = data.get("variants", []) if isinstance(data, dict) else []

        def _row(v: Dict[str, Any]) -> Dict[str, Any]:
            # Fix-R31A-3: ClinVar_search_variants rows never carry a "condition"
            # key (confirmed live) -- condition/disease is a search filter on
            # that tool, not a returned field, so this always silently read "".
            return {
                "name": v.get("title", v.get("name", "")),
                "classification": v.get(
                    "clinical_significance", v.get("classification", "")
                ),
                "review_status": v.get("review_status", ""),
            }

        rows = [v for v in variants if isinstance(v, dict)]
        matched = [
            _row(v)
            for v in rows
            if variant_token
            and _title_matches(v.get("title", v.get("name", "")), variant_token)
        ]
        # If the specific change isn't found (ClinVar titles use HGVS), still return
        # the top gene-level variants as context rather than a misleading empty result.
        variants_out = matched if matched else [_row(v) for v in rows[:10]]
        return {
            "total_gene_variants": data.get("total_count", 0),
            "matched": len(matched),
            "exact_match": bool(matched),
            "variants": variants_out[:10],
        }

    def _parse_gnomad(self, result: Any) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        # gnomad_get_gene nests the record under data.gene.
        gene = (result.get("data") or {}).get("gene") or {}
        if isinstance(gene, dict) and gene.get("gene_id"):
            return {
                "gene_id": gene.get("gene_id"),
                "symbol": gene.get("symbol"),
                "name": gene.get("name"),
                "chromosome": gene.get("chrom"),
                "canonical_transcript": gene.get("canonical_transcript_id"),
            }
        return {}

    def _parse_civic(self, result: Any, variant_token=None) -> Dict[str, Any]:
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        # civic_get_variants_by_gene returns data.gene.variants.nodes (a list).
        gene = (result.get("data") or {}).get("gene") or {}
        nodes = ((gene.get("variants") or {}) if isinstance(gene, dict) else {}).get(
            "nodes", []
        )
        nodes = nodes if isinstance(nodes, list) else []
        rows = [v for v in nodes if isinstance(v, dict)]

        def _row(v: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "name": v.get("name", v.get("variant_name", "")),
                "civic_id": v.get("id"),
                "feature": (v.get("feature") or {}).get("name")
                if isinstance(v.get("feature"), dict)
                else v.get("feature"),
            }

        # Fix-R51A-1: when variant_token is falsy (a gene-only query with no
        # specific variant to look for), the old "if variant_token and not
        # _title_matches(...): continue" filter never triggered a skip --
        # so EVERY gene-level variant silently counted as "matched" (e.g.
        # matched=8 out of 8 total for a bare {"gene": "MSH2"} call, wrongly
        # implying 8 real matches when no filtering criterion was even
        # applied). ClinVar's parser already got this right elsewhere in
        # this file (matched=0, gene-level rows shown separately as
        # unmatched context) -- mirror that same, correct shape here.
        matched = [
            _row(v)
            for v in rows
            if variant_token
            and _title_matches(v.get("name", v.get("variant_name", "")), variant_token)
        ]
        variants_out = matched if matched else [_row(v) for v in rows[:20]]
        return {
            "total_gene_variants": len(nodes),
            "matched": len(matched),
            "exact_match": bool(matched),
            "variants": variants_out[:20],
        }

    def _parse_uniprot(self, result: Any, gene: Optional[str] = None) -> Dict[str, Any]:
        # Fix-R31A-4: UniProt_search's "data" is a dict with a "results" list
        # (e.g. {"total_results": N, "results": [...]}), not itself a list --
        # confirmed live this always fell through to the raw-repr-string escape
        # hatch below, truncating mid-object. Field is also "gene_names" (a
        # list), not "gene_name".
        if not isinstance(result, dict):
            return {"raw": str(result)[:200]}
        data = result.get("data", {})
        results = data.get("results") if isinstance(data, dict) else None
        if isinstance(results, list) and results:
            entry = results[0]
            # Fix-R62A-2: blindly taking the top relevance hit silently
            # returned the WRONG gene's protein for gene-symbol families
            # sharing a name prefix -- confirmed live querying "GBA"
            # (glucocerebrosidase/Gaucher disease, HGNC-renamed to "GBA1" in
            # 2023) put "GBA3" (cytosolic beta-glucosidase, an unrelated
            # gene/enzyme) at position 0, with the correct gene only at
            # position 3 (still tagged with the legacy "GBA" symbol in that
            # UniProt entry's own gene_names). Prefer whichever fetched
            # entry's gene_names contains an exact case-insensitive match to
            # the queried gene; fall back to the top hit only when none does.
            if gene:
                gene_upper = gene.upper()
                exact = next(
                    (
                        r
                        for r in results
                        if gene_upper
                        in [g.upper() for g in (r.get("gene_names") or [])]
                    ),
                    None,
                )
                if exact:
                    entry = exact
            gene_names = entry.get("gene_names") or []
            return {
                "accession": entry.get("accession", ""),
                "protein_name": entry.get("protein_name", ""),
                "gene_name": gene_names[0] if gene_names else "",
                "function": str(entry.get("function", ""))[:300],
            }
        return {"raw": str(data)[:200]}

    def _build_summary(
        self,
        annotations: Dict[str, Any],
        variant: str = None,
        gene: str = None,
        rsid: str = None,
    ) -> Dict[str, Any]:
        # Reflect the identifier the caller actually queried: a variant or rsid
        # is more specific than the gene it was resolved to, so prefer them over
        # the (possibly rsid-derived) gene symbol -- otherwise an rsid-only query
        # mislabels summary.query as the gene (e.g. "BRCA2" for rs80358981).
        summary = {"query": variant or rsid or gene, "sources_with_data": []}

        # A source counts as "with data" only if it returned actual results — not
        # merely because the sub-call did not throw.
        def _has_data(source: str, d: Dict[str, Any]) -> bool:
            if not isinstance(d, dict) or d.get("raw"):
                return False
            if source == "clinvar":
                return bool(d.get("variants"))
            if source == "civic":
                return bool(d.get("variants"))
            if source == "gnomad":
                return bool(d.get("gene_id"))
            if source == "uniprot":
                return bool(d.get("accession"))
            return bool(d)

        for source, data in annotations.items():
            if _has_data(source, data):
                summary["sources_with_data"].append(source)

        clinvar = annotations.get("clinvar", {})
        # Fix-T2A-001: when the queried variant has no exact ClinVar match,
        # `variants` holds unrelated gene-level context (see _parse_clinvar's
        # fallback). Summarizing classifications[0] in that case silently
        # attributes an unrelated variant's classification to the query.
        if clinvar.get("exact_match") and clinvar.get("variants"):
            classifications = [
                v["classification"]
                for v in clinvar["variants"]
                if v.get("classification")
            ]
            if classifications:
                # Surface the MOST clinically significant classification, not the
                # first one listed. A multi-allelic match (e.g. rs80358981 =
                # c.7558C>G VUS + c.7558C>T Pathogenic) previously reported the
                # leading VUS and hid the Pathogenic allele -- a dangerous
                # mis-summary. When the matches disagree, also expose every
                # distinct classification so the curator sees the full picture.
                summary["clinvar_classification"] = min(
                    classifications, key=_clinvar_severity_key
                )
                distinct = list(dict.fromkeys(classifications))
                if len(distinct) > 1:
                    summary["clinvar_classifications"] = distinct
                    summary["clinvar_note"] = (
                        "Multiple ClinVar classifications matched the query "
                        "(e.g. a multi-allelic site); clinvar_classification "
                        "reports the most clinically significant. See "
                        "annotations.clinvar.variants for per-allele detail."
                    )
        elif clinvar.get("variants"):
            summary["clinvar_classification"] = None
            summary["clinvar_note"] = (
                "No exact ClinVar match for the queried variant; "
                "see annotations.clinvar.variants for unmatched gene-level context."
            )

        gnomad = annotations.get("gnomad", {})
        if gnomad.get("gene_id"):
            summary["gnomad_gene_id"] = gnomad["gene_id"]

        civic = annotations.get("civic", {})
        if civic.get("matched"):
            summary["civic_variants_matched"] = civic["matched"]

        return summary
