"""
DrugCentral_get_drug

Get detailed DrugCentral information for a specific drug by its InChIKey or ChEMBL ID. Returns co...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DrugCentral_get_drug(
    chem_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed DrugCentral information for a specific drug by its InChIKey or ChEMBL ID. Returns co...

    Parameters
    ----------
    chem_id : str
        Drug identifier. InChIKey recommended (e.g., 'XZWYZXLIPXDOLR-UHFFFAOYSA-N' fo...
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
    _args = {k: v for k, v in {"chem_id": chem_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "DrugCentral_get_drug",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DrugCentral_get_drug"]
