"""Compound tool: resolve one gene/protein identifier across namespaces in a single call.

Every ID-mapping tool in ToolUniverse requires the caller to already know which
namespace the input belongs to: ``UniProtIDMap_convert_ids`` needs ``from_db``,
``BridgeDb_xrefs`` needs a system code such as ``En`` or ``S``, and
``Ensembl_get_cross_references`` only accepts an Ensembl stable ID. That is the
step an agent holding a bare string like ``TP53`` or ``P04637`` cannot take.

This tool detects the namespace from the literal, routes to the resolvers that
accept it, and reconciles their answers into one cross-reference table where
every value carries the sources that support it.
"""

import re
from typing import Any, ClassVar

from .base_tool import BaseTool
from .tool_registry import register_tool


def _truncate_msg(msg: str, limit: int = 240) -> str:
    """Truncate an error message on a word boundary, never mid-word.

    Sub-tool errors carry the only actionable guidance a caller gets about a
    failed source; cutting one mid-word silently destroys that guidance.
    """
    if len(msg) <= limit:
        return msg
    return msg[:limit].rsplit(" ", 1)[0] + "..."


# Canonical namespaces this tool reports. Anything a source returns outside this
# set is dropped rather than guessed at, so a value's namespace label is always
# one this tool actually understands.
GENE_SYMBOL = "gene_symbol"
ENTREZ = "entrez_gene"
ENSEMBL_GENE = "ensembl_gene"
ENSEMBL_TRANSCRIPT = "ensembl_transcript"
ENSEMBL_PROTEIN = "ensembl_protein"
UNIPROT = "uniprot"
REFSEQ_RNA = "refseq_rna"
REFSEQ_PROTEIN = "refseq_protein"
HGNC = "hgnc"

NAMESPACES = (
    GENE_SYMBOL,
    ENTREZ,
    ENSEMBL_GENE,
    ENSEMBL_TRANSCRIPT,
    ENSEMBL_PROTEIN,
    UNIPROT,
    REFSEQ_RNA,
    REFSEQ_PROTEIN,
    HGNC,
)

# Ordered most-specific first: "P04637" matches the UniProt accession grammar and
# would also satisfy the permissive gene-symbol pattern, so UniProt must win.
_DETECTORS: list[tuple[str, "re.Pattern[str]", str]] = [
    (
        ENSEMBL_GENE,
        re.compile(r"^ENS(?:[A-Z]{3})?G\d{11}(?:\.\d+)?$", re.IGNORECASE),
        "high",
    ),
    (
        ENSEMBL_TRANSCRIPT,
        re.compile(r"^ENS(?:[A-Z]{3})?T\d{11}(?:\.\d+)?$", re.IGNORECASE),
        "high",
    ),
    (
        ENSEMBL_PROTEIN,
        re.compile(r"^ENS(?:[A-Z]{3})?P\d{11}(?:\.\d+)?$", re.IGNORECASE),
        "high",
    ),
    (HGNC, re.compile(r"^HGNC:\d+$", re.IGNORECASE), "high"),
    (REFSEQ_RNA, re.compile(r"^[NX][MR]_\d+(?:\.\d+)?$", re.IGNORECASE), "high"),
    (REFSEQ_PROTEIN, re.compile(r"^[NX]P_\d+(?:\.\d+)?$", re.IGNORECASE), "high"),
    (
        UNIPROT,
        re.compile(
            r"^(?:[OPQ]\d[A-Z0-9]{3}\d|[A-NR-Z]\d(?:[A-Z][A-Z0-9]{2}\d){1,2})(?:-\d+)?$"
        ),
        "high",
    ),
    (ENTREZ, re.compile(r"^\d+$"), "low"),
    (GENE_SYMBOL, re.compile(r"^[A-Za-z][A-Za-z0-9\-@_.]{0,30}$"), "medium"),
]

