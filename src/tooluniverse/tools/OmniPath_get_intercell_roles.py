"""
OmniPath_get_intercell_roles

Get intercellular communication roles for proteins from OmniPath. Classifies proteins as ligands,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_intercell_roles(
    proteins: Optional[str] = None,
    categories: Optional[str] = None,
    scope: Optional[str] = None,
    transmitter: Optional[bool] = None,
    receiver: Optional[bool] = None,
    secreted: Optional[bool] = None,
    limit: Optional[int] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get intercellular communication roles for proteins from OmniPath. Classifies proteins as ligands,...

    Parameters
    ----------
    proteins : str
        Gene symbol(s) or UniProt ID(s), comma-separated. Examples: 'EGFR', 'TGFB1,PD...
    categories : str
        Filter by intercellular role category. Examples: 'ligand', 'receptor', 'adhes...
    scope : str
        Filter by annotation scope: 'generic' (general role) or 'specific' (cell-type...
    transmitter : bool
        Filter for transmitter/sender proteins (true) or non-transmitters (false).
    receiver : bool
        Filter for receiver proteins (true) or non-receivers (false).
    secreted : bool
        Filter for secreted proteins (true) or non-secreted (false).
    limit : int
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

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "proteins": proteins,
            "categories": categories,
            "scope": scope,
            "transmitter": transmitter,
            "receiver": receiver,
            "secreted": secreted,
            "limit": limit,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "OmniPath_get_intercell_roles",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_intercell_roles"]
