"""
NvidiaNIM_maisi

Generate synthetic CT images with segmentation masks using MAISI via NVIDIA NIM. 3D Latent Diffus...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def NvidiaNIM_maisi(
    num_output_samples: int,
    body_region: list[str],
    anatomy_list: Optional[list[str]] = None,
    controllable_anatomy_size: Optional[list[Any]] = None,
    output_size: Optional[list[Any]] = None,
    spacing: Optional[list[Any]] = None,
    image_output_ext: Optional[str] = ".nii.gz",
    label_output_ext: Optional[str] = ".nii.gz",
    pre_signed_url: Optional[str] = "",
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> str:
    """
    Generate synthetic CT images with segmentation masks using MAISI via NVIDIA NIM. 3D Latent Diffus...

    Parameters
    ----------
    num_output_samples : int
        Number of CT images to generate
    body_region : list[str]
        Body regions to generate
    anatomy_list : list[str]
        Specific anatomical structures to include (e.g., liver, spleen, kidney)
    controllable_anatomy_size : list[Any]
        Control anatomy sizes as [[name, ratio], ...]. Example: [['hepatic tumor', 0....
    output_size : list[Any]
        Output volume size [x, y, z]. x,y: 256-512, z: 128-768
    spacing : list[Any]
        Voxel spacing [x, y, z] in mm
    image_output_ext : str
        Output image format
    label_output_ext : str
        Output segmentation format
    pre_signed_url : str
        Optional pre-signed URL to upload results to
    stream_callback : Callable, optional
        Callback for streaming output
    use_cache : bool, default False
        Enable caching
    validate : bool, default True
        Validate parameters

    Returns
    -------
    str
    """
    # Handle mutable defaults to avoid B006 linting error
    if output_size is None:
        output_size = [512, 512, 512]
    if spacing is None:
        spacing = [1.0, 1.0, 1.0]
    # Strip None values so optional parameters don't trigger schema validation errors
    _args = {
        k: v
        for k, v in {
            "num_output_samples": num_output_samples,
            "body_region": body_region,
            "anatomy_list": anatomy_list,
            "controllable_anatomy_size": controllable_anatomy_size,
            "output_size": output_size,
            "spacing": spacing,
            "image_output_ext": image_output_ext,
            "label_output_ext": label_output_ext,
            "pre_signed_url": pre_signed_url,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "NvidiaNIM_maisi",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["NvidiaNIM_maisi"]
