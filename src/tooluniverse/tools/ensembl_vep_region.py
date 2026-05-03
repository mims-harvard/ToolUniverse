"""
ensembl_vep_region

Variant Effect Predictor (VEP) for genomic variants. Predicts functional consequences of variants...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def ensembl_vep_region(
    species: str,
    region: str,
    allele: str,
    AncestralAllele: Optional[int] = 0,
    Blosum62: Optional[int] = 0,
    CADD: Optional[int] = 0,
    Conservation: Optional[int] = 0,
    DisGeNET: Optional[int] = 0,
    GeneSplicer: Optional[int] = 0,
    GO: Optional[int] = 0,
    LoF: Optional[int] = 0,
    MaxEntScan: Optional[int] = 0,
    Phenotypes: Optional[int] = 0,
    SIFT: Optional[str] = None,
    PolyPhen: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> list[Any]:
    """
    Variant Effect Predictor (VEP) for genomic variants. Predicts functional consequences of variants...

    Parameters
    ----------
    species : str
        Species (e.g., 'human', 'homo_sapiens')
    region : str
        Genomic region with variant (e.g., '21:25891796-25891796')
    allele : str
        Alternative allele (e.g., 'T', 'C')
    AncestralAllele : int
        Include ancestral allele information
    Blosum62 : int
        Include BLOSUM62 protein conservation score
    CADD : int
        Include CADD scores
    Conservation : int
        Include conservation scores
    DisGeNET : int
        Include DisGeNET disease associations
    GeneSplicer : int
        Include GeneSplicer predictions
    GO : int
        Include Gene Ontology terms
    LoF : int
        Include Loss-of-Function predictions
    MaxEntScan : int
        Include MaxEntScan splice predictions
    Phenotypes : int
        Include phenotype annotations
    SIFT : str
        SIFT prediction: p=prediction, s=score, b=both
    PolyPhen : str
        PolyPhen prediction: p=prediction, s=score, b=both
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    list[Any]
    """
    # Handle mutable defaults to avoid B006 linting error

    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "species": species,
            "region": region,
            "allele": allele,
            "AncestralAllele": AncestralAllele,
            "Blosum62": Blosum62,
            "CADD": CADD,
            "Conservation": Conservation,
            "DisGeNET": DisGeNET,
            "GeneSplicer": GeneSplicer,
            "GO": GO,
            "LoF": LoF,
            "MaxEntScan": MaxEntScan,
            "Phenotypes": Phenotypes,
            "SIFT": SIFT,
            "PolyPhen": PolyPhen,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "ensembl_vep_region",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["ensembl_vep_region"]
