"""
gProfiler_annotate_snps

Map SNP rsIDs to genes and annotate their functional consequences using g:Profiler (g:SNPense) fr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gProfiler_annotate_snps(
    snp_list: str,
    organism: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map SNP rsIDs to genes and annotate their functional consequences using g:Profiler (g:SNPense) fr...

    Parameters
    ----------
    snp_list : str
        Comma-separated list of SNP rsIDs. Examples: 'rs11540652,rs429358,rs7903146' ...
    organism : str
        Organism identifier. Default: 'hsapiens'. Examples: 'hsapiens' (human), 'mmus...
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
        for k, v in {"snp_list": snp_list, "organism": organism}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gProfiler_annotate_snps",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gProfiler_annotate_snps"]
