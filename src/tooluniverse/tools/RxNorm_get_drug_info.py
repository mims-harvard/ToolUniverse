"""
RxNorm_get_drug_info

Fetch comprehensive drug properties from NLM RxNorm by RXCUI or drug name.
Returns name, term type (IN/BN/SCD/SBD), synonym. No API key required.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxNorm_get_drug_info(
    rxcui: Optional[str] = None,
    drug_name: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Fetch comprehensive drug properties from NLM RxNorm.

    Parameters
    ----------
    rxcui : str, optional
        RxNorm Concept Unique Identifier.
    drug_name : str, optional
        Drug name to auto-resolve to RXCUI.
    stream_callback : Callable, optional
        Callback for streaming output.
    use_cache : bool, default False
        Enable caching.
    validate : bool, default True
        Validate parameters.

    Returns
    -------
    dict[str, Any]
    """
    _args = {
        k: v
        for k, v in {"rxcui": rxcui, "drug_name": drug_name}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "RxNorm_get_drug_info", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxNorm_get_drug_info"]
