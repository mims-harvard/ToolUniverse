"""
UniProtRef_get_proteome

Get reference proteome information from UniProt by proteome ID. Returns the proteome description,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def UniProtRef_get_proteome(
    proteome_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get reference proteome information from UniProt by proteome ID. Returns the proteome description,...

    Parameters
    ----------
    proteome_id : str
        UniProt proteome ID. Examples: 'UP000005640' (human), 'UP000000589' (mouse), ...
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
    _args = {k: v for k, v in {"proteome_id": proteome_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "UniProtRef_get_proteome",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["UniProtRef_get_proteome"]
