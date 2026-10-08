#!/usr/bin/env python3
"""Download BixBench capsule data from Hugging Face.

Downloads all capsule zip files from futurehouse/BixBench and extracts them
to the data directory. Skips capsules that already exist.

Usage:
    python skills/evals/bixbench/download_capsules.py
    python skills/evals/bixbench/download_capsules.py --data-dir /custom/path
"""

import argparse
import shutil
import stat
import sys
import tempfile
import zipfile
from pathlib import Path

DATA_DIR_DEFAULT = (
    Path(__file__).resolve().parent.parent.parent.parent
    / "temp_docs_and_tests"
    / "bixbench"
    / "bixbench"
    / "data"
)


def extract_capsule(archive, destination):
    """Only mark a complete, CRC-checked extraction as reusable."""
    destination = Path(destination)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix=".capsule-") as tmp:
        with zipfile.ZipFile(archive) as zf:
            for info in zf.infolist():
                path = Path(info.filename)
                if (
                    path.is_absolute()
                    or ".." in path.parts
                    or stat.S_ISLNK(info.external_attr >> 16)
                ):
                    raise ValueError(f"Unsafe capsule member: {info.filename}")
            bad = zf.testzip()
            if bad:
                raise ValueError(f"Corrupt capsule member: {bad}")
            zf.extractall(tmp)
        Path(tmp, ".complete").touch()
        if destination.exists():
            shutil.rmtree(destination)
        shutil.move(tmp, destination)


def main():
    parser = argparse.ArgumentParser(description="Download BixBench capsule data")
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=DATA_DIR_DEFAULT,
        help="Directory to store capsule data",
    )
    args = parser.parse_args()

    try:
        from huggingface_hub import hf_hub_download, list_repo_tree
    except ImportError:
        print("Install huggingface_hub: pip install huggingface_hub")
        return 1

    data_dir = args.data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    cache_dir = data_dir / ".cache"

    # Find existing capsules
    existing = {
        d.name
        for d in data_dir.iterdir()
        if d.is_dir()
        and d.name.startswith("CapsuleFolder-")
        and (d / ".complete").exists()
    }

    # List capsule zips in the HF repo
    files = list(list_repo_tree("futurehouse/BixBench", repo_type="dataset"))
    capsule_files = [
        f
        for f in files
        if f.path.startswith("CapsuleFolder-") and f.path.endswith(".zip")
    ]

    to_download = [
        f for f in capsule_files if f.path.replace(".zip", "") not in existing
    ]

    total_bytes = sum(f.size for f in to_download if hasattr(f, "size") and f.size)
    print(f"Existing: {len(existing)}, To download: {len(to_download)}")
    print(f"Total download size: {total_bytes / 1e6:.0f} MB")

    if not to_download:
        print("All capsules already downloaded.")
        return 0

    failed = []
    for i, f in enumerate(to_download, 1):
        size_mb = f.size / 1e6 if hasattr(f, "size") and f.size else 0
        print(f"[{i}/{len(to_download)}] {f.path} ({size_mb:.1f} MB)...", flush=True)
        try:
            local_path = hf_hub_download(
                "futurehouse/BixBench",
                f.path,
                repo_type="dataset",
                cache_dir=str(cache_dir),
            )
            folder_name = f.path.replace(".zip", "")
            extract_to = data_dir / folder_name
            extract_capsule(local_path, extract_to)
            print(f"  OK", flush=True)
        except Exception as e:
            print(f"  FAILED: {e}", flush=True)
            failed.append(f.path)

    final_count = sum(
        1
        for d in data_dir.iterdir()
        if d.is_dir() and d.name.startswith("CapsuleFolder-")
    )
    print(f"\nTotal capsules: {final_count}")
    if failed:
        print(f"Failed ({len(failed)}): {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
