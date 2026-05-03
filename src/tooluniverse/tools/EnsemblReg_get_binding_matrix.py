"""
EnsemblReg_get_binding_matrix

Get a transcription factor binding matrix (position weight matrix/PWM) by stable ID from the Ense...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblReg_get_binding_matrix(
    binding_matrix_id: str,
    species: Optional[str] = "homo_sapiens",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get a transcription factor binding matrix (position weight matrix/PWM) by stable ID from the Ense...

    Parameters
    ----------
    species : str
        Species name. Use 'homo_sapiens' for human. Default: 'homo_sapiens'.
    binding_matrix_id : str
        Ensembl binding matrix stable ID. Format: 'ENSPFM0XXX'. Examples: 'ENSPFM0320...
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
        for k, v in {"species": species, "binding_matrix_id": binding_matrix_id}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblReg_get_binding_matrix",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblReg_get_binding_matrix"]
