"""
ChannelsDB_get_channels_pdb

Get protein channel, tunnel, and pore data for a PDB structure from ChannelsDB. ChannelsDB is a c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChannelsDB_get_channels_pdb(
    pdb_id: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get protein channel, tunnel, and pore data for a PDB structure from ChannelsDB. ChannelsDB is a c...

    Parameters
    ----------
    pdb_id : str
        PDB structure identifier (4-character code, case-insensitive). Examples: '1ym...
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
    _args = {k: v for k, v in {"pdb_id": pdb_id}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "ChannelsDB_get_channels_pdb",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChannelsDB_get_channels_pdb"]
