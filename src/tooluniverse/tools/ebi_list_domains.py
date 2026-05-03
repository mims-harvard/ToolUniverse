"""
ebi_list_domains

List all available EBI Search domains. Returns metadata about all searchable domains including do...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ebi_list_domains(
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    List all available EBI Search domains. Returns metadata about all searchable domains including do...

    Parameters
    ----------
    format : str
        Response format
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
    _args = {k: v for k, v in {"format": format}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ebi_list_domains",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ebi_list_domains"]
