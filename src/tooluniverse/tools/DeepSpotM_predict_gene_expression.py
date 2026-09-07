"""
DeepSpotM_predict_gene_expression

Predict spatial gene expression for a single H&E histology tile LOCALLY using the DeepSpot-M mult...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def DeepSpotM_predict_gene_expression(
    image_path: str,
    genes: list[str] | str,
    source: Optional[str] = None,
    device: Optional[str] = None,
    model_repo: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Predict spatial gene expression for a single H&E histology tile LOCALLY using the DeepSpot-M mult...

    Parameters
    ----------
    image_path : str
        Path to a local 224x224 H&E histology tile (.png, .tif, .tiff, .jpg, .jpeg). ...
    genes : list[str] | str
        Gene symbol(s) to predict, for example ['EPCAM', 'CD3D', 'PTPRC']. Required: ...
    source : str
        Which frozen gene-embedding source to query the decoder with. Default 'scgpt'.
    device : str
        Torch device, for example 'cuda' or 'cpu'. Default 'auto', which uses CUDA wh...
    model_repo : str
        Hugging Face repo or local directory holding the checkpoint. Defaults to 'rat...
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
            "image_path": image_path,
            "genes": genes,
            "source": source,
            "device": device,
            "model_repo": model_repo,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "DeepSpotM_predict_gene_expression",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["DeepSpotM_predict_gene_expression"]
