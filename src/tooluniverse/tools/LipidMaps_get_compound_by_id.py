"""
LipidMaps_get_compound_by_id

Get lipid structure and classification by LIPID MAPS ID (LMID). Returns full lipid record includi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def LipidMaps_get_compound_by_id(
    input_value: str,
    output_item: Optional[str] = "all",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get lipid structure and classification by LIPID MAPS ID (LMID). Returns full lipid record includi...

    Parameters
    ----------
    input_value : str
        LIPID MAPS ID (LMID), e.g., 'LMFA08040013'. Format: LM + 2-letter category + ...
    output_item : str
        Type of output. Options: 'all' (complete record), 'name', 'formula', 'exactma...
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
        k: v
        for k, v in {"input_value": input_value, "output_item": output_item}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "LipidMaps_get_compound_by_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["LipidMaps_get_compound_by_id"]
