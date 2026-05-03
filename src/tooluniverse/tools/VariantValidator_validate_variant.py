"""
VariantValidator_validate_variant

Validate and convert genetic variant descriptions using VariantValidator. Takes HGVS-formatted va...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VariantValidator_validate_variant(
    genome_build: str,
    variant_description: str,
    select_transcripts: str,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Validate and convert genetic variant descriptions using VariantValidator. Takes HGVS-formatted va...

    Parameters
    ----------
    genome_build : str
        Reference genome assembly: 'GRCh37' (hg19) or 'GRCh38' (hg38)
    variant_description : str
        HGVS variant description (e.g., 'NM_007294.4:c.5266dup' for BRCA1 c.5266dupC,...
    select_transcripts : str
        Transcript to validate against (e.g., 'NM_007294.4'). Use 'all' to get all tr...
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
            "genome_build": genome_build,
            "variant_description": variant_description,
            "select_transcripts": select_transcripts,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VariantValidator_validate_variant",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VariantValidator_validate_variant"]
