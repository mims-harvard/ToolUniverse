"""
predict_variant_effect

Score how damaging a genetic variant is, using one model or all 21 at once. Give the variant in w...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def predict_variant_effect(
    variant: Optional[str] = None,
    chrom: Optional[str] = None,
    pos: Optional[int] = None,
    ref: Optional[str] = None,
    alt: Optional[str] = None,
    rsid: Optional[str] = None,
    gene: Optional[str] = None,
    uniprot: Optional[str] = None,
    protein_change: Optional[str] = None,
    sequence: Optional[str] = None,
    position: Optional[int] = None,
    mutant: Optional[str] = None,
    assembly: Optional[str] = None,
    backend: Optional[str | list[str]] = None,
    list_models: Optional[bool] = None,
    include_notes: Optional[bool] = None,
    include_details: Optional[bool] = None,
    include_raw: Optional[bool] = None,
    max_workers: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Score how damaging a genetic variant is, using one model or all 21 at once. Give the variant in w...

    Parameters
    ----------
    variant : str
        Variant in any common form: HGVS ('17:g.7675088C>T'), 'chrom pos ref alt' ('1...
    chrom : str
        Chromosome, if giving coordinates explicitly.
    pos : int
        1-based genomic position.
    ref : str
        Reference allele.
    alt : str
        Alternate allele.
    rsid : str
        dbSNP rsID.
    gene : str
        HGNC gene symbol, e.g. 'TP53'.
    uniprot : str
        UniProt accession, e.g. 'P04637'.
    protein_change : str
        Protein change, e.g. 'R175H' or 'p.Arg175His'.
    sequence : str
        Protein sequence (1-letter). Use this to score a variant in a sequence that i...
    position : int
        1-based residue position, when scoring by sequence.
    mutant : str
        Mutant amino acid (1-letter), when scoring by sequence.
    assembly : str
        Genome build. Default GRCh38; use 'GRCh37' for hg19 coordinates.
    backend : str | list[str]
        Which model(s) to run. Omit or use 'all' to run every applicable model and ge...
    list_models : bool
        Return the catalogue of models for this task -- id, units, direction, API key...
    include_notes : bool
        With list_models, include per-model caveats. Default true.
    include_details : bool
        Include each model's full canonical record, not just the summary table. Defau...
    include_raw : bool
        Keep bulky payloads (structure coordinates, docking poses) in the reply. Defa...
    max_workers : int
        Models to run concurrently. Default 6.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    Any
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "variant": variant,
            "chrom": chrom,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "rsid": rsid,
            "gene": gene,
            "uniprot": uniprot,
            "protein_change": protein_change,
            "sequence": sequence,
            "position": position,
            "mutant": mutant,
            "assembly": assembly,
            "backend": backend,
            "list_models": list_models,
            "include_notes": include_notes,
            "include_details": include_details,
            "include_raw": include_raw,
            "max_workers": max_workers,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "predict_variant_effect",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["predict_variant_effect"]
