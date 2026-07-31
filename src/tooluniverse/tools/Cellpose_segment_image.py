"""
Cellpose_segment_image

Segment cells or nuclei in a single microscopy image LOCALLY using the deep-learning Cellpose mod...
"""

from typing import Any, Optional, Callable
from ._shared_client import get_shared_client


def Cellpose_segment_image(
    image_path: str,
    model_type: Optional[str] = None,
    diameter: Optional[float] = None,
    channels: Optional[list[Any]] = None,
    save_mask: Optional[bool] = None,
    mask_output_path: Optional[str] = None,
    *,
    stream_callback: Optional[Callable[[str], None]] = None,
    use_cache: bool = False,
    validate: bool = True,
) -> dict[str, Any]:
    """
    Segment cells or nuclei in a single microscopy image LOCALLY using the deep-learning Cellpose mod...

    Parameters
    ----------
    image_path : str
        Path to a local microscopy image file (.tif, .tiff, .png, .jpg, .jpeg, .bmp).
    model_type : str
        Cellpose model to use. 'cyto3'/'cyto'/'cyto2' for cells/cytoplasm, 'nuclei' f...
    diameter : float
        Expected object diameter in pixels. Omit or 0 to let cellpose estimate it aut...
    channels : list[Any]
        Two-element [cytoplasm, nucleus] channel spec. Use [0,0] for a grayscale imag...
    save_mask : bool
        If true, save the integer label mask as a 16-bit PNG and return its path. Def...
    mask_output_path : str
        Where to write the mask when save_mask is true. Defaults to '<image_path>_cp_...
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
            "model_type": model_type,
            "diameter": diameter,
            "channels": channels,
            "save_mask": save_mask,
            "mask_output_path": mask_output_path,
        }.items()
        if v is not None
    }
    return get_shared_client().run_one_function(
        {
            "name": "Cellpose_segment_image",
            "arguments": _args,
        },
        stream_callback=stream_callback,
        use_cache=use_cache,
        validate=validate,
    )


__all__ = ["Cellpose_segment_image"]
