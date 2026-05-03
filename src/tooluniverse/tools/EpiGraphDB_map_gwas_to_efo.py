"""
EpiGraphDB_map_gwas_to_efo

Map GWAS trait names to EFO (Experimental Factor Ontology) terms for standardization. Returns EFO...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EpiGraphDB_map_gwas_to_efo(
    trait: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Map GWAS trait names to EFO (Experimental Factor Ontology) terms for standardization. Returns EFO...

    Parameters
    ----------
    trait : str
        GWAS trait name to map to EFO (e.g., 'Body mass index', 'coronary artery dise...
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
    _args = {k: v for k, v in {"trait": trait}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "EpiGraphDB_map_gwas_to_efo",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EpiGraphDB_map_gwas_to_efo"]
