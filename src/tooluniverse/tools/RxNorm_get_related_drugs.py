"""
RxNorm_get_related_drugs

List all related drug products (branded names, generic products, ingredients) for a
drug RXCUI or name using the NLM RxNorm API. No API key required.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def RxNorm_get_related_drugs(
    rxcui: Optional[str] = None,
    drug_name: Optional[str] = None,
    tty: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all related drug products for a drug RXCUI or name.

    Parameters
    ----------
    rxcui : str, optional
        RxNorm Concept Unique Identifier.
    drug_name : str, optional
        Drug name to auto-resolve to RXCUI.
    tty : str, optional
        Term types to include (e.g., 'IN+BN+SBD+SCD'). Default: 'IN+BN+SBD+SCD'.
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
        for k, v in {"rxcui": rxcui, "drug_name": drug_name, "tty": tty}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {"name": "RxNorm_get_related_drugs", "arguments": _args},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["RxNorm_get_related_drugs"]
