"""
HealthCanadaDPD_get_product

Get one drug product's record from the Health Canada Drug Product Database (DPD) by drug_code or ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HealthCanadaDPD_get_product(
    drug_code: Optional[int] = None,
    din: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get one drug product's record from the Health Canada Drug Product Database (DPD) by drug_code or ...

    Parameters
    ----------
    drug_code : int
        DPD drug code from a HealthCanadaDPD search, e.g. 73824. Give this or din.
    din : str
        Drug Identification Number, up to 8 digits, e.g. '02253275'.
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
    _args = {
        k: v for k, v in {"drug_code": drug_code, "din": din}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HealthCanadaDPD_get_product",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HealthCanadaDPD_get_product"]
