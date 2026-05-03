"""
ebi_get_domain_info

Get metadata and field information for a specific EBI domain. Returns domain description, availab...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ebi_get_domain_info(
    domain: str,
    format: Optional[str] = "json",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get metadata and field information for a specific EBI domain. Returns domain description, availab...

    Parameters
    ----------
    domain : str
        EBI domain name (e.g., 'ensembl', 'uniprot', 'interpro')
    format : str

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
        k: v for k, v in {"domain": domain, "format": format}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ebi_get_domain_info",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ebi_get_domain_info"]
