"""
HPA_get_comprehensive_gene_details_by_ensembl_id

Get detailed in-depth information from gene page using Ensembl Gene ID, including image URLs, ant...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def HPA_get_comprehensive_gene_details_by_ensembl_id(
    ensembl_id: str,
    include_images: bool,
    include_antibodies: bool,
    include_expression: bool,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Get detailed in-depth information from gene page using Ensembl Gene ID, including image URLs, ant...

    Parameters
    ----------
    ensembl_id : str
        Ensembl Gene ID, e.g., 'ENSG00000064787' (BCAS1), 'ENSG00000141510' (TP53), e...
    include_images : bool
        Whether to include image URL information (immunofluorescence, cell line image...
    include_antibodies : bool
        Whether to include detailed antibody information (validation status, Western ...
    include_expression : bool
        Whether to include detailed expression data (tissue specificity, subcellular ...
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
            "ensembl_id": ensembl_id,
            "include_images": include_images,
            "include_antibodies": include_antibodies,
            "include_expression": include_expression,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "HPA_get_comprehensive_gene_details_by_ensembl_id",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["HPA_get_comprehensive_gene_details_by_ensembl_id"]
