"""
GeneBe_classify_variant

Classify a germline variant under the ACMG/AMP guidelines using GeneBe (genebe.net). Given chromo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneBe_classify_variant(
    chr: str,
    pos: int,
    ref: str,
    alt: str,
    genome: Optional[str] = "hg38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Classify a germline variant under the ACMG/AMP guidelines using GeneBe (genebe.net). Given chromo...

    Parameters
    ----------
    chr : str
        Chromosome, e.g. '7', 'X' (a 'chr' prefix is also accepted).
    pos : int
        1-based genomic position of the variant, e.g. 140753336.
    ref : str
        Reference allele, e.g. 'A'.
    alt : str
        Alternate allele, e.g. 'T'.
    genome : str
        Genome build: 'hg38' (default) / 'GRCh38' or 'hg19' / 'GRCh37'.
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
            "chr": chr,
            "pos": pos,
            "ref": ref,
            "alt": alt,
            "genome": genome,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GeneBe_classify_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GeneBe_classify_variant"]
