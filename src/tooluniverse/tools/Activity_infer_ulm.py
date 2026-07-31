"""
Activity_infer_ulm

Infer transcription-factor / pathway activities from a per-gene statistic (e.g. a DESeq2/edgeR t-...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Activity_infer_ulm(
    network: list[Any],
    gene_stats: Optional[dict[str, Any]] = None,
    genes: Optional[list[str]] = None,
    stats: Optional[list[Any]] = None,
    min_targets: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Infer transcription-factor / pathway activities from a per-gene statistic (e.g. a DESeq2/edgeR t-...

    Parameters
    ----------
    gene_stats : dict[str, Any]
        {gene: statistic} mapping (e.g. DE t-statistic per gene). Alternative to gene...
    genes : list[str]
        Gene identifiers (use with `stats`, same order).
    stats : list[Any]
        Per-gene statistic (same order as `genes`).
    network : list[Any]
        Regulatory edges: [{source, target, weight}] (weight defaults to 1; 'mor' acc...
    min_targets : int
        Minimum targets present in the gene list for a source to be tested (default 5).
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
            "gene_stats": gene_stats,
            "genes": genes,
            "stats": stats,
            "network": network,
            "min_targets": min_targets,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Activity_infer_ulm",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Activity_infer_ulm"]
