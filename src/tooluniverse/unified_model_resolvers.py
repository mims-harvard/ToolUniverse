"""Turn one canonical input into every representation the backends need.

This is the half of the unified interface that is *not* declarative, because
the work is real: the nine variant-effect models in ToolUniverse are keyed on
four mutually unconvertible coordinate systems. CADD and GeneBe want
``chrom/pos/ref/alt``; AlphaMissense wants a UniProt accession plus ``R175H``;
ESM-2 wants the actual protein sequence plus a 1-based residue index; SpliceAI
wants genomic HGVS. Converting between them is a lookup against real reference
data, not string manipulation, so a resolver does it once per call and every
backend reads from the shared result.

Two properties matter more than completeness here:

* **Resolution is best effort and says what it failed to do.** A backend whose
  representation is missing is *skipped with a reason* ("needs genomic
  coordinates; input was a protein change with no genomic mapping"), never
  called with a ``None`` that surfaces as an opaque upstream error.

* **Resolution pays for itself.** ``ProtVar_map_variant`` returns the UniProt
  mapping *and* AlphaMissense, EVE, ESM-1v, popEVE and CADD scores in one
  reply, and ``EnsemblVEP_annotate_hgvs`` returns the protein consequence *and*
  SIFT and PolyPhen. Those payloads are cached in the resolution context and
  read directly by the backends that declare ``from_context``, so seven of the
  variant-effect models cost two HTTP requests between them rather than seven.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Optional, Tuple

# 3-letter -> 1-letter. ProtVar and most protein databases speak 3-letter;
# ESM, AlphaMissense and the HGVS protein short form speak 1-letter.
_AA3_TO_1 = {
    "ALA": "A",
    "ARG": "R",
    "ASN": "N",
    "ASP": "D",
    "CYS": "C",
    "GLN": "Q",
    "GLU": "E",
    "GLY": "G",
    "HIS": "H",
    "ILE": "I",
    "LEU": "L",
    "LYS": "K",
    "MET": "M",
    "PHE": "F",
    "PRO": "P",
    "SER": "S",
    "THR": "T",
    "TRP": "W",
    "TYR": "Y",
    "VAL": "V",
    "TER": "*",
    "SEC": "U",
    "PYL": "O",
}
_STANDARD_AA = set("ACDEFGHIKLMNPQRSTVWY")

_HGVS_G_RE = re.compile(
    r"^(?:(?P<acc>[\w.]+):)?g\.(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)$",
    re.IGNORECASE,
)
_CHROM_PREFIXED_RE = re.compile(
    r"^(?:chr)?(?P<chrom>[\dXYMT]+):g?\.?(?P<pos>\d+)(?P<ref>[ACGT]+)>(?P<alt>[ACGT]+)$",
    re.IGNORECASE,
)
_PROTEIN_CHANGE_RE = re.compile(
    r"^p?\.?(?P<ref>[A-Z][a-z]{2}|[A-Z])(?P<pos>\d+)(?P<alt>[A-Z][a-z]{2}|[A-Z*])$"
)
_RSID_RE = re.compile(r"^rs\d+$", re.IGNORECASE)
# NCBI RefSeq chromosome accessions, GRCh38: NC_000001.11 .. NC_000024.10.
_REFSEQ_CHROM_RE = re.compile(r"^NC_0000(\d{2})\.\d+$", re.IGNORECASE)
_REFSEQ_NUM_TO_CHROM = {**{i: str(i) for i in range(1, 23)}, 23: "X", 24: "Y"}


class ResolutionError(Exception):
    """The canonical input could not be understood at all (as opposed to only
    partly resolved, which is normal and non-fatal)."""


def aa1(residue: Any) -> Optional[str]:
    """Normalize an amino acid to its 1-letter code."""
    if not residue:
        return None
    token = str(residue).strip()
    if len(token) == 1:
        return token.upper()
    return _AA3_TO_1.get(token.upper())


def _first_canonical(mappings: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Pick the isoform a caller means when they name a gene.

    ProtVar returns every isoform a genomic position touches -- for TP53 that
    is a dozen, most of them unreviewed TrEMBL fragments carrying no
    predictions at all. The reviewed canonical entry is the one whose scores
    are comparable across variants and the one every published benchmark uses,
    so prefer it explicitly and only fall back to position order.
    """
    for mapping in mappings:
        if mapping.get("canonical"):
            return mapping
    return mappings[0] if mappings else None


