"""
OpenGenes_get_gene

Get the aging/longevity profile of a human gene by symbol from Open Genes, a manually-curated agi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenGenes_get_gene(
    symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get the aging/longevity profile of a human gene by symbol from Open Genes, a manually-curated agi...

    Parameters
    ----------
    symbol : str
        Human gene symbol, e.g. 'GHR', 'FOXO3', 'TP53', 'SIRT1'.
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
    _args = {k: v for k, v in {"symbol": symbol}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenGenes_get_gene",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenGenes_get_gene"]
