"""
EnsemblVEP_variant_recoder

Convert genetic variant identifiers between different nomenclature formats using the Ensembl Vari...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblVEP_variant_recoder(
    variant_id: str,
    species: Optional[str] = "human",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Convert genetic variant identifiers between different nomenclature formats using the Ensembl Vari...

    Parameters
    ----------
    variant_id : str
        Variant identifier to recode. Accepts: rsID (e.g., 'rs429358'), HGVS notation...
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
        for k, v in {"variant_id": variant_id, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblVEP_variant_recoder",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblVEP_variant_recoder"]