# --------------------------------------------------------------------------- #
# variant_effect
# --------------------------------------------------------------------------- #
def resolve_variant_effect(
    arguments: Dict[str, Any], call: Callable[[str, Dict[str, Any]], Any]
) -> Dict[str, Any]:
    """Canonical variant input -> genomic + protein + sequence representations.

    Accepts any one of: ``variant`` (free text -- HGVS, ``chr:pos ref>alt``, or
    an rsID), explicit ``chrom/pos/ref/alt``, ``rsid``, or a protein-level
    ``gene``/``uniprot`` plus ``protein_change``. A raw ``sequence`` plus
    ``position``/``mutant`` is also accepted and drives the sequence-only
    models without any database lookup.
    """
    resolved: Dict[str, Any] = {
        "task": "variant_effect",
        "genomic": {},
        "protein": {},
        "notes": [],
        "sources": [],
    }
    notes: List[str] = resolved["notes"]

    genomic = _parse_genomic_input(arguments)
    rsid = _clean(arguments.get("rsid"))
    protein_in = _parse_protein_input(arguments)
    sequence = _clean_sequence(arguments.get("sequence"))

    free = _clean(arguments.get("variant"))
    if free and not genomic and not rsid:
        parsed_genomic, parsed_rsid, parsed_protein = _parse_free_variant(free)
        genomic = genomic or parsed_genomic
        rsid = rsid or parsed_rsid
        if parsed_protein and not protein_in.get("position"):
            protein_in.update(parsed_protein)

    resolved["assembly"] = (
        _clean(arguments.get("assembly")) or _clean(arguments.get("genome")) or "GRCh38"
    )
    # MyVariant keys its store on UCSC build names and *defaults to hg19*.
    # Confirmed live: a GRCh38 coordinate sent without this returns HTTP 404,
    # which reads as "no such variant" rather than "wrong build" -- so the
    # build has to be stated explicitly on every call.
    resolved["ucsc_build"] = (
        "hg19"
        if "37" in resolved["assembly"] or "hg19" in resolved["assembly"].lower()
        else "hg38"
    )

    # An rsID pins nothing until it is looked up: resolve it to coordinates
    # first so that every downstream backend has something to work with.
    if rsid and not genomic:
        genomic = _genomic_from_rsid(rsid, call, notes, resolved)

    # A protein-level input with no coordinates: ProtVar maps in that direction
    # too, so try it before giving up on the coordinate-keyed backends.
    if (
        not genomic
        and protein_in.get("position")
        and (protein_in.get("uniprot") or protein_in.get("gene"))
    ):
        genomic = _genomic_from_protein(protein_in, call, notes, resolved)

    if genomic:
        resolved["genomic"] = genomic
        # A symmetric window around the variant for genome language models.
        # UCSC's start is 0-based and end is exclusive, so a 1-based position p
        # sits at index p-1; centring 512 bases either side gives the model
        # enough context without paying for a huge fetch.
        half = 512
        pos = genomic.get("pos") or 0
        if pos:
            resolved["dna_window_start"] = max(0, pos - 1 - half)
            resolved["dna_window_end"] = pos + half
            # Evo 2 takes a 1-based position *within the supplied window*.
            # Kept 1-based (never 0) so it cannot be mistaken for "absent" by
            # the falsy check in missing_requirements.
            resolved["evo2_position"] = pos - max(0, pos - 1 - half)
        resolved["hgvs_g"] = "{chrom}:g.{pos}{ref}>{alt}".format(**genomic)
        resolved["hgvs_g_chr"] = "chr{chrom}:g.{pos}{ref}>{alt}".format(**genomic)
        resolved["spdi_like"] = "{chrom} {pos} {ref} {alt}".format(**genomic)
        resolved["spdi_dash"] = "{chrom}-{pos}-{ref}-{alt}".format(**genomic)
    if rsid:
        resolved["rsid"] = rsid

    # ------------------------------------------------------------------ #
    # ProtVar: the protein mapping *and* five models' scores in one request.
    # ------------------------------------------------------------------ #
    if genomic:
        protvar = _call_protvar(resolved["spdi_like"], call, notes, resolved)
        if protvar:
            resolved["protvar"] = protvar
            mapping = _first_canonical(protvar.get("isoform_mappings") or [])
            if mapping:
                resolved["protvar_canonical"] = mapping
                protein_in.setdefault("uniprot", mapping.get("accession"))
                protein_in.setdefault("gene", mapping.get("gene"))
                protein_in.setdefault("position", mapping.get("position"))
                protein_in.setdefault("ref_aa", aa1(mapping.get("ref_aa")))
                protein_in.setdefault("alt_aa", aa1(mapping.get("alt_aa")))
                resolved["consequence"] = mapping.get("consequence")

    # ------------------------------------------------------------------ #
    # Ensembl VEP: transcript consequence plus SIFT and PolyPhen.
    # ------------------------------------------------------------------ #
    if resolved.get("hgvs_g"):
        vep = _call_vep(resolved["hgvs_g"], call, notes, resolved)
        if vep:
            resolved["vep"] = vep
            consequence = _pick_vep_consequence(vep)
            if consequence:
                resolved["vep_consequence"] = consequence
                protein_in.setdefault("gene", consequence.get("gene_symbol"))
                protein_in.setdefault("position", consequence.get("protein_start"))
                aas = str(consequence.get("amino_acids") or "")
                if "/" in aas:
                    ref_aa, alt_aa = aas.split("/", 1)
                    protein_in.setdefault("ref_aa", aa1(ref_aa))
                    protein_in.setdefault("alt_aa", aa1(alt_aa))
                resolved.setdefault(
                    "consequence", consequence.get("consequence_terms", [None])[0]
                )

    protein = {k: v for k, v in protein_in.items() if v is not None}
    if protein.get("position") and protein.get("ref_aa") and protein.get("alt_aa"):
        protein["variant"] = "{ref_aa}{position}{alt_aa}".format(**protein)
        protein["hgvs_p"] = "p.{ref_aa}{position}{alt_aa}".format(**protein)
    resolved["protein"] = protein

    # ------------------------------------------------------------------ #
    # Protein sequence -- required by the sequence-only models (ESM-2).
    # ------------------------------------------------------------------ #
    if not sequence and protein.get("uniprot"):
        sequence = _sequence_from_uniprot(protein["uniprot"], call, notes, resolved)
    if not sequence and protein.get("gene"):
        accession = _uniprot_from_gene(protein["gene"], call, notes, resolved)
        if accession:
            protein.setdefault("uniprot", accession)
            sequence = _sequence_from_uniprot(accession, call, notes, resolved)

    if sequence:
        resolved["sequence"] = sequence
        position = protein.get("position") or _as_int(arguments.get("position"))
        alt_aa = protein.get("alt_aa") or aa1(arguments.get("mutant"))
        if position and 1 <= position <= len(sequence):
            observed = sequence[position - 1]
            declared = protein.get("ref_aa")
            if declared and observed != declared:
                # A silent coordinate mismatch is the single most damaging
                # failure mode here: every sequence model would happily score
                # the wrong residue and return a confident number. Refuse the
                # sequence rather than let that through.
                notes.append(
                    f"Sequence/coordinate mismatch: {protein.get('uniprot')} has "
                    f"{observed} at position {position}, but the variant declares "
                    f"{declared}. Sequence-based backends were skipped; check the "
                    "isoform and coordinate build."
                )
                resolved.pop("sequence", None)
            else:
                resolved["seq_position"] = position
                resolved["seq_ref_aa"] = observed
                if alt_aa:
                    resolved["seq_alt_aa"] = alt_aa
                protein.setdefault("ref_aa", observed)
        elif position:
            notes.append(
                f"Position {position} is outside the {len(sequence)}-residue "
                "sequence; sequence-based backends were skipped."
            )
            resolved.pop("sequence", None)

    if not resolved.get("genomic") and not resolved.get("sequence") and not protein:
        raise ResolutionError(
            "Could not resolve the variant from the supplied arguments. Provide "
            "one of: 'variant' (HGVS such as '17:g.7676154G>A' or an rsID), "
            "'chrom'/'pos'/'ref'/'alt', 'rsid', 'gene' + 'protein_change' "
            "(e.g. gene='TP53', protein_change='R175H'), or 'sequence' + "
            "'position' + 'mutant'."
        )
    return resolved


