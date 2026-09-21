"""
DDBJ_get_cross_references

List the DDBJ records linked to an accession, so you can walk a study to its experiments, runs, a...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DDBJ_get_cross_references(
    accession: str,
    entry_type: Optional[str] = None,
    reference_type: Optional[str] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    List the DDBJ records linked to an accession, so you can walk a study to its experiments, runs, a...

    Parameters
    ----------
    accession : str
        DDBJ accession, e.g. 'DRP000001'.
    entry_type : str
        Override the inferred entry type. One of: bioproject, biosample, sra-study, s...
    reference_type : str
        Only return links of this type, e.g. 'sra-run', 'bioproject'.
    limit : int
        Maximum links to return (default 25, max 200).
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
    _args = {
        k: v
        for k, v in {
            "accession": accession,
            "entry_type": entry_type,
            "reference_type": reference_type,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DDBJ_get_cross_references",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DDBJ_get_cross_references"]
