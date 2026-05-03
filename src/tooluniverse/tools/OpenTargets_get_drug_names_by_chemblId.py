"""
OpenTargets_get_drug_names_by_chemblId

Get drug generic name and brand names (trade names) based on ChEMBL ID. Returns the drug name (ty...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_drug_names_by_chemblId(
    chemblId: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get drug generic name and brand names (trade names) based on ChEMBL ID. Returns the drug name (ty...

    Parameters
    ----------
    chemblId : str
        The ChEMBL ID of the drug.
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"chemblId": chemblId}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_drug_names_by_chemblId",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_drug_names_by_chemblId"]
