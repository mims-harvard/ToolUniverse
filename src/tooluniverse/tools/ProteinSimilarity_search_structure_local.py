"""
ProteinSimilarity_search_structure_local

Compare single-chain PDB queries locally with Foldseek/TM-align and caller-managed references. Re...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ProteinSimilarity_search_structure_local(
    query_path: str,
    reference_path: str,
    threads: Optional[int] = None,
    timeout_seconds: Optional[int] = None,
    max_hits_per_query: Optional[int] = None,
    minimum_query_coverage: Optional[float] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Compare single-chain PDB queries locally with Foldseek/TM-align and caller-managed references. Re...

    Parameters
    ----------
    query_path : str
        Local single-chain one-model .pdb file, or directory of1–50 such files with s...
    reference_path : str
        Local reference file or prebuilt database prefix (.dbtype must exist); builti...
    threads : int
        CPU threads; defaults to2.
    timeout_seconds : int
        Bounded process runtime; defaults to300 seconds.
    max_hits_per_query : int
        Returned hits per query, defaults to20; truncation is explicit.
    minimum_query_coverage : float
        Minimum fraction of query residues covered; defaults to0.
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
            "query_path": query_path,
            "reference_path": reference_path,
            "threads": threads,
            "timeout_seconds": timeout_seconds,
            "max_hits_per_query": max_hits_per_query,
            "minimum_query_coverage": minimum_query_coverage,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ProteinSimilarity_search_structure_local",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ProteinSimilarity_search_structure_local"]
