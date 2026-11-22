"""
PubMLST_type_sequence

Type a DNA sequence against a PubMLST scheme: find the exact allele match at each locus and, when...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMLST_type_sequence(
    database: str,
    sequence: str,
    scheme_id: Optional[int] = None,
    partial_matches: Optional[bool] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Type a DNA sequence against a PubMLST scheme: find the exact allele match at each locus and, when...

    Parameters
    ----------
    database : str
        PubMLST sequence-definition database, e.g. 'pubmlst_neisseria_seqdef', or an ...
    scheme_id : int
        Scheme id from PubMLST_list_schemes (default 1, usually the 7-locus MLST sche...
    sequence : str
        DNA sequence or FASTA text (one locus or assembly contigs).
    partial_matches : bool
        Also return the closest allele for loci without an exact match (default false).
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "database": database,
            "scheme_id": scheme_id,
            "sequence": sequence,
            "partial_matches": partial_matches,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubMLST_type_sequence",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMLST_type_sequence"]
