"""
ZINC_search_by_properties

Filter ZINC compounds by molecular properties (Lipinski Rule of Five, Veber rules). Specify range...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZINC_search_by_properties(
    operation: str,
    mwt_min: Optional[float | Any] = None,
    mwt_max: Optional[float | Any] = None,
    logp_min: Optional[float | Any] = None,
    logp_max: Optional[float | Any] = None,
    hbd_max: Optional[int | Any] = None,
    hba_max: Optional[int | Any] = None,
    rb_max: Optional[int | Any] = None,
    purchasability: Optional[str | Any] = None,
    count: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Filter ZINC compounds by molecular properties (Lipinski Rule of Five, Veber rules). Specify range...

    Parameters
    ----------
    operation : str
        Operation type
    mwt_min : float | Any
        Minimum molecular weight in Da (e.g., 150 for fragments, 250 for leads)
    mwt_max : float | Any
        Maximum molecular weight in Da (e.g., 500 for Lipinski, 250 for fragments)
    logp_min : float | Any
        Minimum LogP (e.g., -1 for hydrophilic compounds)
    logp_max : float | Any
        Maximum LogP (e.g., 5 for Lipinski rule, 3 for lead-like)
    hbd_max : int | Any
        Maximum hydrogen bond donors (e.g., 5 for Lipinski)
    hba_max : int | Any
        Maximum hydrogen bond acceptors (e.g., 10 for Lipinski)
    rb_max : int | Any
        Maximum rotatable bonds (e.g., 10 for Veber rule)
    purchasability : str | Any
        Restrict to a purchasability tier
    count : int
        Maximum number of results (default: 20, max: 100)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    return get_shared_client().run_one_function(
        {
            "name": "ZINC_search_by_properties",
            "arguments": {
                "operation": operation,
                "mwt_min": mwt_min,
                "mwt_max": mwt_max,
                "logp_min": logp_min,
                "logp_max": logp_max,
                "hbd_max": hbd_max,
                "hba_max": hba_max,
                "rb_max": rb_max,
                "purchasability": purchasability,
                "count": count,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZINC_search_by_properties"]
