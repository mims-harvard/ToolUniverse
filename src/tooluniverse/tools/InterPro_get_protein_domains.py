"""
InterPro_get_protein_domains

Get protein domain annotations from InterPro database using UniProt protein ID. Returns domain fa...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_protein_domains(
    protein_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Get protein domain annotations from InterPro database using UniProt protein ID. Returns domain fa...

    Parameters
    ----------
    protein_id : str
        UniProt protein ID (e.g., P05067, Q9Y6K9)
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {k: v for k, v in {"protein_id": protein_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_protein_domains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_protein_domains"]
