"""
AllenBrain_search_structures

Search for brain structures/regions in the Allen Brain Atlas ontology by acronym or name. Returns...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AllenBrain_search_structures(
    acronym: Optional[str | Any] = None,
    name: Optional[str | Any] = None,
    num_rows: Optional[int] = 50,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Search for brain structures/regions in the Allen Brain Atlas ontology by acronym or name. Returns...

    Parameters
    ----------
    acronym : str | Any
        Structure acronym for exact match. Examples: 'CA1', 'VISp', 'TH', 'HIP', 'CTX'.
    name : str | Any
        Structure name for partial match (alternative to acronym). Example: 'hippocam...
    num_rows : int
        Max results to return. Default: 50.
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
    _args = {
        k: v
        for k, v in {"acronym": acronym, "name": name, "num_rows": num_rows}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AllenBrain_search_structures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AllenBrain_search_structures"]
