"""
EnsemblVar_get_variant_consequences

Get detailed variant information including consequence type, clinical significance, synonyms, evi...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblVar_get_variant_consequences(
    variant_id: str,
    species: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get detailed variant information including consequence type, clinical significance, synonyms, evi...

    Parameters
    ----------
    variant_id : str
        dbSNP rsID of the variant. Examples: 'rs429358' (APOE), 'rs7903146' (TCF7L2),...
    species : str
        Species name. Default 'human'. Examples: 'human', 'homo_sapiens'.
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
            "name": "EnsemblVar_get_variant_consequences",
            "arguments": {"variant_id": variant_id, "species": species},
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblVar_get_variant_consequences"]
