"""
MARRVEL_get_omim_phenotypes

Get OMIM phenotype/disease associations for a human gene by symbol via MARRVEL: each association'...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MARRVEL_get_omim_phenotypes(
    symbol: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get OMIM phenotype/disease associations for a human gene by symbol via MARRVEL: each association'...

    Parameters
    ----------
    symbol : str
        HGNC gene symbol, e.g. 'CFTR', 'BRCA1'.
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
            "name": "MARRVEL_get_omim_phenotypes",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MARRVEL_get_omim_phenotypes"]
