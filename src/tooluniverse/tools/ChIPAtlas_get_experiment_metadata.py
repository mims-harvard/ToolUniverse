"""
ChIPAtlas_get_experiment_metadata

ChIP-Atlas single-experiment structured metadata: given one experiment accession (SRX/DRX/ERX), r...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_get_experiment_metadata(
    experiment_id: str,
    operation: Optional[str] = "get_experiment_metadata",
    genome: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    ChIP-Atlas single-experiment structured metadata: given one experiment accession (SRX/DRX/ERX), r...

    Parameters
    ----------
    operation : str

    experiment_id : str
        Experiment accession in SRX/DRX/ERX format (e.g. 'SRX080331').
    genome : str
        Optional: restrict to one genome assembly (an experiment can have records for...
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
            "operation": operation,
            "experiment_id": experiment_id,
            "genome": genome,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_get_experiment_metadata",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_get_experiment_metadata"]
