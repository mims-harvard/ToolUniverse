"""
CodonUsage_get_table

Retrieve the codon usage table for an organism from the Codon Usage Database, indexed by NCBI tax...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CodonUsage_get_table(
    taxid: int | str,
    amino_acid: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Retrieve the codon usage table for an organism from the Codon Usage Database, indexed by NCBI tax...

    Parameters
    ----------
    taxid : int | str
        NCBI taxonomy identifier, e.g. 9606 (human), 83333 (E. coli K-12), 4932 (yeas...
    amino_acid : str
        Restrict to one amino acid using its three-letter code, e.g. 'Leu', 'Ala', or...
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
        for k, v in {"taxid": taxid, "amino_acid": amino_acid}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "CodonUsage_get_table",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CodonUsage_get_table"]
