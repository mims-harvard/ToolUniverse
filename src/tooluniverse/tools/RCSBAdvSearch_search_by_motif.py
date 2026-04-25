"""
RCSBAdvSearch_search_by_motif

Search RCSB PDB for protein structures containing a specific sequence motif pattern. Supports PRO...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RCSBAdvSearch_search_by_motif(
    pattern: str,
    pattern_type: Optional[str] = None,
    sequence_type: Optional[str] = None,
    rows: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search RCSB PDB for protein structures containing a specific sequence motif pattern. Supports PRO...

    Parameters
    ----------
    pattern : str
        Sequence motif pattern. PROSITE format examples: 'C-x(2,4)-C-x(3)-[LIVMFYWC]-...
    pattern_type : str
        Pattern format: 'prosite' (default, PROSITE-style), 'regex' (regular expressi...
    sequence_type : str
        Sequence type: 'protein' (default) or 'dna' or 'rna'.
    rows : int
        Number of results to return (default: 10, max: 50).
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
    _args = {k: v for k, v in {
        "pattern": pattern,
                "pattern_type": pattern_type,
                "sequence_type": sequence_type,
                "rows": rows
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "RCSBAdvSearch_search_by_motif",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["RCSBAdvSearch_search_by_motif"]
