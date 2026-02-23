"""
ZFIN_get_allele

Get detailed information about a specific zebrafish allele from ZFIN via the Alliance of Genome R...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ZFIN_get_allele(
    allele_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed information about a specific zebrafish allele from ZFIN via the Alliance of Genome R...

    Parameters
    ----------
    allele_id : str
        ZFIN allele ID with 'ZFIN:' prefix. Examples: 'ZFIN:ZDB-ALT-210706-1' (szu2 a...
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
        {"name": "ZFIN_get_allele", "arguments": {"allele_id": allele_id}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ZFIN_get_allele"]
