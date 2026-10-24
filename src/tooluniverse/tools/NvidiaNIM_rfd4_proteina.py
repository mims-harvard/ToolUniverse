"""
NvidiaNIM_rfd4_proteina

De novo biomolecular design with RFD4-Proteina (NVIDIA + UW Institute for Protein Design) via NVI...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_rfd4_proteina(
    task: str,
    input: dict[str, Any],
    sampling: Optional[dict[str, Any]] = None,
    metrics: Optional[dict[str, Any]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    De novo biomolecular design with RFD4-Proteina (NVIDIA + UW Institute for Protein Design) via NVI...

    Parameters
    ----------
    task : str
        How the sampler runs the trajectory. Ask the deployment which tasks it serves...
    input : dict[str, Any]
        The design specification: a named structure file carried inline in the reques...
    sampling : dict[str, Any]
        Sampler budget. The three recycle schedules differ only in trunk passes over ...
    metrics : dict[str, Any]
        Which in-repository metrics to compute. Oracle-backed refolding metrics need ...
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
            "task": task,
            "input": input,
            "sampling": sampling,
            "metrics": metrics,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_rfd4_proteina",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_rfd4_proteina"]
