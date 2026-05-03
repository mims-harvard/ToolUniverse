"""
EnsemblVar_get_population_frequencies

Get allele frequency data for a variant (SNP/indel) across global populations from gnomAD and 100...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def EnsemblVar_get_population_frequencies(
    variant_id: str,
    species: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Get allele frequency data for a variant (SNP/indel) across global populations from gnomAD and 100...

    Parameters
    ----------
    variant_id : str
        dbSNP rsID of the variant. Examples: 'rs429358' (APOE), 'rs7903146' (TCF7L2),...
    species : str
        Species name. Default 'human'. Examples: 'human', 'homo_sapiens'.
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
        for k, v in {"variant_id": variant_id, "species": species}.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "EnsemblVar_get_population_frequencies",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["EnsemblVar_get_population_frequencies"]
