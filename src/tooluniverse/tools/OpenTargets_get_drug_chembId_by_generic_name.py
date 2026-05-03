"""
OpenTargets_get_drug_chembId_by_generic_name

Fetch the drug chemblId and description based on the drug generic name.
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OpenTargets_get_drug_chembId_by_generic_name(
    drugName: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Fetch the drug chemblId and description based on the drug generic name.

    Parameters
    ----------
    drugName : str
        The generic name of the drug for which the ID is required.
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
    _args = {k: v for k, v in {"drugName": drugName}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OpenTargets_get_drug_chembId_by_generic_name",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OpenTargets_get_drug_chembId_by_generic_name"]
