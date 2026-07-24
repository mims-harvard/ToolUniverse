"""
VCF_normalize

Normalize a local VCF/BCF with bcftools norm (split or join multiallelics; left-align indels agai...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def VCF_normalize(
    operation: str,
    vcf_path: str,
    multiallelics: Optional[str] = None,
    reference_fasta: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Normalize a local VCF/BCF with bcftools norm (split or join multiallelics; left-align indels agai...

    Parameters
    ----------
    operation : str
        Operation (fixed)
    vcf_path : str
        Path to a local .vcf, .vcf.gz, or .bcf file
    multiallelics : str
        'split' (default) breaks multiallelic records into biallelic; 'join' merges; ...
    reference_fasta : str
        Optional reference FASTA path; enables indel left-alignment (-f)
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
            "operation": operation,
            "vcf_path": vcf_path,
            "multiallelics": multiallelics,
            "reference_fasta": reference_fasta,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "VCF_normalize",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["VCF_normalize"]
