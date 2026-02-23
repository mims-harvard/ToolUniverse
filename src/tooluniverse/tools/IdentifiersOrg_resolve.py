"""
IdentifiersOrg_resolve

Resolve a biological identifier to its resource URLs using Identifiers.org. Given a namespace (e....
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def IdentifiersOrg_resolve(
    namespace: str,
    local_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Resolve a biological identifier to its resource URLs using Identifiers.org. Given a namespace (e....

    Parameters
    ----------
    namespace : str
        Database namespace prefix. Examples: 'uniprot', 'pdb', 'ncbigene', 'go', 'tax...
    local_id : str
        The local identifier within the namespace. Examples: 'P04637' (for uniprot), ...
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
        {
            "name": "IdentifiersOrg_resolve",
            "arguments": {"namespace": namespace, "local_id": local_id},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["IdentifiersOrg_resolve"]
