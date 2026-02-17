"""
OmniPath_get_signaling_interactions

Get intracellular signaling pathway interactions from OmniPath's curated datasets. Supports query...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_signaling_interactions(
    partners: Optional[str | Any] = None,
    sources: Optional[str | Any] = None,
    targets: Optional[str | Any] = None,
    datasets: Optional[str | Any] = None,
    directed: Optional[bool | Any] = None,
    signed: Optional[bool | Any] = None,
    organisms: Optional[int | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get intracellular signaling pathway interactions from OmniPath's curated datasets. Supports query...

    Parameters
    ----------
    partners : str | Any
        Gene symbol(s) or UniProt ID(s) to query. Comma-separated for multiple. Examp...
    sources : str | Any
        Gene symbol(s) or UniProt ID(s) for source/upstream proteins only.
    targets : str | Any
        Gene symbol(s) or UniProt ID(s) for target/downstream proteins only.
    datasets : str | Any
        Which OmniPath dataset(s) to query, comma-separated. Options: 'omnipath' (cur...
    directed : bool | Any
        Filter for directed interactions only (default: true for signaling).
    signed : bool | Any
        Filter for interactions with known stimulation/inhibition sign.
    organisms : int | Any
        NCBI taxonomy ID. Default: 9606 (human). Options: 9606, 10090, 10116.
    limit : int | Any
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

    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_signaling_interactions",
            "arguments": {
                "partners": partners,
                "sources": sources,
                "targets": targets,
                "datasets": datasets,
                "directed": directed,
                "signed": signed,
                "organisms": organisms,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_signaling_interactions"]
