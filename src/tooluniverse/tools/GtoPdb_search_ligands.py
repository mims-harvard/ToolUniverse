"""
GtoPdb_search_ligands

Search the Guide to Pharmacology database for pharmacological ligands (drugs, natural products, e...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GtoPdb_search_ligands(
    name: Optional[str | Any] = None,
    type_: Optional[str | Any] = None,
    approved: Optional[bool | Any] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Search the Guide to Pharmacology database for pharmacological ligands (drugs, natural products, e...

    Parameters
    ----------
    name : str | Any
        Ligand name or INN to search. Examples: 'aspirin', 'morphine', 'dopamine', 'c...
    type_ : str | Any
        Ligand type filter. Values: 'Approved', 'Synthetic organic', 'Natural product...
    approved : bool | Any
        Filter to approved drugs only (true) or all ligands (false/omit)
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
            "name": "GtoPdb_search_ligands",
            "arguments": {"name": name, "type": type_, "approved": approved},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GtoPdb_search_ligands"]
