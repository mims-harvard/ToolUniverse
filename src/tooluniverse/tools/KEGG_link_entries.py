"""
KEGG_link_entries

Find cross-references between KEGG databases using the KEGG /link API. Given a KEGG entry (gene, ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def KEGG_link_entries(
    source: str,
    target: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Find cross-references between KEGG databases using the KEGG /link API. Given a KEGG entry (gene, ...

    Parameters
    ----------
    source : str
        KEGG entry ID to query. Examples: 'hsa:7157' (gene), 'hsa05200' (pathway), 'H...
    target : str
        Target KEGG database to search for links. Options: 'pathway', 'disease', 'dru...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v for k, v in {"source": source, "target": target}.items() if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_link_entries",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_link_entries"]
