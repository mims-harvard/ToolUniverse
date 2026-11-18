"""
PubMLST_get_profile

Get the allelic profile of one sequence type (ST) from a PubMLST typing scheme: the allele number...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def PubMLST_get_profile(
    database: str,
    st: int | str,
    scheme_id: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get the allelic profile of one sequence type (ST) from a PubMLST typing scheme: the allele number...

    Parameters
    ----------
    database : str
        PubMLST sequence-definition database, e.g. 'pubmlst_neisseria_seqdef', or an ...
    scheme_id : int
        Scheme id from PubMLST_list_schemes (default 1, usually the 7-locus MLST sche...
    st : int | str
        Sequence type number, e.g. 11 (also accepts 'ST-11').
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
        k: v
        for k, v in {"database": database, "scheme_id": scheme_id, "st": st}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "PubMLST_get_profile",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["PubMLST_get_profile"]
