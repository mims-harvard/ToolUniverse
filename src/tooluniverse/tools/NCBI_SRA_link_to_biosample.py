"""
NCBI_SRA_link_to_biosample

Link SRA sequencing runs to their associated BioSample records to access biological sample metada...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NCBI_SRA_link_to_biosample(
    operation: str,
    accessions: list[str] | str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Link SRA sequencing runs to their associated BioSample records to access biological sample metada...

    Parameters
    ----------
    operation : str
        Operation type (fixed: link_to_biosample)
    accessions : list[str] | str
        SRA UID(s) from NCBI_SRA_search_runs. Can be single UID or array of UIDs. The...
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

    return get_shared_client().run_one_function(
        {
            "name": "NCBI_SRA_link_to_biosample",
            "arguments": {"operation": operation, "accessions": accessions},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NCBI_SRA_link_to_biosample"]
