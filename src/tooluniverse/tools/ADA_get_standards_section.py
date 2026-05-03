"""
ADA_get_standards_section

Fetch detailed content from a specific ADA Standards of Care section by PMID. Retrieves the abstr...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ADA_get_standards_section(
    pmid: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Fetch detailed content from a specific ADA Standards of Care section by PMID. Retrieves the abstr...

    Parameters
    ----------
    pmid : str
        PubMed ID (PMID) of the ADA Standards section to retrieve (e.g., '41358900' f...
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
    _args = {k: v for k, v in {"pmid": pmid}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ADA_get_standards_section",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ADA_get_standards_section"]
