"""
KEGG_link_entries

Find cross-references between KEGG databases using the KEGG /link API.
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
) -> Any:
    """
    Find cross-references between KEGG databases.

    Parameters
    ----------
    source : str
        KEGG entry ID (e.g., 'hsa:7157' for gene, 'hsa05200' for pathway, 'H00004' for disease).
    target : str
        Target KEGG database (e.g., 'pathway', 'disease', 'drug', 'compound', 'ko', 'hsa').
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
    return get_shared_client().run_one_function(
        {
            "name": "KEGG_link_entries",
            "arguments": {"source": source, "target": target},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["KEGG_link_entries"]
