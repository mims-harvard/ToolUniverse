"""Isolated optional pKAI backend; installed packaged weights only, CPU only."""

import contextlib
import hashlib
import importlib.metadata
import io
import json
import os
import sys
from pathlib import Path


def predict(request):
    os.environ["CUDA_VISIBLE_DEVICES"] = ""
    try:
        import pkai
        import torch
        from pkai.pKAI import pKAI
    except ImportError:
        return {
            "status": "error",
            "error": "Optional pKAI/torch dependency missing in python_executable; install pKAI in an isolated environment",
        }
    variant = request["model_variant"]
    checkpoint = Path(pkai.__file__).parent / "models" / (variant + "_model.pt")
    if not checkpoint.is_file():
        return {
            "status": "error",
            "error": "Packaged pKAI checkpoint missing; this tool never downloads model weights",
        }
    with contextlib.redirect_stdout(io.StringIO()), torch.inference_mode():
        values = pKAI(
            request["pdb_path"],
            model_name=variant,
            device="cpu",
            threads=request["threads"],
        )
    groups = [
        {"chain": c, "residue_number": int(n), "residue_name": r, "pka": float(v)}
        for c, n, r, v in values
    ]
    return {
        "status": "success",
        "data": {
            "model_variant": variant,
            "groups": groups,
            "backend": {
                "package": "pkai",
                "package_version": importlib.metadata.version("pkai"),
                "torch_version": torch.__version__,
                "device": "cpu",
                "checkpoint_sha256": hashlib.sha256(
                    checkpoint.read_bytes()
                ).hexdigest(),
                "model_download_performed": False,
            },
            "pka_decimal_places": 2,
        },
    }


def main():
    request, output = map(Path, sys.argv[1:3])
    try:
        result = predict(json.loads(request.read_text()))
    except Exception as exc:
        result = {"status": "error", "error": str(exc)}
    output.write_text(json.dumps(result, allow_nan=False))


if __name__ == "__main__":
    main()
