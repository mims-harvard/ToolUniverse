"""Compound tool: assemble a drug-target profile from several databases in one call.

Asking whether a gene is a viable target means asking five separate questions —
what is it, what does it do, where is it expressed, can it be drugged, and what
happens if you inhibit it — of tools keyed by three different identifiers.
OpenTargets' twenty target endpoints all take an Ensembl gene id, UniProt takes
an accession, and gnomAD takes a symbol. This resolves the target once and
returns the sections together.

Two of those answers are worth more when they are checked against each other
than when either is taken alone, so loss-of-function constraint is read from
both OpenTargets and gnomAD and the two are compared rather than merged.
"""

import re
from typing import Any

from .base_tool import BaseTool
from .tool_registry import register_tool


def _truncate_msg(msg: str, limit: int = 240) -> str:
    """Truncate an error message on a word boundary, never mid-word."""
    if len(msg) <= limit:
        return msg
    return msg[:limit].rsplit(" ", 1)[0] + "..."


SECTIONS = ("identity", "function", "expression", "tractability", "safety")

# Which sections read the shared OpenTargets target record and the UniProt
# accession, kept as data so the fetch decision and the documented cost cannot
# drift apart.
_NEEDS_TARGET_INFO = frozenset({"identity"})

# The expression endpoint pages at 250 by default and a target carries ~1400
# rows, so ranking the first page would present an arbitrary slice as the top
# tissues. 3000 is the documented maximum and fetches every row in one call.
_EXPRESSION_SIZE = 3000

# UniProt function prose carries its evidence inline, and for a well-studied
# protein the citations outweigh the biology: TP53's description is ~2600
# characters of which roughly half is "(PubMed:11025664, PubMed:12524540, ...)"
# repeated per clause. The claims are what a reader needs here; the accessions
# are still available from UniProt itself, and their removal is disclosed.
_CITATIONS = re.compile(r"\s*\((?:PubMed:\d+(?:,\s*)?)+\)")

# A human Ensembl gene id carries no species infix; ENSMUSG is mouse. OpenTargets
# curates human targets only and answers a non-human id with "no target" once per
# endpoint, so a mouse gene produced six failures and no explanation of why.
_HUMAN_ENSEMBL = re.compile(r"^ENSG\d+$", re.IGNORECASE)


def _is_human_ensembl(ensembl: str | None) -> bool:
    return bool(ensembl and _HUMAN_ENSEMBL.match(ensembl))


