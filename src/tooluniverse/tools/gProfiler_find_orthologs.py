"""
gProfiler_find_orthologs

Find orthologous genes across species using g:Profiler (g:Orth) from the University of Tartu. Map...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gProfiler_find_orthologs(
    gene_list: str,
    source_organism: Optional[str] = None,
    target_organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Find orthologous genes across species using g:Profiler (g:Orth) from the University of Tartu. Map...

    Parameters
    ----------
    gene_list : str
        Comma-separated list of gene identifiers from the source organism. Examples: ...
    source_organism : str
        Source organism. Default: 'hsapiens'. Examples: 'hsapiens' (human), 'mmusculu...
    target_organism : str
        Target organism to find orthologs in. Default: 'mmusculus'. Examples: 'mmuscu...
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

    return get_shared_client().run_one_function(
        {
            "name": "gProfiler_find_orthologs",
            "arguments": {
                "gene_list": gene_list,
                "source_organism": source_organism,
                "target_organism": target_organism,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gProfiler_find_orthologs"]
