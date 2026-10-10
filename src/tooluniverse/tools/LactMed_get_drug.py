"""
LactMed_get_drug

Breastfeeding / lactation safety of one drug from LactMed, the Drugs and Lactation Database (NICH...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LactMed_get_drug(
    drug_name: str,
    section: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Breastfeeding / lactation safety of one drug from LactMed, the Drugs and Lactation Database (NICH...

    Parameters
    ----------
    drug_name : str
        Generic (preferred) or brand drug name, e.g. 'metoprolol' or 'Lopressor'.
    section : str
        Optional: return only this section in full, e.g. 'Drug Levels' or 'Effects in...
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
        for k, v in {"drug_name": drug_name, "section": section}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LactMed_get_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LactMed_get_drug"]
