"""
cBioPortal_get_copy_number_alterations

Get discrete copy-number alteration (CNA) calls per sample from GISTIC profiles for a gene in a c...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def cBioPortal_get_copy_number_alterations(
    study_id: str,
    gene_list: str,
    gene: Optional[str] = None,
    alteration_type: Optional[str] = "ALL",
    sample_list_id: Optional[str] = None,
    molecular_profile_id: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get discrete copy-number alteration (CNA) calls per sample from GISTIC profiles for a gene in a c...

    Parameters
    ----------
    study_id : str
        Cancer study ID (e.g., 'brca_tcga_pan_can_atlas_2018'). The discrete GISTIC p...
    gene_list : str
        Comma-separated gene symbols (e.g., 'ERBB2' or 'TP53,ERBB2')
    gene : str
        Alias for gene_list: comma-separated gene symbols
    alteration_type : str
        CNA category filter: 'AMP' (amplification), 'GAIN', 'DIPLOID', 'HETLOSS' (sha...
    sample_list_id : str
        Optional sample list ID. Defaults to '{study_id}_all'.
    molecular_profile_id : str
        Optional explicit GISTIC molecular profile ID (overrides auto-resolution).
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
            "study_id": study_id,
            "gene_list": gene_list,
            "gene": gene,
            "alteration_type": alteration_type,
            "sample_list_id": sample_list_id,
            "molecular_profile_id": molecular_profile_id,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "cBioPortal_get_copy_number_alterations",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["cBioPortal_get_copy_number_alterations"]
