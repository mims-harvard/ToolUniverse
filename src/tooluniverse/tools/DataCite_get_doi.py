"""
DataCite_get_doi

Get metadata for a research dataset or publication by DOI from DataCite. DataCite is the primary ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DataCite_get_doi(
    doi: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get metadata for a research dataset or publication by DOI from DataCite. DataCite is the primary ...

    Parameters
    ----------
    doi : str
        DOI of the research output (e.g., '10.5281/zenodo.4088438', '10.5061/dryad.23...
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
        {"name": "DataCite_get_doi", "arguments": {"doi": doi}},
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DataCite_get_doi"]
