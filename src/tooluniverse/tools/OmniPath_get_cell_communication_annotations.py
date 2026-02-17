"""
OmniPath_get_cell_communication_annotations

Get cell-cell communication annotations for proteins from databases like CellPhoneDB, CellChatDB,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OmniPath_get_cell_communication_annotations(
    proteins: str,
    databases: Optional[str | Any] = None,
    genesymbols: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get cell-cell communication annotations for proteins from databases like CellPhoneDB, CellChatDB,...

    Parameters
    ----------
    proteins : str
        UniProt accession(s) or gene symbol(s), comma-separated. Examples: 'P01137,P3...
    databases : str | Any
        Filter by annotation database(s), comma-separated. Cell communication databas...
    genesymbols : bool | Any
        Whether to include gene symbols in output (default: true).
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
            "name": "OmniPath_get_cell_communication_annotations",
            "arguments": {
                "proteins": proteins,
                "databases": databases,
                "genesymbols": genesymbols,
            },
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["OmniPath_get_cell_communication_annotations"]