# from_db values for UniProtIDMap_convert_ids, per detected namespace.
_UNIPROT_FROM_DB = {
    GENE_SYMBOL: "Gene_Name",
    ENSEMBL_GENE: "Ensembl",
    ENSEMBL_TRANSCRIPT: "Ensembl_Transcript",
    ENSEMBL_PROTEIN: "Ensembl_Protein",
    ENTREZ: "GeneID",
    REFSEQ_RNA: "RefSeq_Nucleotide",
    REFSEQ_PROTEIN: "RefSeq_Protein",
    HGNC: "HGNC",
}

# BridgeDb system codes, per detected namespace. 'H' is the HGNC *symbol* space
# and 'Hac' the HGNC *accession* space: querying 'HGNC:11998' against 'H' is
# accepted and returns nothing, which would otherwise read as a source that
# succeeded and simply had no cross-references.
_BRIDGEDB_SOURCE = {
    ENSEMBL_GENE: "En",
    GENE_SYMBOL: "H",
    HGNC: "Hac",
    UNIPROT: "S",
    ENTREZ: "L",
}

# BridgeDb `database` labels -> canonical namespace. Labels outside this map
# (PDB, GeneOntology, Affy, ...) are deliberately ignored: they are real
# cross-references but not identifiers for the gene/protein itself.
_BRIDGEDB_DB = {
    "Ensembl": ENSEMBL_GENE,
    "Entrez Gene": ENTREZ,
    "HGNC": GENE_SYMBOL,
    "HGNC Accession number": HGNC,
    "Uniprot-TrEMBL": UNIPROT,
}

# Ensembl xref `dbname` -> (namespace of primary_id, namespace of display_id).
#
# The two fields hold different identifiers and neither is usable everywhere.
# The HGNC xref carries primary_id 'HGNC:11998' and display_id 'TP53', so
# reading one field for both namespaces files an accession as a gene symbol.
# Conversely Uniprot/SWISSPROT's display_id is the versioned 'P04637.312',
# which is not an accession any other resolver would return, so only its
# primary_id is taken. Uniprot_gn's primary_id is an arbitrary TrEMBL accession
# rather than the reviewed one, so only its display_id (the symbol) is used.
#
# Which dbnames appear depends on the feature level: a gene carries HGNC,
# EntrezGene and Uniprot_gn; a translation carries the UniProt and RefSeq
# peptide xrefs. Both sets are mapped here because this runs for either.
_ENSEMBL_DB = {
    "HGNC": (HGNC, GENE_SYMBOL),
    "EntrezGene": (ENTREZ, GENE_SYMBOL),
    "Uniprot_gn": (None, GENE_SYMBOL),
    "Uniprot/SWISSPROT": (UNIPROT, None),
    "Uniprot/SPTREMBL": (UNIPROT, None),
    "RefSeq_mRNA": (REFSEQ_RNA, None),
    "RefSeq_peptide": (REFSEQ_PROTEIN, None),
}

# g:Convert is asked for whichever of these two the input is not, so the call
# always returns something the input did not already state.
_GPROFILER_NAMESPACE = {ENSEMBL_GENE: "ENSG", UNIPROT: "UNIPROTSWISSPROT"}

# Species vocabularies differ per resolver: g:Profiler wants 'mmusculus' and
# BridgeDb wants 'Mouse'. Sending MyGene's 'mouse' to either is an HTTP 400 or a
# silent human-namespace lookup, so an unknown species skips those two sources
# with a stated reason rather than querying the wrong organism.
_SPECIES = {
    "human": ("hsapiens", "Human", 9606),
    "9606": ("hsapiens", "Human", 9606),
    "mouse": ("mmusculus", "Mouse", 10090),
    "10090": ("mmusculus", "Mouse", 10090),
    "rat": ("rnorvegicus", "Rat", 10116),
    "10116": ("rnorvegicus", "Rat", 10116),
    "zebrafish": ("drerio", "Zebrafish", 7955),
    "7955": ("drerio", "Zebrafish", 7955),
    "fruit fly": ("dmelanogaster", "Fruit fly", 7227),
    "7227": ("dmelanogaster", "Fruit fly", 7227),
    "worm": ("celegans", "Worm", 6239),
    "6239": ("celegans", "Worm", 6239),
    "yeast": ("scerevisiae", "Yeast", 4932),
    "4932": ("scerevisiae", "Yeast", 4932),
}

