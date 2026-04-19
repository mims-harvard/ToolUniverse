#!/usr/bin/env python3
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


DOCS_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = DOCS_DIR / "_build" / "html"
EN_DIR = OUTPUT_ROOT / "en"
ZH_DIR = OUTPUT_ROOT / "zh-CN"
EXCLUDED_ROOT_ITEMS = {"en", "zh-CN", ".doctrees"}


def copy_root_to_en() -> None:
    if EN_DIR.exists():
        shutil.rmtree(EN_DIR)
    EN_DIR.mkdir(parents=True, exist_ok=True)

    for item in OUTPUT_ROOT.iterdir():
        if item.name in EXCLUDED_ROOT_ITEMS:
            continue
        target = EN_DIR / item.name
        if item.is_dir():
            shutil.copytree(item, target, dirs_exist_ok=True)
        else:
            shutil.copy2(item, target)


def build_zh_docs() -> None:
    cmd = [
        sys.executable,
        "-m",
        "sphinx",
        "-b",
        "html",
        "-D",
        "language=zh_CN",
        str(DOCS_DIR),
        str(ZH_DIR),
        "--keep-going",
        "-q",
    ]
    subprocess.run(cmd, cwd=DOCS_DIR, check=True)


def main() -> int:
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    copy_root_to_en()

    try:
        build_zh_docs()
    except subprocess.CalledProcessError as exc:
        print(f"[post-build] zh-CN build failed: {exc}", file=sys.stderr)
        return 0

    print("[post-build] synced /en and rebuilt /zh-CN")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
