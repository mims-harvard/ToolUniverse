"""
DNA_golden_gate_assemble

Work out the product of a Golden Gate reaction that has already been performed: given the plasmid...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DNA_golden_gate_assemble(
    fragments: list[str],
    operation: Optional[str] = "golden_gate_assemble",
    enzyme: Optional[str] = "BsaI",
    circular: Optional[bool] = True,
    labels: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Work out the product of a Golden Gate reaction that has already been performed: given the plasmid...

    Parameters
    ----------
    operation : str
        Operation (optional; defaults to 'golden_gate_assemble' for this tool).
    fragments : list[str]
        The DNA sequences combined in the reaction (plasmids or linear parts), A/T/G/...
    enzyme : str
        Type IIS enzyme used in the reaction, e.g. 'BsaI' (default), 'BbsI', 'Esp3I'/...
    circular : bool
        Whether the inputs are circular plasmids (default true). Set false for linear...
    labels : list[str]
        Optional names for the inputs (e.g. plasmid names), echoed in the assembly or...
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
            "fragments": fragments,
            "enzyme": enzyme,
            "circular": circular,
            "labels": labels,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DNA_golden_gate_assemble",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DNA_golden_gate_assemble"]
