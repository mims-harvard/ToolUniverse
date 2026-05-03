"""
EnsemblVEP_annotate_rsid

Predict functional consequences of a genetic variant using its dbSNP rs identifier via the Ensemb...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblVEP_annotate_rsid(
    variant_id: Optional[str] = None,
    rsid: Optional[str] = None,
    rs_id: Optional[str] = None,
    species: Optional[str] = "human",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict functional consequences of a genetic variant using its dbSNP rs identifier via the Ensemb...

    Parameters
    ----------
    variant_id : str
        dbSNP rs identifier. Examples: 'rs7903146' (TCF7L2, type 2 diabetes), 'rs4293...
    rsid : str
        Alias for variant_id. dbSNP rs identifier (e.g., 'rs7903146').
    rs_id : str
        Alias for variant_id. dbSNP rs identifier (e.g., 'rs7903146').
    species : str
        Species name. Default: 'human'.
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
            "variant_id": variant_id,
            "rsid": rsid,
            "rs_id": rs_id,
            "species": species,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblVEP_annotate_rsid",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblVEP_annotate_rsid"]
