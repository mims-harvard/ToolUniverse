"""
L1000FWD_sig_search

Transcriptomic signature query against the LINCS L1000 Connectivity Map via the L1000FWD Firework...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def L1000FWD_sig_search(
    operation: str,
    up_genes: list[str],
    down_genes: list[str],
    n_results: Optional[int] = 10,
    mode: Optional[str] = 'similar',
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Transcriptomic signature query against the LINCS L1000 Connectivity Map via the L1000FWD Firework...

    Parameters
    ----------
    operation : str
        Operation type
    up_genes : list[str]
        List of up-regulated gene symbols (e.g., ['MYC', 'TP53'])
    down_genes : list[str]
        List of down-regulated gene symbols (e.g., ['CDKN1A', 'RB1'])
    n_results : int
        Number of top results to return (default 10)
    mode : str
        Return signatures 'similar' to or 'opposite' of the query signature (default:...
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
        "operation": operation,
                "up_genes": up_genes,
                "down_genes": down_genes,
                "n_results": n_results,
                "mode": mode
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "L1000FWD_sig_search",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["L1000FWD_sig_search"]
