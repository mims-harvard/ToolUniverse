"""
CPIC_get_drug_info

Get pharmacogenomics information for a drug from the CPIC database. Returns drug identifiers incl...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def CPIC_get_drug_info(
    name: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get pharmacogenomics information for a drug from the CPIC database. Returns drug identifiers incl...

    Parameters
    ----------
    name : str
        Drug name in lowercase (e.g., 'warfarin', 'codeine', 'clopidogrel', 'simvasta...
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

    return get_shared_client().run_one_function(
        {"name": "CPIC_get_drug_info", "arguments": {"name": name}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["CPIC_get_drug_info"]
