"""
InterPro_list_member_signatures

Browse the signature catalog of one InterPro member database. Results are cursor-paginated: when ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_list_member_signatures(
    member_database: str,
    entry_type: Optional[str] = None,
    page_size: Optional[int] = None,
    cursor: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Browse the signature catalog of one InterPro member database. Results are cursor-paginated: when ...

    Parameters
    ----------
    member_database : str
        Member database slug: pfam, smart, panther, cdd, ncbifam, ssf, cathgene3d, pr...
    entry_type : str
        Optional filter by entry type: family, domain, homologous_superfamily, or site.
    page_size : int
        Number of signatures to return per page (1-100, default 20).
    cursor : str
        Opaque InterPro cursor returned as next_cursor by a previous call.
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
        for k, v in {
            "member_database": member_database,
            "entry_type": entry_type,
            "page_size": page_size,
            "cursor": cursor,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_list_member_signatures",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_list_member_signatures"]
