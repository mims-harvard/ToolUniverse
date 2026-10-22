"""
OmniPath_get_signaling_interactions

Get intracellular signaling pathway interactions from OmniPath's curated datasets. Supports query...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_signaling_interactions(
    partners: Optional[str] = None,
    sources: Optional[str] = None,
    targets: Optional[str] = None,
    datasets: Optional[str] = None,
    directed: Optional[bool] = None,
    signed: Optional[bool] = None,
    organisms: Optional[int] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get intracellular signaling pathway interactions from OmniPath's curated datasets. Supports query...

    Parameters
    ----------
    partners : str
        Gene symbol(s) or UniProt ID(s) to query. Comma-separated for multiple. Examp...
    sources : str
        Gene symbol(s) or UniProt ID(s) for source/upstream proteins only.
    targets : str
        Gene symbol(s) or UniProt ID(s) for target/downstream proteins only.
    datasets : str
        Which OmniPath dataset(s) to query, comma-separated. Options: 'omnipath' (cur...
    directed : bool
        Filter for directed interactions only (default: true for signaling).
    signed : bool
        Filter for interactions with known stimulation/inhibition sign.
    organisms : int
        NCBI taxonomy ID. Default: 9606 (human). Options: 9606, 10090, 10116.
    limit : int
        Maximum number of interactions to return.
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
            "partners": partners,
            "sources": sources,
            "targets": targets,
            "datasets": datasets,
            "directed": directed,
            "signed": signed,
            "organisms": organisms,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_signaling_interactions",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_signaling_interactions"]
