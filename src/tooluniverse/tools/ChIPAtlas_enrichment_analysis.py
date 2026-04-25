"""
ChIPAtlas_enrichment_analysis

Perform enrichment analysis to identify transcription factors and histone modifications enriched ...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ChIPAtlas_enrichment_analysis(
    operation: Optional[str] = "enrichment_analysis",
    bed_data: Optional[str] = None,
    motif: Optional[str] = None,
    gene_list: Optional[list[str] | str] = None,
    genome: Optional[str] = "hg38",
    antigen_class: Optional[str] = None,
    cell_type_class: Optional[str] = None,
    threshold: Optional[str] = "05",
    distance: Optional[str] = "5000",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Perform enrichment analysis to identify transcription factors and histone modifications enriched ...

    Parameters
    ----------
    operation : str

    bed_data : str
        **Option 1**: BED format genomic regions (tab-separated: chr, start, end). Fo...
    motif : str
        **Option 2**: DNA sequence motif in IUPAC notation. Use: A/T/G/C (bases), W=A...
    gene_list : list[str] | str
        **Option 3**: Gene symbols (HGNC for human, MGI for mouse, RGD for rat, FlyBa...
    genome : str
        Genome assembly
    antigen_class : str
        Filter by antigen class (e.g., 'TFs and others', 'Histone', 'RNA polymerase')
    cell_type_class : str
        Filter by cell type class (e.g., 'Blood', 'Liver', 'Brain')
    threshold : str
        Peak calling stringency (MACS2 Q-value). Options: '05'=1e-5 (permissive, more...
    distance : str
        Distance from Transcription Start Site (TSS) in base pairs for gene-TF associ...
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
            "bed_data": bed_data,
            "motif": motif,
            "gene_list": gene_list,
            "genome": genome,
            "antigen_class": antigen_class,
            "cell_type_class": cell_type_class,
            "threshold": threshold,
            "distance": distance,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ChIPAtlas_enrichment_analysis",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ChIPAtlas_enrichment_analysis"]