ALL_SOURCES = ("mygene", "uniprot_idmap", "gprofiler", "bridgedb", "ensembl_xrefs")


# Namespaces whose accessions carry an optional ``.<version>`` suffix that
# different resolvers disagree about: g:Profiler answers 'P04637.307', everyone
# else 'P04637'; MyGene answers 'NP_000537.3', Ensembl 'NP_000537'. Version is
# not part of the identity, and keeping both forms splits one identifier into
# two rows that each report half the agreement they earned.
_VERSIONED = frozenset(
    {
        ENSEMBL_GENE,
        ENSEMBL_TRANSCRIPT,
        ENSEMBL_PROTEIN,
        UNIPROT,
        REFSEQ_RNA,
        REFSEQ_PROTEIN,
    }
)

# A trailing '.<digits>'. Deliberately not '-<digits>': 'P04637-1' is a UniProt
# isoform, a different molecule, not a different version of the same one.
_VERSION_SUFFIX = re.compile(r"\.\d+$")

# An Ensembl stable ID names its own species: ENSMUSG is mouse, a plain ENSG is
# human. Defaulting such an input to human sends UniProt, g:Profiler and
# BridgeDb at the wrong organism, where they return nothing and report no
# failure — the answer simply arrives with less agreement behind it.
_ENSEMBL_SPECIES_PREFIX = re.compile(r"^ENS([A-Z]{3})?[GTP]\d{11}", re.IGNORECASE)
_ENSEMBL_SPECIES = {
    None: "human",
    "MUS": "mouse",
    "RNO": "rat",
    "DAR": "zebrafish",
}


def _drop_gprofiler_sentinel(value: Any) -> Any:
    """Turn g:Convert's literal 'None' string into a real absence."""
    return None if value is None or str(value).strip().lower() == "none" else value


def _empty_resolution_error(identifier: str, namespace: str, queried, failed) -> str:
    """Explain an empty result, distinguishing 'not found' from 'not answered'.

    Resolving nothing is a failed request, not a resolution to the empty set.
    Returned as a success it reads as an identifier that maps to nothing, and
    whether the resolvers looked and found nothing or never answered changes
    what that means entirely.
    """
    answered = set(queried) - {entry.split(":", 1)[0] for entry in failed}
    if answered:
        reason = (
            f"{len(answered)} resolver(s) answered and none holds it, so it is "
            f"probably not a current identifier in '{namespace}'. Check the "
            "spelling, or pass 'namespace' if it was detected wrongly."
        )
    else:
        reason = (
            "every resolver failed, so this is not evidence the identifier does "
            f"not exist: {'; '.join(failed)}"
        )
    return f"No identifiers resolved for '{identifier}' — {reason}"


def _species_from_identifier(identifier: str) -> tuple[str | None, str | None]:
    """Infer species from an Ensembl stable ID.

    Returns (species, unsupported_prefix). A prefix this tool has no resolver
    vocabulary for yields (None, prefix) so the caller can be told to name the
    species rather than silently getting human results.
    """
    match = _ENSEMBL_SPECIES_PREFIX.match(identifier.strip())
    if not match:
        return None, None
    prefix = match.group(1)
    prefix = prefix.upper() if prefix else None
    species = _ENSEMBL_SPECIES.get(prefix)
    return (species, None) if species else (None, prefix)


def _normalize_value(namespace: str, value: Any) -> str | None:
    """Canonicalize one reported value, or None when it carries no identifier.

    Two forms of the same identifier must collapse, or concordance counts the
    formatting rather than the agreement: MyGene reports HGNC as the bare
    ``11998`` and BridgeDb as ``HGNC:11998``, and version suffixes vary by
    resolver.
    """
    if namespace not in NAMESPACES or value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if namespace == HGNC and not text.upper().startswith("HGNC:"):
        text = f"HGNC:{text}"
    if namespace in _VERSIONED:
        text = _VERSION_SUFFIX.sub("", text)
    return text