@register_tool("CompoundTargetProfileTool")
class CompoundTargetProfileTool(BaseTool):
    """Resolve a target once, then gather its profile from several databases."""

    # Caps, named so the slicing and the disclosure that restates what it cut
    # can never drift apart.
    TISSUES_PER_SOURCE = 8
    LIABILITIES_CAP = 15
    FUNCTION_CAP = 3

    def __init__(self, tool_config: dict[str, Any], **kwargs):
        super().__init__(tool_config)

    # --------------------------------------------------------------------- run

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw = arguments.get("target")
        if not raw or not str(raw).strip():
            return {"status": "error", "error": "'target' is required."}
        target = str(raw).strip()

        requested = arguments.get("sections")
        if requested is not None and not requested:
            return {
                "status": "error",
                "error": (
                    "'sections' was empty. Omit it for all sections, or name at "
                    f"least one of: {', '.join(SECTIONS)}."
                ),
            }
        sections = list(requested) if requested else list(SECTIONS)
        unknown = [s for s in sections if s not in SECTIONS]
        if unknown:
            return {
                "status": "error",
                "error": (
                    f"Unknown section(s): {', '.join(unknown)}. "
                    f"Available: {', '.join(SECTIONS)}."
                ),
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        failed: list[str] = []
        skipped: list[str] = []
        queried: list[str] = []

        def note(source: str, reason: str) -> None:
            skipped.append(f"{source}: {reason}")

        def call(source: str, tool_name: str, args: dict[str, Any]) -> Any:
            queried.append(source)
            try:
                r = tu.run_one_function({"name": tool_name, "arguments": args})
            except Exception as e:  # never propagate out of run()
                failed.append(f"{source}: {_truncate_msg(str(e))}")
                return None
            # Not every tool uses the {status, data} envelope: UniProt's function
            # endpoint answers with a bare list of strings, which must not be
            # mistaken for a failure.
            if isinstance(r, dict) and r.get("status") == "error":
                failed.append(
                    f"{source}: {_truncate_msg(str(r.get('error', 'unknown error')))}"
                )
                return None
            return r

        resolved = self._resolve(call, target, arguments.get("species") or "human")
        if not resolved["ensembl_gene"]:
            return {
                "status": "error",
                "error": (
                    f"Could not resolve '{target}' to an Ensembl gene id, which "
                    "every target endpoint is keyed by. Check the symbol, or pass "
                    "an Ensembl gene id directly."
                ),
            }

        data: dict[str, Any] = {
            "query": {"target": target, **resolved},
            "sources_queried": [],
            "sources_failed": failed,
            "sources_skipped": skipped,
        }

        wants = set(sections)
        ensembl = resolved["ensembl_gene"]
        human = _is_human_ensembl(ensembl)
        if not human:
            note(
                "opentargets",
                f"'{ensembl}' is not a human Ensembl gene id, and OpenTargets "
                "curates human targets only, so identity, expression, "
                "tractability and safety were not looked up there",
            )
        info = (
            self._target_info(call, ensembl)
            if human and wants & _NEEDS_TARGET_INFO
            else {}
        )

        if "identity" in sections:
            data["identity"] = self._identity(info, resolved)
        if "function" in sections:
            data["function"] = self._function(call, note, resolved["uniprot"])
        if "expression" in sections:
            data["expression"] = (
                self._expression(call, ensembl) if human else self._absent_expression()
            )
        if "tractability" in sections:
            data["tractability"] = (
                self._tractability(call, ensembl)
                if human
                else self._absent_tractability()
            )
        if "safety" in sections:
            data["safety"] = self._safety(
                call, note, ensembl, resolved["symbol"], human
            )

        data["sources_queried"] = sorted(set(queried))
        data["disclosure_notes"] = self._notes(data, sections)
        return {"status": "success", "data": data}

    # -------------------------------------------------------------- resolution

    def _resolve(self, call, target: str, species: str) -> dict[str, Any]:
        """Map the input to an Ensembl gene id, a UniProt accession and a symbol.

        Delegated to resolve_identifier_for_gene_or_protein rather than repeated
        here: it already detects the namespace, resolves withdrawn symbols
        through their aliases, and reports which sources agreed.

        Three resolvers, not two: with only MyGene and BridgeDb, SEPT9's two
        Ensembl ids tie at concordance 1 and arrival order picks
        ENSG00000282302, an alt contig OpenTargets does not hold, so every
        section then failed. g:Profiler breaks that tie onto the reference gene
        at no real cost. UniProt ID mapping is still left out because it submits
        a job and the ids are already covered.
        """
        r = call(
            "resolver",
            "resolve_identifier_for_gene_or_protein",
            {
                "identifier": target,
                "species": species,
                "sources": ["mygene", "bridgedb", "gprofiler"],
            },
        )
        ids = ((r or {}).get("data", {}) or {}).get("identifiers", {}) or {}

        def top(namespace):
            rows = ids.get(namespace) or []
            return rows[0]["value"] if rows else None

        return {
            "ensembl_gene": top("ensembl_gene"),
            "uniprot": top("uniprot"),
            "symbol": top("symbol") or top("gene_symbol"),
            "species": species,
        }

    # ---------------------------------------------------------------- sections

    def _target_info(self, call, ensembl: str) -> dict[str, Any]:
        r = call(
            "opentargets",
            "OpenTargets_get_target_info_by_ensemblID",
            {"ensemblId": ensembl},
        )
        return (((r or {}).get("data", {}) or {}).get("target") or {}) if r else {}

    def _identity(self, info: dict, resolved: dict) -> dict[str, Any]:
        location = info.get("genomicLocation") or {}
        return {
            "symbol": info.get("approvedSymbol") or resolved.get("symbol"),
            "name": info.get("approvedName"),
            "biotype": info.get("biotype"),
            "ensembl_gene": resolved.get("ensembl_gene"),
            "uniprot": resolved.get("uniprot"),
            "genomic_location": (
                {
                    "chromosome": location.get("chromosome"),
                    "start": location.get("start"),
                    "end": location.get("end"),
                    "strand": location.get("strand"),
                }
                if location
                else None
            ),
        }

    def _function(self, call, note, uniprot: str | None) -> dict[str, Any]:
        if not uniprot:
            note("uniprot", "function text is keyed by UniProt accession")
            return {
                "descriptions": [],
                "truncated": False,
                "pubmed_citations_removed": False,
            }
        r = call("uniprot", "UniProt_get_function_by_accession", {"accession": uniprot})
        # A bare list of strings, not the usual envelope.
        rows = r if isinstance(r, list) else []
        texts = []
        stripped_citations = False
        for x in rows:
            if not isinstance(x, str) or not x.strip():
                continue
            cleaned = _CITATIONS.sub("", x)
            if cleaned != x:
                stripped_citations = True
            texts.append(cleaned.strip())
        return {
            "descriptions": texts[: self.FUNCTION_CAP],
            "truncated": len(texts) > self.FUNCTION_CAP,
            "pubmed_citations_removed": stripped_citations,
        }

    def _expression(self, call, ensembl: str) -> dict[str, Any]:
        r = call(
            "opentargets",
            "OpenTargets_get_target_expression_by_ensemblID",
            {"ensemblId": ensembl, "size": _EXPRESSION_SIZE},
        )
        block = (((r or {}).get("data", {}) or {}).get("target", {}) or {}).get(
            "baselineExpression", {}
        ) or {}
        rows = block.get("rows") or []

        # Datasources are not comparable: GTEx reports bulk TPM and Tabula
        # Sapiens pseudobulk CPM, so a single ranking across both would order
        # different quantities against each other.
        by_source: dict[str, list] = {}
        without_tissue = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            tissue = (row.get("tissueBiosample") or {}).get("biosampleName")
            if not tissue:
                # Some rows carry no biosample at all — counted rather than
                # dropped silently, so rows_read still adds up.
                without_tissue += 1
                continue
            cell_type = (row.get("celltypeBiosample") or {}).get("biosampleName")
            by_source.setdefault(row.get("datasourceId") or "unknown", []).append(
                (tissue, row.get("median"), row.get("unit"), cell_type)
            )

        summary = {}
        for source, entries in by_source.items():
            ranked = sorted(entries, key=lambda e: (e[1] is None, -(e[1] or 0)))
            # A single-cell source reports one row per cell type within a tissue:
            # Tabula Sapiens gives TP53 1173 rows over 65 tissues, with aorta
            # appearing at 204, 28 and 0. Ranking the rows listed the same tissue
            # several times and read as a ranking of tissues, so each tissue is
            # kept once at its highest-expressing cell type, which is named.
            best: dict[str, tuple] = {}
            for tissue, median, _unit, cell_type in ranked:
                if tissue not in best:
                    best[tissue] = (median, cell_type)
            top = list(best.items())[: self.TISSUES_PER_SOURCE]
            summary[source] = {
                "unit": ranked[0][2] if ranked else None,
                "rows_measured": len(entries),
                "distinct_tissues": len(best),
                "highest_expression": [
                    {"tissue": t, "median": m, "cell_type": c} for t, (m, c) in top
                ],
            }
        return {
            "rows_total": block.get("count"),
            "rows_read": len(rows),
            "rows_without_tissue": without_tissue,
            "complete": not block.get("truncated", False),
            "by_datasource": summary,
        }

    @staticmethod
    def _absent_expression() -> dict[str, Any]:
        return {
            "rows_total": None,
            "rows_read": 0,
            "rows_without_tissue": 0,
            "complete": None,
            "by_datasource": {},
        }

    @staticmethod
    def _absent_tractability() -> dict[str, Any]:
        return {
            "assessments": None,
            "supported_by_modality": {},
            "modalities_with_evidence": [],
        }

    def _tractability(self, call, ensembl: str) -> dict[str, Any]:
        r = call(
            "opentargets",
            "OpenTargets_get_target_tractability_by_ensemblID",
            {"ensemblId": ensembl},
        )
        rows = (((r or {}).get("data", {}) or {}).get("target", {}) or {}).get(
            "tractability"
        ) or []
        # Rows are one assessment per (modality, label) with a boolean; only the
        # true ones say anything, and the modality is what a reader acts on.
        by_modality: dict[str, list] = {}
        assessed = 0
        for row in rows:
            if not isinstance(row, dict):
                continue
            assessed += 1
            if row.get("value") and row.get("label"):
                by_modality.setdefault(row.get("modality") or "unknown", []).append(
                    row["label"]
                )
        return {
            "assessments": assessed,
            "supported_by_modality": by_modality,
            "modalities_with_evidence": sorted(by_modality),
        }

    def _safety(
        self, call, note, ensembl: str, symbol: str | None, human: bool = True
    ) -> dict[str, Any]:
        r = (
            call(
                "opentargets",
                "OpenTargets_get_target_safety_profile_by_ensemblID",
                {"ensemblId": ensembl},
            )
            if human
            else None
        )
        # Tri-state: True answered, False called and failed, None not applicable.
        checked_liabilities = None if not human else r is not None
        rows = (((r or {}).get("data", {}) or {}).get("target", {}) or {}).get(
            "safetyLiabilities"
        ) or []
        named = [row for row in rows if isinstance(row, dict) and row.get("event")]
        liabilities = [{"event": row["event"]} for row in named[: self.LIABILITIES_CAP]]

        # Loss-of-function constraint from both curators. They read the same
        # gnomAD releases but not the same version, so the expected counts differ
        # and only gnomAD publishes pLI; comparing them is more informative than
        # quoting either alone.
        ot = (
            call(
                "opentargets",
                "OpenTargets_get_target_constraint_info_by_ensemblID",
                {"ensemblId": ensembl},
            )
            if human
            else None
        )
        ot_lof = None
        for row in (((ot or {}).get("data", {}) or {}).get("target", {}) or {}).get(
            "geneticConstraint"
        ) or []:
            if isinstance(row, dict) and row.get("constraintType") == "lof":
                ot_lof = {
                    "observed": row.get("obs"),
                    "expected": row.get("exp"),
                    "oe": row.get("oe"),
                    "oe_upper": row.get("oeUpper"),
                }

        gnomad_lof = None
        if symbol and human:
            g = call("gnomad", "gnomad_get_gene_constraints", {"gene_symbol": symbol})
            block = (((g or {}).get("data", {}) or {}).get("gene") or {}).get(
                "gnomad_constraint"
            ) or {}
            if block:
                gnomad_lof = {
                    "observed": block.get("obs_lof"),
                    "expected": block.get("exp_lof"),
                    "oe": block.get("oe_lof"),
                    "pLI": block.get("pLI"),
                }
        elif not human:
            note("gnomad", "constraint is published for human genes only")
        else:
            note("gnomad", "constraint is keyed by gene symbol")

        agreement = None
        if ot_lof and gnomad_lof:
            agreement = ot_lof.get("observed") == gnomad_lof.get("observed")

        return {
            "liabilities_checked": checked_liabilities,
            "safety_liabilities": liabilities,
            "liabilities_truncated": len(named) > len(liabilities),
            "lof_constraint_opentargets": ot_lof,
            "lof_constraint_gnomad": gnomad_lof,
            "sources_agree_on_observed_lof": agreement,
        }

    # ------------------------------------------------------------------ output

    def _notes(self, data: dict, sections) -> list[str]:
        """State every reason the profile above could be misread."""
        notes: list[str] = []

        expression = data.get("expression") or {}
        if expression.get("by_datasource"):
            notes.append(
                "Expression is ranked separately per datasource because the units "
                "are not comparable: GTEx reports bulk TPM and Tabula Sapiens "
                "pseudobulk CPM. A tissue high in one is not necessarily high in "
                "the other, and neither ranking is a statement about protein level."
            )
        cell_typed = [
            src
            for src, blk in (expression.get("by_datasource") or {}).items()
            if any(t.get("cell_type") for t in blk.get("highest_expression") or [])
        ]
        if cell_typed:
            notes.append(
                f"{', '.join(cell_typed)} measures one value per cell type within "
                "a tissue, so each tissue is listed once at its highest-expressing "
                "cell type, which is named. A high value there describes that cell "
                "type, not the tissue as a whole."
            )
        if expression.get("rows_without_tissue"):
            notes.append(
                f"{expression['rows_without_tissue']} of "
                f"{expression.get('rows_read')} expression rows name no tissue "
                "and are excluded from the rankings, which is why the per-source "
                "counts do not sum to rows_read."
            )
        if "expression" in sections and expression.get("complete") is False:
            notes.append(
                f"Only {expression.get('rows_read')} of "
                f"{expression.get('rows_total')} expression rows were read, so the "
                "highest-expressing tissues listed are the highest among those "
                "read, not necessarily overall."
            )

        tractability = data.get("tractability") or {}
        # assessments is None when the source does not cover this target, so
        # there is no assessment to characterise either way.
        if (
            "tractability" in sections
            and tractability.get("assessments") is not None
            and not tractability.get("modalities_with_evidence")
        ):
            notes.append(
                "No modality carries tractability evidence. That is the absence of "
                "a positive assessment, not an assessment that the target is "
                "undruggable."
            )

        safety = data.get("safety") or {}
        checked = safety.get("liabilities_checked")
        if "safety" in sections and checked is None:
            notes.append(
                "Liabilities and constraint were not looked up, because the "
                "curators consulted cover human targets only. The empty fields "
                "describe this tool's coverage, not the target."
            )
        elif "safety" in sections and checked is False:
            notes.append(
                "The safety-liability lookup did not answer, so the empty list "
                "says nothing about this target's liabilities."
            )
        elif "safety" in sections and not safety.get("safety_liabilities"):
            notes.append(
                "An empty liability list means OpenTargets curates none for this "
                "target, which is not evidence that inhibiting it is safe — most "
                "targets have no curated liability simply because none has been "
                "reported."
            )
        if safety.get("sources_agree_on_observed_lof") is False:
            notes.append(
                "OpenTargets and gnomAD report different observed loss-of-function "
                "counts, so they are reading different gnomAD releases. Prefer the "
                "one whose version you can pin, and treat the constraint as "
                "approximate."
            )
        if safety.get("lof_constraint_gnomad") and not safety.get(
            "lof_constraint_opentargets"
        ):
            notes.append(
                "Only gnomAD returned loss-of-function constraint, so there was no "
                "second opinion on it."
            )

        if data.get("sources_failed"):
            notes.append(
                f"{len(data['sources_failed'])} source(s) failed; the sections they "
                "feed are missing rather than empty. Read 'sources_failed' before "
                "reading an absent field as a negative finding."
            )
        return notes
