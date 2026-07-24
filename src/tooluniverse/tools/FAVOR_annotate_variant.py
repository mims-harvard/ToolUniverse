"""
FAVOR_annotate_variant

Comprehensive functional annotation of a single GRCh38 variant via FAVOR (Functional Annotation o...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def FAVOR_annotate_variant(
    variant: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Comprehensive functional annotation of a single GRCh38 variant via FAVOR (Functional Annotation o...

    Parameters
    ----------
    variant : str
        GRCh38 SNV/indel as chr-pos-ref-alt. Accepts '19-44908822-C-T', 'chr19:449088...
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
    _args = {k: v for k, v in {"variant": variant}.items() if v is not None}
    return get_shared_client().run_one_function(
        {
            "name": "FAVOR_annotate_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["FAVOR_annotate_variant"]
