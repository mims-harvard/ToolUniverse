"""
OmniPath_get_intercell_roles

Get intercellular communication roles for proteins from OmniPath. Classifies proteins as ligands,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_intercell_roles(
    proteins: Optional[str | Any] = None,
    categories: Optional[str | Any] = None,
    scope: Optional[str | Any] = None,
    transmitter: Optional[bool | Any] = None,
    receiver: Optional[bool | Any] = None,
    secreted: Optional[bool | Any] = None,
    limit: Optional[int | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get intercellular communication roles for proteins from OmniPath. Classifies proteins as ligands,...

    Parameters
    ----------
    proteins : str | Any
        Gene symbol(s) or UniProt ID(s), comma-separated. Examples: 'EGFR', 'TGFB1,PD...
    categories : str | Any
        Filter by intercellular role category. Examples: 'ligand', 'receptor', 'adhes...
    scope : str | Any
        Filter by annotation scope: 'generic' (general role) or 'specific' (cell-type...
    transmitter : bool | Any
        Filter for transmitter/sender proteins (true) or non-transmitters (false).
    receiver : bool | Any
        Filter for receiver proteins (true) or non-receivers (false).
    secreted : bool | Any
        Filter for secreted proteins (true) or non-secreted (false).
    limit : int | Any
        Maximum number of results to return. Default: no limit.
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
            "name": "OmniPath_get_intercell_roles",
            "arguments": {
                "proteins": proteins,
                "categories": categories,
                "scope": scope,
                "transmitter": transmitter,
                "receiver": receiver,
                "secreted": secreted,
                "limit": limit,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_intercell_roles"]