@register_tool("CompoundIdentifierResolutionTool")
class CompoundIdentifierResolutionTool(BaseTool):
    """Detect an identifier's namespace and resolve it across the others."""

    # Caps, named so the slicing and the disclosure that restates what it cut
    # can never drift apart. BridgeDb alone returns ~600 xrefs for TP53.
    VALUES_PER_NAMESPACE = 10

    def __init__(self, tool_config: dict[str, Any], **kwargs):
        super().__init__(tool_config)

    # ------------------------------------------------------------------ detect

    @staticmethod
    def detect(identifier: str) -> tuple[str | None, str, list[str]]:
        """Return (namespace, confidence, alternatives) for a raw identifier."""
        matches = [
            (ns, conf) for ns, pat, conf in _DETECTORS if pat.match(identifier.strip())
        ]
        if not matches:
            return None, "none", []
        primary, confidence = matches[0]
        return primary, confidence, [ns for ns, _ in matches[1:]]

    # --------------------------------------------------------------------- run

    def run(self, arguments: dict[str, Any]) -> dict[str, Any]:
        raw = arguments.get("identifier")
        if not raw or not str(raw).strip():
            return {"status": "error", "error": "'identifier' is required."}
        identifier = str(raw).strip()

        override = arguments.get("namespace")
        if override and override not in NAMESPACES:
            return {
                "status": "error",
                "error": (
                    f"Unsupported namespace '{override}'. "
                    f"Supported: {', '.join(NAMESPACES)}."
                ),
            }

        detected, confidence, alternatives = self.detect(identifier)
        namespace = override or detected
        if not namespace:
            return {
                "status": "error",
                "error": (
                    f"Could not recognize '{identifier}' as a gene or protein "
                    "identifier. Pass 'namespace' explicitly, or use a "
                    "compound/ontology resolver instead — this tool covers "
                    f"{', '.join(NAMESPACES)} only."
                ),
            }

        requested_species = arguments.get("species")
        implied_species, unsupported_prefix = _species_from_identifier(identifier)
        species = requested_species or implied_species or "human"
        species_conflict = (
            implied_species
            if requested_species
            and implied_species
            and str(requested_species).lower() != implied_species
            else None
        )
        # UniProt ID mapping is not species-aware unless told: 'TP53' with no
        # taxon filter maps to a spread of vertebrate p53 accessions that need
        # not include the human one. Derive the taxon from species so an
        # explicit species is honoured, and let an explicit tax_id win.
        tax_id = arguments.get("tax_id")
        if tax_id is None:
            tax_id = (_SPECIES.get(str(species).lower()) or (None, None, None))[2]
        requested = arguments.get("sources") or list(ALL_SOURCES)
        unknown = [s for s in requested if s not in ALL_SOURCES]
        if unknown:
            return {
                "status": "error",
                "error": (
                    f"Unknown source(s): {', '.join(unknown)}. "
                    f"Available: {', '.join(ALL_SOURCES)}."
                ),
            }

        from .execute_function import ToolUniverse

        tu = ToolUniverse()
        tu.load_tools()

        sources_failed: list[str] = []
        sources_skipped: list[str] = []
        sources_queried: list[str] = []
        # namespace -> value -> {"sources": set, "order": int}
        found: dict[str, dict[str, dict[str, Any]]] = {ns: {} for ns in NAMESPACES}
        seen = 0

        def record(ns: str, value: Any, source: str) -> None:
            """Remember a reported value, keeping the position it first arrived at.

            Sources list their primary answer first: MyGene returns mouse Trp53 as
            ``[ENSMUSG00000059552, ENSMSIG00000025886]``, the reference assembly
            ahead of the other one. Both have one source, so without the arrival
            order a tie-break on the value itself puts ENSMSIG first and the tool
            answers with the wrong gene.
            """
            nonlocal seen
            text = _normalize_value(ns, value)
            if text is None:
                return
            entry = found[ns].setdefault(text, {"sources": set(), "order": seen})
            entry["sources"].add(source)
            seen += 1

        def note(source: str, reason: str) -> None:
            """Record a source withheld on purpose, and why.

            Kept apart from sources_failed: a withheld resolver was never called,
            so counting it as a failure would report more failures than calls.
            """
            sources_skipped.append(f"{source}: {reason}")

        def call(source: str, tool_name: str, args: dict[str, Any]) -> Any:
            sources_queried.append(source)
            try:
                r = tu.run_one_function({"name": tool_name, "arguments": args})
            except Exception as e:  # never propagate out of run()
                sources_failed.append(f"{source}: {_truncate_msg(str(e))}")
                return None
            if isinstance(r, dict) and r.get("status") == "error":
                sources_failed.append(
                    f"{source}: {_truncate_msg(str(r.get('error', 'unknown error')))}"
                )
                return None
            return r

        # Query on the canonical form. UniProt ID mapping rejects a versioned
        # identifier outright for RefSeq_Nucleotide and Ensembl — 'NM_000546.6'
        # comes back in failed_ids while 'NM_000546' resolves — so passing the
        # caller's literal through loses whole sources for no reason. The
        # original stays in query.identifier.
        query_id = _normalize_value(namespace, identifier) or identifier

        if "mygene" in requested:
            self._from_mygene(call, record, query_id, namespace, species)
        if "uniprot_idmap" in requested:
            self._from_uniprot(call, record, note, query_id, namespace, tax_id)
        if "gprofiler" in requested:
            self._from_gprofiler(call, record, note, query_id, namespace, species)
        if "bridgedb" in requested:
            self._from_bridgedb(call, record, note, query_id, namespace, species)
        if "ensembl_xrefs" in requested:
            self._from_ensembl(call, record, note, query_id, namespace)

        identifiers, truncated = self._rank(found)
        total = len(set(sources_queried))

        if not identifiers:
            return {
                "status": "error",
                "error": _empty_resolution_error(
                    identifier, namespace, sources_queried, sources_failed
                ),
            }

        # A withdrawn symbol resolves through MyGene's alias field, so the table
        # is headed by a symbol the caller did not type. Say so rather than
        # letting them assume their spelling is current.
        symbols = [row["value"] for row in identifiers.get(GENE_SYMBOL, [])]
        renamed_to = (
            symbols[0]
            if namespace == GENE_SYMBOL
            and symbols
            and identifier.lower() not in {s.lower() for s in symbols}
            else None
        )

        data: dict[str, Any] = {
            "query": {
                "identifier": identifier,
                "namespace_detected": detected,
                "namespace_used": namespace,
                "detection_confidence": "overridden" if override else confidence,
                "detection_alternatives": alternatives,
                "species": species,
            },
            "sources_queried": sorted(set(sources_queried)),
            "sources_failed": sources_failed,
            "sources_skipped": sources_skipped,
            "total_sources_queried": total,
            "identifiers": identifiers,
            "namespaces_truncated": truncated,
            "disclosure_notes": self._notes(
                identifiers,
                sources_failed,
                sources_skipped,
                truncated,
                confidence,
                alternatives,
                override,
                namespace,
                species_conflict,
                unsupported_prefix,
                renamed_to,
            ),
        }
        return {"status": "success", "data": data}

    # ----------------------------------------------------------------- sources

    def _from_mygene(self, call, record, identifier, namespace, species) -> None:
        """MyGene resolves nearly every namespace in one query; the workhorse."""
        fields = "symbol,entrezgene,ensembl.gene,uniprot,refseq,HGNC"
        if namespace in (ENTREZ, ENSEMBL_GENE):
            r = call(
                "mygene",
                "MyGene_get_gene_annotation",
                {"gene_id": identifier, "fields": fields},
            )
            hits = [r.get("data")] if isinstance(r, dict) and r.get("data") else []
        else:
            # Scope a symbol to the symbol and alias fields.
            #
            # Unscoped, "TP53" full-text matches paralogs like TP53TG3, whose
            # Entrez and Ensembl IDs are then reported as equivalents of the
            # queried gene — wrong answers, not merely noisy ones. But scoping to
            # `symbol` alone matches only the *current* symbol, so a withdrawn
            # one like SEPT9 or MARCH1 finds nothing and MyGene contributes no
            # Entrez or Ensembl at all. Both fields together resolve the rename
            # and still return a single gene for a current symbol.
            #
            # Quoted so a symbol containing Lucene syntax cannot change the query.
            query = (
                f'symbol:"{identifier}" OR alias:"{identifier}"'
                if namespace == GENE_SYMBOL
                else identifier
            )
            r = call(
                "mygene",
                "MyGene_query_genes",
                {
                    "query": query,
                    "species": species,
                    "fields": fields,
                    "size": 5,
                },
            )
            hits = (
                (r or {}).get("data", {}).get("hits", []) if isinstance(r, dict) else []
            )
        for hit in hits or []:
            if not isinstance(hit, dict):
                continue
            record(GENE_SYMBOL, hit.get("symbol"), "mygene")
            record(ENTREZ, hit.get("entrezgene"), "mygene")
            record(HGNC, hit.get("HGNC"), "mygene")
            ens = hit.get("ensembl")
            for item in ens if isinstance(ens, list) else [ens]:
                if isinstance(item, dict):
                    record(ENSEMBL_GENE, item.get("gene"), "mygene")
            uni = hit.get("uniprot")
            if isinstance(uni, dict):
                swiss = uni.get("Swiss-Prot")
                for v in swiss if isinstance(swiss, list) else [swiss]:
                    record(UNIPROT, v, "mygene")
            ref = hit.get("refseq")
            if isinstance(ref, dict):
                for key, ns in (("rna", REFSEQ_RNA), ("protein", REFSEQ_PROTEIN)):
                    vals = ref.get(key)
                    for v in vals if isinstance(vals, list) else [vals]:
                        record(ns, v, "mygene")

    def _from_uniprot(self, call, record, note, identifier, namespace, tax_id) -> None:
        if namespace == UNIPROT:
            # UniProt rejects a same-database mapping: UniProtKB_AC-ID ->
            # UniProtKB-Swiss-Prot returns the input in failed_ids. Calling it
            # anyway spends a job submission to learn nothing.
            note(
                "uniprot_idmap",
                "input is already a UniProt accession; UniProt ID Mapping "
                "rejects a UniProtKB-to-UniProtKB conversion",
            )
            return
        from_db = _UNIPROT_FROM_DB.get(namespace)
        if not from_db:
            note(
                "uniprot_idmap",
                f"UniProt ID Mapping has no source database for {namespace}",
            )
            return
        args: dict[str, Any] = {
            "ids": identifier,
            "from_db": from_db,
            "to_db": "UniProtKB-Swiss-Prot",
        }
        if tax_id is not None:
            args["tax_id"] = tax_id
        r = call("uniprot_idmap", "UniProtIDMap_convert_ids", args)
        for row in (
            (r or {}).get("data", {}).get("results", []) if isinstance(r, dict) else []
        ):
            if isinstance(row, dict):
                record(UNIPROT, row.get("to"), "uniprot_idmap")

    def _from_gprofiler(
        self, call, record, note, identifier, namespace, species
    ) -> None:
        """g:Convert detects its own input namespace, so it is a true second opinion."""
        organism = (_SPECIES.get(str(species).lower()) or (None,))[0]
        if organism is None:
            note(
                "gprofiler",
                f"no g:Profiler organism code known for species '{species}'; "
                "skipped rather than queried against the wrong organism",
            )
            return
        # Ask for whichever of the two the caller did not already supply.
        target_ns = UNIPROT if namespace == ENSEMBL_GENE else ENSEMBL_GENE
        args = {
            "gene_list": identifier,
            "target_namespace": _GPROFILER_NAMESPACE[target_ns],
            "organism": organism,
        }
        r = call("gprofiler", "gProfiler_convert_ids", args)
        for row in (r or {}).get("data", []) if isinstance(r, dict) else []:
            if not isinstance(row, dict):
                continue
            # g:Convert fills EVERY field of an unmapped row with the literal
            # string "None" — converted, name and description alike — so the
            # sentinel has to be rejected per field, not just on the conversion.
            record(
                target_ns, _drop_gprofiler_sentinel(row.get("converted")), "gprofiler"
            )
            record(GENE_SYMBOL, _drop_gprofiler_sentinel(row.get("name")), "gprofiler")

    def _from_bridgedb(
        self, call, record, note, identifier, namespace, species
    ) -> None:
        source = _BRIDGEDB_SOURCE.get(namespace)
        if not source:
            note("bridgedb", f"BridgeDb has no identifier space for {namespace}")
            return
        organism = (_SPECIES.get(str(species).lower()) or (None, None))[1]
        if organism is None:
            note(
                "bridgedb",
                f"no BridgeDb organism name known for species '{species}'; "
                "skipped rather than queried against human by default",
            )
            return
        r = call(
            "bridgedb",
            "BridgeDb_xrefs",
            {
                "operation": "xrefs",
                "identifier": identifier,
                "source": source,
                "organism": organism,
            },
        )
        rows = (
            (r or {}).get("data", {}).get("cross_references", [])
            if isinstance(r, dict)
            else []
        )
        for row in rows:
            if not isinstance(row, dict):
                continue
            ns = _BRIDGEDB_DB.get(row.get("database"))
            if ns:
                record(ns, row.get("identifier"), "bridgedb")

    def _from_ensembl(self, call, record, note, identifier, namespace) -> None:
        if namespace not in (ENSEMBL_GENE, ENSEMBL_TRANSCRIPT, ENSEMBL_PROTEIN):
            note(
                "ensembl_xrefs",
                f"Ensembl cross-references are keyed by Ensembl stable ID, "
                f"so a {namespace} input cannot be looked up there",
            )
            return
        r = call("ensembl_xrefs", "ensembl_get_xrefs", {"id": identifier})
        for row in (r or {}).get("data", []) if isinstance(r, dict) else []:
            if not isinstance(row, dict):
                continue
            mapping = _ENSEMBL_DB.get(row.get("dbname"))
            if not mapping:
                continue
            primary_ns, display_ns = mapping
            if primary_ns:
                record(primary_ns, row.get("primary_id"), "ensembl_xrefs")
            if display_ns:
                record(display_ns, row.get("display_id"), "ensembl_xrefs")

    # ------------------------------------------------------------------ output

    def _rank(self, found) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
        """Order each namespace by concordance, then by arrival, then cap.

        Arrival order is the tie-break rather than the value itself: sources put
        their primary answer first, and sorting equally-supported values
        alphabetically would promote whichever identifier happens to sort low.
        """
        out: dict[str, list[dict[str, Any]]] = {}
        truncated: list[str] = []
        for ns in NAMESPACES:
            values = found.get(ns) or {}
            if not values:
                continue
            ranked = sorted(
                (
                    {
                        "value": value,
                        "sources": sorted(entry["sources"]),
                        "concordance": len(entry["sources"]),
                        "_order": entry["order"],
                    }
                    for value, entry in values.items()
                ),
                key=lambda row: (-row["concordance"], row["_order"]),
            )
            for row in ranked:
                del row["_order"]
            if len(ranked) > self.VALUES_PER_NAMESPACE:
                truncated.append(ns)
            out[ns] = ranked[: self.VALUES_PER_NAMESPACE]
        return out, truncated

    # Why a namespace's grammar is not self-certifying, stated per namespace so
    # the caveat always describes the identifier actually passed in.
    _AMBIGUITY: ClassVar[dict[str, str]] = {
        ENTREZ: (
            "a bare integer is read as an Entrez Gene ID, but PubChem CIDs, "
            "taxonomy IDs and many other namespaces share that shape"
        ),
        GENE_SYMBOL: (
            "gene symbols are not unique across species and are frequently "
            "reassigned; aliases and withdrawn symbols resolve to the current gene"
        ),
    }

    def _notes(
        self,
        identifiers,
        sources_failed,
        sources_skipped,
        truncated,
        confidence,
        alternatives,
        override,
        namespace,
        species_conflict=None,
        unsupported_prefix=None,
        renamed_to=None,
    ) -> list[str]:
        """State every reason a reader could misread the table above."""
        notes: list[str] = [
            (
                "'concordance' counts the sources that reported a value, not evidence "
                "that the value is correct; a value only one source can return still "
                "has concordance 1 when it is right."
            )
        ]
        if sources_failed or sources_skipped:
            missing = len(sources_failed) + len(sources_skipped)
            where = " and ".join(
                part
                for part in (
                    f"'sources_failed' ({len(sources_failed)})"
                    if sources_failed
                    else "",
                    f"'sources_skipped' ({len(sources_skipped)})"
                    if sources_skipped
                    else "",
                )
                if part
            )
            notes.append(
                f"{missing} source(s) did not contribute; a value they alone would "
                "have supplied is missing, and concordance for the rest is "
                f"correspondingly lower. Read {where} before treating a low "
                "concordance as disagreement."
            )
        if not override and confidence in ("low", "medium"):
            reason = self._AMBIGUITY.get(namespace)
            notes.append(
                f"The input namespace was inferred as '{namespace}' with "
                f"{confidence} confidence"
                + (
                    f" (also matches: {', '.join(alternatives)})"
                    if alternatives
                    else ""
                )
                + (f" — {reason}" if reason else "")
                + ". Pass 'namespace' to remove the guess."
            )
        if truncated:
            notes.append(
                f"Namespace(s) {', '.join(truncated)} had more than "
                f"{self.VALUES_PER_NAMESPACE} distinct values and were cut to the "
                "highest-concordance ones; absence from this list is not evidence "
                "a value does not exist."
            )
        if len(identifiers.get(UNIPROT, [])) > 1:
            notes.append(
                "Multiple UniProt accessions are normal for one gene: BridgeDb "
                "reports TrEMBL isoforms alongside the reviewed Swiss-Prot entry. "
                "Prefer the accession that MyGene and UniProt agree on."
            )
        if species_conflict:
            notes.append(
                f"The identifier is an Ensembl ID for {species_conflict}, but "
                "'species' asked for something else, and the explicit request "
                "was honoured. The organism-specific resolvers were pointed at "
                "the requested species and will have found nothing there."
            )
        tied = [
            ns
            for ns, rows in identifiers.items()
            if len(rows) > 1
            and rows[0].get("concordance") == rows[1].get("concordance")
        ]
        if tied:
            notes.append(
                f"In {', '.join(tied)} the leading value is tied with the next on "
                "concordance, so the order between them carries no evidence — it "
                "is the order the sources happened to report. A pseudoautosomal "
                "gene really does have two equally valid Ensembl IDs. Treat the "
                "tied values as alternatives, not as first and second choice."
            )
        if renamed_to:
            notes.append(
                f"The queried symbol is not the current one; it resolved through "
                f"an alias to '{renamed_to}'. Downstream tools that key on the "
                "current symbol should use that."
            )
        if unsupported_prefix:
            notes.append(
                f"The Ensembl prefix 'ENS{unsupported_prefix}' names a species "
                "this tool has no resolver vocabulary for, so the lookup used "
                "the default. Pass 'species' to query the right organism — "
                f"supported: {', '.join(sorted(set(_ENSEMBL_SPECIES.values())))}."
            )
        return notes
