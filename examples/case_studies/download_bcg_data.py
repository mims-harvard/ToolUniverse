#!/usr/bin/env python3
"""Download the public BCG-CORONA trial tables used by Case 3.

Source: https://zenodo.org/records/12737228 (CC0-1.0)
"Safety and efficacy of BCG re-vaccination in relation to COVID-19 morbidity
in healthcare workers: A double-blind, randomised, controlled, phase 3 trial."

Downloads ~4 MB and extracts the SDTM CSV tables next to this script.

Run:
    python download_bcg_data.py [--dest DIR]
"""

from __future__ import annotations

import argparse
import sys
import urllib.request
import zipfile
from pathlib import Path

ZENODO_RECORD = "https://zenodo.org/records/12737228"
ARCHIVE_URL = (
    "https://zenodo.org/api/records/12737228/files/"
    "TASK008-BCG_CORONA_SDTM_datasets_V5.zip/content"
)
# The two tables Case 3 needs.
DM_FILE = "TASK008_BCG-CORONA_DM.csv"
AE_FILE = "TASK008_BCG-CORONA_AE.csv"


def download(dest: Path) -> Path:
    dest.mkdir(parents=True, exist_ok=True)
    dm, ae = dest / DM_FILE, dest / AE_FILE
    if dm.exists() and ae.exists():
        print(f"Already present in {dest}:\n  {DM_FILE}\n  {AE_FILE}")
        return dest

    archive = dest / "TASK008-BCG_CORONA_SDTM_datasets_V5.zip"
    print(f"Downloading from {ZENODO_RECORD} ...")
    urllib.request.urlretrieve(ARCHIVE_URL, archive)
    print(f"  got {archive.stat().st_size / 1e6:.1f} MB")

    with zipfile.ZipFile(archive) as zf:
        zf.extractall(dest)
    archive.unlink()

    missing = [f for f in (DM_FILE, AE_FILE) if not (dest / f).exists()]
    if missing:
        print(
            f"ERROR: expected files missing after extract: {missing}", file=sys.stderr
        )
        raise SystemExit(1)

    print(f"Extracted to {dest}:\n  {DM_FILE}\n  {AE_FILE}")
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dest",
        type=Path,
        default=Path(__file__).parent / "data",
        help="Directory to download into (default: ./data)",
    )
    args = parser.parse_args()
    download(args.dest)


if __name__ == "__main__":
    main()