# ----------------------------- input parsing ------------------------------- #
def _parse_genomic_input(arguments: Dict[str, Any]) -> Dict[str, Any]:
    chrom = _clean(
        arguments.get("chrom") or arguments.get("chromosome") or arguments.get("chr")
    )
    pos = _as_int(arguments.get("pos") or arguments.get("position_genomic"))
    ref = _clean(arguments.get("ref"))
    alt = _clean(arguments.get("alt"))
    if chrom and pos and ref and alt:
        return {
            "chrom": _normalize_chrom(chrom),
            "pos": pos,
            "ref": ref.upper(),
            "alt": alt.upper(),
        }
    return {}


def _parse_protein_input(arguments: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {
        "uniprot": _clean(arguments.get("uniprot") or arguments.get("uniprot_id")),
        "gene": _clean(arguments.get("gene") or arguments.get("gene_symbol")),
    }
    change = _clean(arguments.get("protein_change") or arguments.get("aa_change"))
    if change:
        match = _PROTEIN_CHANGE_RE.match(change.replace("p.", ""))
        if match:
            out["position"] = int(match.group("pos"))
            out["ref_aa"] = aa1(match.group("ref"))
            out["alt_aa"] = aa1(match.group("alt"))
    if "position" not in out and arguments.get("position") is not None:
        out["position"] = _as_int(arguments.get("position"))
        out["ref_aa"] = aa1(arguments.get("wild_type") or arguments.get("ref_aa"))
        out["alt_aa"] = aa1(arguments.get("mutant") or arguments.get("alt_aa"))
    return {k: v for k, v in out.items() if v is not None}


def _parse_free_variant(
    text: str,
) -> Tuple[Dict[str, Any], Optional[str], Dict[str, Any]]:
    """Recognize the handful of shapes people actually paste into a variant box."""
    token = text.strip()
    if _RSID_RE.match(token):
        return {}, token.lower(), {}

    # "17 7676154 G A" / "17-7676154-G-A" / "17,7676154,G,A"
    parts = re.split(r"[\s,\-]+", token)
    if len(parts) == 4 and parts[1].isdigit():
        return (
            {
                "chrom": _normalize_chrom(parts[0]),
                "pos": int(parts[1]),
                "ref": parts[2].upper(),
                "alt": parts[3].upper(),
            },
            None,
            {},
        )

    match = _CHROM_PREFIXED_RE.match(token)
    if match:
        return (
            {
                "chrom": _normalize_chrom(match.group("chrom")),
                "pos": int(match.group("pos")),
                "ref": match.group("ref").upper(),
                "alt": match.group("alt").upper(),
            },
            None,
            {},
        )

    match = _HGVS_G_RE.match(token)
    if match:
        chrom = None
        accession = match.group("acc")
        if accession:
            refseq = _REFSEQ_CHROM_RE.match(accession)
            if refseq:
                chrom = _REFSEQ_NUM_TO_CHROM.get(int(refseq.group(1)))
        if chrom:
            return (
                {
                    "chrom": chrom,
                    "pos": int(match.group("pos")),
                    "ref": match.group("ref").upper(),
                    "alt": match.group("alt").upper(),
                },
                None,
                {},
            )

    # "TP53 R175H" / "TP53 p.Arg175His"
    tokens = token.split()
    if len(tokens) == 2:
        change = _PROTEIN_CHANGE_RE.match(tokens[1].replace("p.", ""))
        if change:
            return (
                {},
                None,
                {
                    "gene": tokens[0].upper(),
                    "position": int(change.group("pos")),
                    "ref_aa": aa1(change.group("ref")),
                    "alt_aa": aa1(change.group("alt")),
                },
            )
    return {}, None, {}


# ------------------------------ sub-lookups -------------------------------- #
def _genomic_from_rsid(rsid, call, notes, resolved) -> Dict[str, Any]:
    payload = _retry(call, "EnsemblVEP_annotate_rsid", {"rsid": rsid})
    if not isinstance(payload, dict) or not payload.get("seq_region_name"):
        notes.append(
            f"Could not resolve {rsid} to genomic coordinates via Ensembl VEP."
        )
        return {}
    resolved["sources"].append("EnsemblVEP_annotate_rsid")
    alleles = str(payload.get("allele_string") or "").split("/")
    if len(alleles) < 2:
        notes.append(f"{rsid} returned no usable allele string.")
        return {}
    ref = alleles[0].upper()
    # A multi-allelic rsID names several alternates; without an explicit choice
    # the first is the only defensible pick, and saying so beats guessing
    # silently.
    alt = alleles[1].upper()
    if len(alleles) > 2:
        notes.append(
            f"{rsid} is multi-allelic ({payload.get('allele_string')}); scored the "
            f"first alternate allele ({alt}). Pass explicit chrom/pos/ref/alt to "
            "score a different one."
        )
    return {
        "chrom": _normalize_chrom(payload.get("seq_region_name")),
        "pos": _as_int(payload.get("start")),
        "ref": ref,
        "alt": alt,
    }


def _genomic_from_protein(protein, call, notes, resolved) -> Dict[str, Any]:
    accession = protein.get("uniprot")
    if not accession and protein.get("gene"):
        accession = _uniprot_from_gene(protein["gene"], call, notes, resolved)
        if accession:
            protein["uniprot"] = accession
    if not accession:
        return {}
    change = "{}{}{}".format(
        protein.get("ref_aa") or "",
        protein.get("position"),
        protein.get("alt_aa") or "",
    )
    payload = _unwrap(call("ProtVar_map_variant", {"variant": f"{accession} {change}"}))
    if not isinstance(payload, dict):
        notes.append(
            f"ProtVar could not map {accession} {change} to genomic coordinates; "
            "coordinate-keyed backends were skipped."
        )
        return {}
    resolved["sources"].append("ProtVar_map_variant")
    coords = payload.get("genomic_coordinates") or {}
    if not coords.get("pos"):
        notes.append(
            f"ProtVar returned no genomic coordinates for {accession} {change} "
            "(a protein change can map to several codons); coordinate-keyed "
            "backends were skipped."
        )
        return {}
    resolved["protvar"] = payload
    return {
        "chrom": _normalize_chrom(coords.get("chr")),
        "pos": _as_int(coords.get("pos")),
        "ref": str(coords.get("ref") or "").upper(),
        "alt": str(coords.get("alt") or "").upper(),
    }


def _call_protvar(spdi_like, call, notes, resolved) -> Optional[Dict[str, Any]]:
    if isinstance(resolved.get("protvar"), dict):
        return resolved["protvar"]
    payload = _unwrap(call("ProtVar_map_variant", {"variant": spdi_like}))
    if not isinstance(payload, dict) or not payload.get("isoform_mappings"):
        notes.append(
            "ProtVar returned no isoform mapping; AlphaMissense, EVE, ESM-1v, "
            "popEVE and ProtVar's CADD were unavailable for this variant."
        )
        return None
    resolved["sources"].append("ProtVar_map_variant")
    return payload


def _call_vep(hgvs_g, call, notes, resolved) -> Optional[Dict[str, Any]]:
    payload = _retry(call, "EnsemblVEP_annotate_hgvs", {"hgvs_notation": hgvs_g})
    if not isinstance(payload, dict):
        notes.append(
            "Ensembl VEP returned no annotation; SIFT and PolyPhen were unavailable."
        )
        return None
    resolved["sources"].append("EnsemblVEP_annotate_hgvs")
    return payload


def _pick_vep_consequence(vep: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Choose one transcript from VEP's per-transcript list.

    VEP reports every overlapping transcript, and their SIFT/PolyPhen scores
    genuinely differ (0.13 vs 0.14 for the same substitution on two TP53
    transcripts). Prefer the MANE Select / canonical transcript so the number
    is reproducible and matches what a clinical report would quote, and fall
    back to the first protein-coding entry that actually carries a protein
    consequence.
    """
    consequences = vep.get("transcript_consequences") or []
    if not consequences:
        return None
    for key in ("mane_select", "canonical"):
        for entry in consequences:
            if entry.get(key):
                return entry
    for entry in consequences:
        if entry.get("biotype") == "protein_coding" and entry.get("protein_start"):
            return entry
    return consequences[0]


def _uniprot_from_gene(gene, call, notes, resolved) -> Optional[str]:
    payload = _unwrap(
        call(
            "UniProtIDMap_gene_to_uniprot",
            # gene_names is a *string* here, not a list: the tool's schema
            # rejects a list outright ("['TP53'] is not of type 'string'"),
            # which surfaced as "could not map gene TP53" -- a resolution
            # failure that looked like a missing gene rather than a bad call.
            {"gene_names": gene, "tax_id": "9606", "reviewed_only": True},
        )
    )
    accession = _find_first_accession(payload)
    if not accession:
        notes.append(f"Could not map gene {gene} to a reviewed UniProt accession.")
        return None
    resolved["sources"].append("UniProtIDMap_gene_to_uniprot")
    return accession


def _find_first_accession(payload: Any) -> Optional[str]:
    """Dig an accession out of whatever shape the ID-mapping tool returned.

    ID-mapping replies vary by tool version (``results`` list, ``mappings``
    dict, bare dict keyed by gene), and a resolver that hard-codes one of them
    breaks silently on the others -- as a missing accession, which looks like
    "no such gene" rather than "we did not read the reply".
    """
    accession_re = re.compile(
        r"^[OPQ][0-9][A-Z0-9]{3}[0-9]$|^[A-NR-Z][0-9](?:[A-Z][A-Z0-9]{2}[0-9]){1,2}$"
    )

    def walk(node: Any) -> Optional[str]:
        if isinstance(node, str):
            return node if accession_re.match(node) else None
        if isinstance(node, dict):
            for key in ("accession", "to", "uniprot", "primaryAccession", "uniprot_id"):
                found = walk(node.get(key))
                if found:
                    return found
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        if isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    return walk(payload)


def _sequence_from_uniprot(accession, call, notes, resolved) -> Optional[str]:
    payload = _unwrap(
        call("UniProt_get_sequence_by_accession", {"accession": accession})
    )
    sequence = None
    if isinstance(payload, str):
        sequence = payload
    elif isinstance(payload, dict):
        for key in ("sequence", "value", "seq"):
            candidate = payload.get(key)
            if isinstance(candidate, str):
                sequence = candidate
                break
            if isinstance(candidate, dict) and isinstance(candidate.get("value"), str):
                sequence = candidate["value"]
                break
    sequence = _clean_sequence(sequence)
    if not sequence:
        notes.append(
            f"Could not fetch the canonical sequence for {accession}; "
            "sequence-based backends were skipped."
        )
        return None
    resolved["sources"].append("UniProt_get_sequence_by_accession")
    return sequence


# --------------------------------------------------------------------------- #
# structure_prediction
# --------------------------------------------------------------------------- #
def resolve_structure_prediction(
    arguments: Dict[str, Any], call: Callable[[str, Dict[str, Any]], Any]
) -> Dict[str, Any]:
    """Canonical folding input -> sequence(s) plus optional ligand.

    Accepts a raw ``sequence``, a ``uniprot`` accession, or a ``gene`` symbol;
    ``sequences`` (a list) requests a complex, and ``ligand_smiles`` requests
    co-folding, both of which only some backends support.
    """
    resolved: Dict[str, Any] = {
        "task": "structure_prediction",
        "notes": [],
        "sources": [],
    }
    notes: List[str] = resolved["notes"]

    sequences = arguments.get("sequences")
    if isinstance(sequences, str):
        sequences = [sequences]
    sequences = [_clean_sequence(s) for s in (sequences or [])]
    sequences = [s for s in sequences if s]

    single = _clean_sequence(arguments.get("sequence"))
    if single:
        sequences.insert(0, single)

    accession = _clean(arguments.get("uniprot") or arguments.get("uniprot_id"))
    gene = _clean(arguments.get("gene") or arguments.get("gene_symbol"))
    if not sequences and gene and not accession:
        accession = _uniprot_from_gene(gene, call, notes, resolved)
    if not sequences and accession:
        fetched = _sequence_from_uniprot(accession, call, notes, resolved)
        if fetched:
            sequences = [fetched]

    if not sequences:
        raise ResolutionError(
            "No protein sequence to fold. Provide 'sequence' (1-letter amino "
            "acids), 'sequences' (a list, for a complex), 'uniprot', or 'gene'."
        )

    invalid = sorted(set("".join(sequences)) - _STANDARD_AA - set("XBZUO"))
    if invalid:
        raise ResolutionError(
            f"Sequence contains non-amino-acid characters: {invalid}. Provide a "
            "1-letter protein sequence."
        )

    # OpenFold3 takes a nested per-molecule spec rather than a flat sequence
    # list, and Boltz-2 takes yet another shape. Building them here keeps the
    # registry declarative instead of teaching the templating engine to map
    # over lists.
    # OpenFold3 refuses a protein without an MSA, and its own error names the
    # escape hatch: "an MSA consisting of only the query sequence". That is
    # what is sent here, which makes the model runnable but strips it of the
    # evolutionary signal MSA-based folders depend on -- expect markedly lower
    # accuracy than AlphaFold2/OpenFold2 with a real alignment. The measured
    # lDDT will show exactly how much that costs. Use NvidiaNIM_msa_search to
    # build a real alignment when accuracy matters.
    resolved["of3_molecules"] = [
        {
            "type": "protein",
            "sequence": seq,
            "msa": {
                "uniref90": {"a3m": {"alignment": f">query\n{seq}", "format": "a3m"}}
            },
        }
        for seq in sequences
    ]
    resolved.update(
        {
            "sequence": sequences[0],
            "sequences": sequences,
            "n_chains": len(sequences),
            "length": len(sequences[0]),
            "total_length": sum(len(s) for s in sequences),
            "uniprot": accession,
            "gene": gene,
            "is_complex": len(sequences) > 1,
        }
    )
    ligand = _clean(arguments.get("ligand_smiles"))
    if ligand:
        resolved["ligand_smiles"] = ligand
        resolved["is_cofolding"] = True

    # An experimental reference turns pLDDT (the model's self-reported
    # confidence) into lDDT (measured accuracy). Without one, folders can only
    # be ranked on how sure they sound, which rewards the confidently wrong.
    reference = _clean(arguments.get("reference_pdb_id"))
    if reference:
        structure = _fetch_pdb_text(reference, notes)
        if structure:
            resolved["reference_structure"] = structure
            resolved["reference_pdb_id"] = reference.upper()
    elif _clean(arguments.get("reference_structure")):
        resolved["reference_structure"] = arguments["reference_structure"]
    return resolved


# --------------------------------------------------------------------------- #
# molecular_property
# --------------------------------------------------------------------------- #
def resolve_molecular_property(
    arguments: Dict[str, Any], call: Callable[[str, Dict[str, Any]], Any]
) -> Dict[str, Any]:
    """Canonical ADMET input -> SMILES plus the requested canonical property.

    The ``property`` argument is a ToolUniverse-canonical id (``bbb_penetration``,
    ``herg_inhibition``, ...). Each backend's own field name for that property
    lives in its registry entry, which is what lets ADMET-AI's
    ``BBB_Martins`` and SwissADME's ``BBB permeant`` be read as one quantity.
    """
    resolved: Dict[str, Any] = {
        "task": "molecular_property",
        "notes": [],
        "sources": [],
    }

    smiles = _clean(arguments.get("smiles") or arguments.get("SMILES"))
    if not smiles:
        name = _clean(
            arguments.get("drug") or arguments.get("compound") or arguments.get("name")
        )
        if name:
            smiles = _smiles_from_name(name, call, resolved)
    if not smiles:
        raise ResolutionError(
            "No structure to predict on. Provide 'smiles', or a 'drug'/'compound' "
            "name that can be resolved to one."
        )

    prop = _clean(arguments.get("property"))
    if not prop:
        raise ResolutionError(
            "No 'property' requested. Call the task's list endpoint to see the "
            "canonical property ids this task supports."
        )

    resolved.update({"smiles": smiles, "property": prop.lower().strip()})
    return resolved


def _smiles_from_name(name, call, resolved) -> Optional[str]:
    """Resolve a compound name to SMILES via PubChem.

    Both lookups are searched recursively rather than by flat key, because
    PubChem nests its answers and renames its fields. Confirmed live: the CID
    arrives at ``data.IdentifierList.CID[0]`` and the structure at
    ``data.PropertyTable.Properties[0].ConnectivitySMILES`` -- note
    *Connectivity*, not the ``CanonicalSMILES`` this code originally looked
    for, which PubChem retired. A flat-key lookup found neither, so every
    ``drug``/``ligand`` name silently resolved to nothing and surfaced as "No
    structure to predict on" -- indistinguishable from the caller having
    supplied no molecule at all.
    """
    payload = _unwrap(call("PubChem_get_CID_by_compound_name", {"name": name}))
    cid = _find_cid(payload)
    if not cid:
        resolved["notes"].append(
            f"Could not resolve compound name {name!r} to a PubChem CID."
        )
        return None

    props = _unwrap(call("PubChem_get_compound_properties_by_CID", {"cid": int(cid)}))
    smiles = _find_smiles(props)
    if smiles:
        resolved["sources"].append("PubChem")
        resolved["notes"].append(f"Resolved {name!r} to PubChem CID {cid}.")
    else:
        resolved["notes"].append(
            f"PubChem returned no structure for {name!r} (CID {cid})."
        )
    return _clean(smiles)


def _find_cid(payload: Any) -> Optional[int]:
    """First PubChem CID anywhere in the reply."""

    def walk(node: Any) -> Optional[int]:
        if isinstance(node, bool):
            return None
        if isinstance(node, int):
            return node
        if isinstance(node, str) and node.isdigit():
            return int(node)
        if isinstance(node, dict):
            for key in ("CID", "cid", "cids"):
                if key in node:
                    found = walk(node[key])
                    if found:
                        return found
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        if isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    return walk(payload)


# PubChem's SMILES field names, current first. "ConnectivitySMILES" replaced
# "CanonicalSMILES"; "SMILES" is what the older PUG REST paths return.
_SMILES_KEYS = (
    "ConnectivitySMILES",
    "CanonicalSMILES",
    "IsomericSMILES",
    "SMILES",
    "smiles",
    "canonical_smiles",
)


def _find_smiles(payload: Any) -> Optional[str]:
    def walk(node: Any) -> Optional[str]:
        if isinstance(node, dict):
            for key in _SMILES_KEYS:
                value = node.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            for value in node.values():
                found = walk(value)
                if found:
                    return found
        if isinstance(node, list):
            for item in node:
                found = walk(item)
                if found:
                    return found
        return None

    return walk(payload)


# --------------------------------------------------------------------------- #
# binding_affinity
# --------------------------------------------------------------------------- #
def resolve_binding_affinity(
    arguments: Dict[str, Any], call: Callable[[str, Dict[str, Any]], Any]
) -> Dict[str, Any]:
    """Canonical docking input -> receptor (sequence and/or PDB id) + ligand SMILES."""
    resolved: Dict[str, Any] = {"task": "binding_affinity", "notes": [], "sources": []}
    notes: List[str] = resolved["notes"]

    ligand = _clean(arguments.get("ligand_smiles") or arguments.get("smiles"))
    if not ligand:
        name = _clean(arguments.get("ligand") or arguments.get("compound"))
        if name:
            ligand = _smiles_from_name(name, call, resolved)
    if not ligand:
        raise ResolutionError(
            "No ligand. Provide 'ligand_smiles' (or a 'ligand' name resolvable "
            "to SMILES)."
        )

    pdb_id = _clean(arguments.get("pdb_id"))
    sequence = _clean_sequence(
        arguments.get("protein_sequence") or arguments.get("sequence")
    )
    accession = _clean(arguments.get("uniprot") or arguments.get("uniprot_id"))
    gene = _clean(arguments.get("target") or arguments.get("gene"))

    if not sequence and not pdb_id:
        if not accession and gene:
            accession = _uniprot_from_gene(gene, call, notes, resolved)
        if accession:
            sequence = _sequence_from_uniprot(accession, call, notes, resolved)

    if not sequence and not pdb_id:
        raise ResolutionError(
            "No receptor. Provide 'protein_sequence', 'pdb_id', 'uniprot', or a "
            "'target' gene symbol."
        )

    resolved.update(
        {
            "ligand_smiles": ligand,
            "protein_sequence": sequence,
            "pdb_id": pdb_id,
            "uniprot": accession,
            "gene": gene,
        }
    )

    # Pose-prediction backends take *files*, not identifiers: DiffDock wants
    # receptor PDB text and a 3D ligand SDF. Without these two keys the
    # backend can never satisfy its own `needs` and is skipped on every call
    # -- which looked like "no API key" rather than "this is wired wrong",
    # because the key check runs first and masked it.
    if pdb_id:
        structure = _fetch_pdb_text(pdb_id, notes)
        if structure:
            resolved["protein_structure"] = structure
    sdf = _smiles_to_sdf(ligand, notes)
    if sdf:
        resolved["ligand_sdf"] = sdf
    return resolved


def _fetch_pdb_text(pdb_id: str, notes: List[str]) -> Optional[str]:
    """Receptor coordinates as PDB text, straight from RCSB's file service.

    No ToolUniverse tool returns raw coordinates -- the RCSB/PDBe tools here
    all return metadata -- so this goes to the canonical file endpoint
    directly, the same way the dataset loaders fetch their sources.
    """
    import re as _re

    if not _re.fullmatch(r"[0-9A-Za-z]{4}", pdb_id or ""):
        notes.append(
            f"{pdb_id!r} is not a 4-character PDB id; structure-based docking "
            "backends were skipped."
        )
        return None
    try:
        import requests

        response = requests.get(
            f"https://files.rcsb.org/download/{pdb_id.upper()}.pdb",
            timeout=90,
            headers={"User-Agent": "ToolUniverse/unified-models"},
        )
        response.raise_for_status()
        text = response.text
    except Exception as exc:
        notes.append(f"Could not fetch PDB {pdb_id} coordinates from RCSB: {exc}")
        return None
    if "ATOM" not in text:
        notes.append(f"RCSB returned no ATOM records for {pdb_id}.")
        return None
    return text


def _smiles_to_sdf(smiles: str, notes: List[str]) -> Optional[str]:
    """A 3D ligand SDF from SMILES.

    Docking needs a conformer, not a graph, so the molecule is embedded and
    minimized rather than merely parsed. RDKit is an optional dependency, so a
    missing install degrades to skipping the SDF-based backends with a reason
    instead of raising.
    """
    try:
        from rdkit import Chem
        from rdkit.Chem import AllChem
    except ImportError:
        notes.append(
            "RDKit is not installed, so no 3D ligand conformer could be built; "
            "SDF-based docking backends were skipped. Install with "
            "'pip install tooluniverse[ml]'."
        )
        return None
    try:
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            notes.append(f"RDKit could not parse the ligand SMILES {smiles!r}.")
            return None
        mol = Chem.AddHs(mol)
        # A fixed seed keeps the conformer -- and therefore the docking score
        # computed from it -- reproducible between runs.
        if AllChem.EmbedMolecule(mol, randomSeed=0xF00D) != 0:
            notes.append(f"RDKit could not embed a 3D conformer for {smiles!r}.")
            return None
        AllChem.MMFFOptimizeMolecule(mol)
        return Chem.MolToMolBlock(mol)
    except Exception as exc:
        notes.append(f"Could not build a 3D ligand conformer: {exc}")
        return None


# --------------------------------------------------------------------------- #
# shared helpers
# --------------------------------------------------------------------------- #
RESOLVERS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "variant_effect": resolve_variant_effect,
    "structure_prediction": resolve_structure_prediction,
    "molecular_property": resolve_molecular_property,
    "binding_affinity": resolve_binding_affinity,
}


# --------------------------------------------------------------------------- #
# Lazily fetched shared payloads
# --------------------------------------------------------------------------- #
# Some payloads answer several backends at once but are not needed to resolve
# the input itself, so fetching them during resolution would tax every caller
# for data most of them never read. They are declared here instead and pulled
# on demand, once, only when a selected backend asks for them.
CONTEXT_PROVIDERS: Dict[str, Dict[str, Dict[str, Any]]] = {
    "variant_effect": {
        # Genome foundation models (Evo 2) read DNA, not a protein change, so
        # they need a reference window centred on the variant -- something no
        # other backend here wants. Fetched only when one of them is selected.
        "dna_window": {
            "tool": "UCSC_get_sequence",
            "args": {
                "genome": "{ucsc_build}",
                "chrom": "chr{genomic.chrom}",
                "start": "{dna_window_start}",
                "end": "{dna_window_end}",
            },
            "needs": ["genomic.pos", "dna_window_start"],
            "serves": "Evo 2",
        },
        # FAVOR returns several independent predictors in one keyless call --
        # MutationAssessor, MutationTaster, MetaSVM and LINSIGHT -- the same
        # free-lunch pattern as ProtVar and dbNSFP. Fetched only when one of
        # them is selected.
        "favor": {
            "tool": "FAVOR_annotate_variant",
            "args": {"variant": "{spdi_dash}"},
            "needs": ["spdi_dash"],
            "serves": "MutationAssessor, MutationTaster, MetaSVM and LINSIGHT",
        },
        "dbnsfp": {
            "tool": "MyVariant_get_pathogenicity_scores",
            "args": {"variant_id": "{hgvs_g_chr}", "assembly": "{ucsc_build}"},
            "needs": ["hgvs_g_chr"],
            "serves": "REVEL, VEST4 and MetaRNN",
        },
    }
}


def ensure_context(
    resolved: Dict[str, Any],
    key: str,
    call: Callable[[str, Dict[str, Any]], Any],
) -> Optional[Any]:
    """Fetch a shared payload once, memoized into the resolution context.

    Returns the payload, or ``None`` when it is unavailable -- in which case a
    note explaining *which* backends that costs is appended to ``resolved``,
    because "REVEL returned nothing" and "we never managed to ask" are
    different facts and only one of them is about REVEL.
    """
    if key in resolved:
        return resolved[key]

    from .unified_model_spec import render

    provider = (CONTEXT_PROVIDERS.get(resolved.get("task", "")) or {}).get(key)
    if provider is None:
        return None

    missing = [
        need for need in provider.get("needs", []) if not _lookup_dotted(resolved, need)
    ]
    if missing:
        resolved["notes"].append(
            f"Could not fetch '{key}' ({provider.get('serves', 'several backends')}): "
            f"missing {', '.join(missing)}."
        )
        resolved[key] = None
        return None

    args = {k: render(v, resolved) for k, v in provider["args"].items()}
    payload = _unwrap(call(provider["tool"], args))
    if payload is None:
        resolved["notes"].append(
            f"{provider['tool']} returned no data, so {provider.get('serves', 'some backends')} "
            "could not be scored for this input."
        )
    else:
        resolved["sources"].append(provider["tool"])
    resolved[key] = payload
    return payload


def _lookup_dotted(context: Dict[str, Any], dotted: str) -> Any:
    node: Any = context
    for part in dotted.split("."):
        if not isinstance(node, dict):
            return None
        node = node.get(part)
        if node is None:
            return None
    return node


def get_resolver(name: str) -> Callable[..., Dict[str, Any]]:
    resolver = RESOLVERS.get(name)
    if resolver is None:
        raise KeyError(f"No resolver named {name!r}. Known: {sorted(RESOLVERS)}")
    return resolver


def _retry(
    call: Callable[[str, Dict[str, Any]], Any],
    tool: str,
    args: Dict[str, Any],
    attempts: int = 3,
) -> Any:
    """Call a resolution tool, retrying transient upstream failures.

    Ensembl's REST service fails intermittently under load -- observed both an
    HTTP 500 from the variant recoder and an empty VEP annotation for a
    coordinate that had answered correctly moments earlier. Because resolution
    is upstream of every backend, one such blip silently costs *all* the
    models that depend on that payload: a single flaky VEP call is what
    removed both SIFT and PolyPhen-2 from an otherwise complete comparison.
    Retrying here is far cheaper than losing the run, and the short backoff
    keeps a genuinely dead service from costing more than a second or two.
    """
    delay = 0.4
    for attempt in range(attempts):
        payload = _unwrap(call(tool, args))
        if payload is not None:
            return payload
        if attempt < attempts - 1:
            import time

            time.sleep(delay)
            delay *= 2
            # Replaying a memoized failure is not a retry, so ask the caller
            # to skip its cache. Injecting a throwaway argument would do it
            # too, but tools validate their parameters strictly and an unknown
            # key is rejected outright -- trading a transient failure for a
            # permanent one.
            fresh = getattr(call, "fresh", None)
            if fresh is not None:
                payload = _unwrap(fresh(tool, args))
                if payload is not None:
                    return payload
    return None


def _unwrap(payload: Any) -> Any:
    """Strip ToolUniverse's ``{"status": "success", "data": ...}`` envelope.

    Tools in the codebase disagree about whether to wrap; a resolver that only
    handles one shape drops perfectly good data from the other.
    """
    if isinstance(payload, dict):
        if payload.get("status") == "error" or "error" in payload and len(payload) <= 2:
            return None
        if "data" in payload and payload.get("status") in (None, "success", "ok"):
            return payload["data"]
    return payload


def _clean(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _clean_sequence(value: Any) -> Optional[str]:
    if not value:
        return None
    text = "".join(str(value).split()).upper()
    # Tolerate a pasted FASTA record rather than rejecting it.
    if text.startswith(">"):
        lines = str(value).splitlines()
        text = "".join(
            line.strip() for line in lines if not line.startswith(">")
        ).upper()
    return text or None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_chrom(value: Any) -> Optional[str]:
    text = _clean(value)
    if not text:
        return None
    text = re.sub(r"^chr", "", text, flags=re.IGNORECASE)
    return "MT" if text.upper() in ("M", "MT") else text.upper()
