"""
SpliceAI_predict_splice

Predict splice-altering effects using SpliceAI deep learning model. Returns delta scores for acce...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SpliceAI_predict_splice(
    variant: str,
    genome: Optional[str] = "38",
    distance: Optional[int] = 50,
    mask: Optional[bool] = False,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict splice-altering effects using SpliceAI deep learning model. Returns delta scores for acce...

    Parameters
    ----------
    variant : str
        Variant in chr-pos-ref-alt format (e.g., chr8-140300616-T-G) or colon-separated
    genome : str
        Genome build: 37 (GRCh37/hg19) or 38 (GRCh38/hg38). Default: 38
    distance : int
        Distance parameter for model (default: 50). Larger values capture more distal...
    mask : bool
        Use masked scores (recommended for variant interpretation). Raw scores better...
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    dict[str, Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "variant": variant,
            "genome": genome,
            "distance": distance,
            "mask": mask,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SpliceAI_predict_splice",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SpliceAI_predict_splice"]
