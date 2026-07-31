"""
GeneBe_classify_variants_batch

Batch-classify up to 1000 germline variants under the ACMG/AMP guidelines in a single GeneBe (gen...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def GeneBe_classify_variants_batch(
    variants: list[Any],
    genome: Optional[str] = "hg38",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Batch-classify up to 1000 germline variants under the ACMG/AMP guidelines in a single GeneBe (gen...

    Parameters
    ----------
    variants : list[Any]
        List of variants to classify (max 1000). Each item is an object with chr, pos...
    genome : str
        Genome build for ALL variants in the batch: 'hg38' (default) / 'GRCh38' or 'h...
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
        for k, v in {"variants": variants, "genome": genome}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "GeneBe_classify_variants_batch",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["GeneBe_classify_variants_batch"]
