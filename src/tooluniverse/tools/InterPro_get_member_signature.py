"""
InterPro_get_member_signature

Retrieve detail for a single InterPro MEMBER-DATABASE signature (not an integrated InterPro IPR e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def InterPro_get_member_signature(
    member_database: str,
    accession: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Retrieve detail for a single InterPro MEMBER-DATABASE signature (not an integrated InterPro IPR e...

    Parameters
    ----------
    member_database : str
        Member database slug: pfam, smart, panther, cdd, ncbifam (TIGRFAM), ssf (SUPE...
    accession : str
        The member-database signature accession, e.g. PF00069 (Pfam), SM00002 (SMART)...
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
        for k, v in {"member_database": member_database, "accession": accession}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "InterPro_get_member_signature",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["InterPro_get_member_signature"]
