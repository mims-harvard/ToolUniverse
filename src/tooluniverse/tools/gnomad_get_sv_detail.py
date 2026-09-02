"""
gnomad_get_sv_detail

Get detailed information for a specific gnomAD structural variant by its ID. Resolves IDs from bo...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def gnomad_get_sv_detail(
    variant_id: str,
    dataset: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed information for a specific gnomAD structural variant by its ID. Resolves IDs from bo...

    Parameters
    ----------
    variant_id : str
        gnomAD structural variant ID. GRCh38/v4 IDs look like 'DEL_chr17_24e4872b'; G...
    dataset : str
        Optional SV callset override. Defaults to the callset auto-detected from the ...
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
        for k, v in {
            "variant_id": variant_id,
            "dataset": dataset,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "gnomad_get_sv_detail",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["gnomad_get_sv_detail"]
