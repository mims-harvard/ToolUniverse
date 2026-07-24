"""
SPrediXcan_associate

Summary-based transcriptome-wide association (S-PrediXcan, Barbeira 2018): test a gene for trait ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def SPrediXcan_associate(
    weight: list[Any],
    gwas_z: list[Any],
    snp_sd: Optional[list[Any]] = None,
    covariance: Optional[list[Any]] = None,
    snp: Optional[list[str]] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Summary-based transcriptome-wide association (S-PrediXcan, Barbeira 2018): test a gene for trait ...

    Parameters
    ----------
    weight : list[Any]
        Per-SNP eQTL prediction weights for the gene (same SNP order as gwas_z).
    gwas_z : list[Any]
        Per-SNP GWAS z-scores (beta/se), same SNP order.
    snp_sd : list[Any]
        Per-SNP standard deviation (~sqrt(2*MAF*(1-MAF))); default 1.0 (standardized).
    covariance : list[Any]
        Optional SNP covariance matrix (n x n, same SNP order). If omitted, SNPs are ...
    snp : list[str]
        Optional SNP identifiers (same order), for reference.
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
            "weight": weight,
            "gwas_z": gwas_z,
            "snp_sd": snp_sd,
            "covariance": covariance,
            "snp": snp,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "SPrediXcan_associate",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["SPrediXcan_associate"]
