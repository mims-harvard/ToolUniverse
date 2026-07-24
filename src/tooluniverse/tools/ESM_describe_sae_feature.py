"""
ESM_describe_sae_feature

Label a single SAE feature_id with its dominant biological category by aggregating UniProt featur...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ESM_describe_sae_feature(
    feature_id: int,
    sae_model: Optional[str] = "esmc-6b-2024-12_k64_codebook16384_layer60",
    model: Optional[str] = "esmc-6b-2024-12",
    n_proteins: Optional[int] = 10,
    top_residues_per_protein: Optional[int] = 3,
    use_cache_: Optional[bool] = True,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Label a single SAE feature_id with its dominant biological category by aggregating UniProt featur...

    Parameters
    ----------
    feature_id : int
        SAE feature index in [0, 16383]. Use the values returned by ESM_get_sae_featu...
    sae_model : str
        SAE checkpoint to label. Cache is keyed on this — different SAEs produce diff...
    model : str
        ESMC backbone.
    n_proteins : int
        Number of panel proteins to run SAE on. Default 10 (the full curated panel). ...
    top_residues_per_protein : int
        For each protein, take the top-K residues where the target feature activates ...
    use_cache_ : bool
        If true (default) and a cached label exists at ~/.cache/tooluniverse/sae_labe...
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
            "feature_id": feature_id,
            "sae_model": sae_model,
            "model": model,
            "n_proteins": n_proteins,
            "top_residues_per_protein": top_residues_per_protein,
            "use_cache": use_cache_,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ESM_describe_sae_feature",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ESM_describe_sae_feature"]
