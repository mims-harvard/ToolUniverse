"""
EBI_translate_sequence

Translate nucleotide to protein, back-translate protein to nucleotide, or produce a six-frame tra...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EBI_translate_sequence(
    sequence: str,
    mode: Optional[str] = None,
    frame: Optional[str] = None,
    codon_table: Optional[str] = None,
    min_orf_size: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Translate nucleotide to protein, back-translate protein to nucleotide, or produce a six-frame tra...

    Parameters
    ----------
    sequence : str
        Input sequence, FASTA or raw.
    mode : str
        'dna_to_protein' (default), 'protein_to_dna', or 'six_frame'.
    frame : str
        Reading frame for dna_to_protein: '1','2','3','-1','-2','-3', or '6' for all.
    codon_table : str
        Genetic code, e.g. '0' standard, '2' vertebrate mitochondrial, '11' bacterial.
    min_orf_size : int
        Minimum ORF size in nucleotides for six_frame mode.
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
            "sequence": sequence,
            "mode": mode,
            "frame": frame,
            "codon_table": codon_table,
            "min_orf_size": min_orf_size,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EBI_translate_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EBI_translate_sequence"]
