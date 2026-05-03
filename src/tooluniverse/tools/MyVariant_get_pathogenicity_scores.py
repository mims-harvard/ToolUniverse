"""
MyVariant_get_pathogenicity_scores

Get comprehensive pathogenicity prediction scores for a variant from dbNSFP. Returns REVEL, CADD,...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def MyVariant_get_pathogenicity_scores(
    variant_id: str,
    fields: Optional[
        str
    ] = "dbnsfp.revel.score,dbnsfp.cadd.phred,dbnsfp.alphamissense.score,dbnsfp.alphamissense.pred,dbnsfp.sift.score,dbnsfp.sift.pred,dbnsfp.polyphen2_hdiv.score,dbnsfp.polyphen2_hdiv.pred,dbnsfp.metarnn.score,dbnsfp.metarnn.pred,dbnsfp.gerp_rs,dbnsfp.phylop100way_vertebrate.rankscore,dbnsfp.phastcons100way_vertebrate.rankscore,dbnsfp.vest4.score,dbnsfp.mutationtaster.pred,clinvar.rcv.clinical_significance,dbsnp.rsid",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get comprehensive pathogenicity prediction scores for a variant from dbNSFP. Returns REVEL, CADD,...

    Parameters
    ----------
    variant_id : str
        Variant ID: rsID (e.g., rs45478192) or HGVS genomic (e.g., chr16:g.23635348A>...
    fields : str
        Fields to return (pre-configured for pathogenicity scores)
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
        for k, v in {"variant_id": variant_id, "fields": fields}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "MyVariant_get_pathogenicity_scores",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["MyVariant_get_pathogenicity_scores"]
