"""
AlphaGenome_predict_interval

Predict multimodal genomic tracks for a genomic interval with DeepMind AlphaGenome (single DNA-se...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def AlphaGenome_predict_interval(
    chromosome: str,
    start: int,
    end: int,
    output_types: Optional[list[str]] = None,
    ontology_terms: Optional[list[str]] = None,
    organism: Optional[str] = None,
    sequence_length: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> Any:
    """
    Predict multimodal genomic tracks for a genomic interval with DeepMind AlphaGenome (single DNA-se...

    Parameters
    ----------
    chromosome : str
        Chromosome, e.g. 'chr19'.
    start : int
        Interval start (0-based).
    end : int
        Interval end.
    output_types : list[str]
        Modalities to predict, e.g. ['RNA_SEQ','ATAC'] (default ['RNA_SEQ']).
    ontology_terms : list[str]
        Optional tissue/cell ontology terms (e.g. ['UBERON:0001114'] = liver) to rest...
    organism : str
        'human' (default) or 'mouse'.
    sequence_length : str
        Context window: 16KB, 100KB, 500KB, or 1MB (default).
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
            "chromosome": chromosome,
            "start": start,
            "end": end,
            "output_types": output_types,
            "ontology_terms": ontology_terms,
            "organism": organism,
            "sequence_length": sequence_length,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "AlphaGenome_predict_interval",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["AlphaGenome_predict_interval"]
