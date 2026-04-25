"""
OxO_get_ontology_mappings

Get cross-reference mappings between ontology terms using the EBI Ontology Xref Service (OxO). Ma...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def OxO_get_ontology_mappings(
    term_id: str,
    distance: Optional[int] = 1,
    size: Optional[int] = 20,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get cross-reference mappings between ontology terms using the EBI Ontology Xref Service (OxO). Ma...

    Parameters
    ----------
    term_id : str
        Ontology term identifier to map. Format: PREFIX:ID. Examples: 'HP:0001250' (s...
    distance : int
        Maximum mapping distance. 1=direct mappings only, 2=via one intermediary, 3=v...
    size : int
        Maximum number of mappings to return (default 20, max 100).
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
    _args = {k: v for k, v in {
        "term_id": term_id,
                "distance": distance,
                "size": size
    }.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "OxO_get_ontology_mappings",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate
    )


__all__ = ["OxO_get_ontology_mappings"]
