#!/usr/bin/env python3
"""Preflight environment check for running nf-core pipelines.

Checks Docker, Nextflow, Java (required) and sra-tools (optional, only
needed for SRA-accession downloads). Never fabricates a result: every check
either passes with real evidence (a version string actually printed by the
tool) or fails with a concrete fix instruction. Exits non-zero if any
REQUIRED check fails.
"""

import platform
import re
import shutil
import subprocess
import sys

MIN_NEXTFLOW = (23, 4)
MIN_JAVA = 11


def run(cmd):
    """Run a command, return (rc, stdout+stderr) without raising."""
    try:
        p = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30, check=False
        )
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, ""
    except subprocess.TimeoutExpired:
        return 124, "(timed out)"


def is_linux():
    return platform.system() == "Linux"


def check_docker():
    path = shutil.which("docker")
    if not path:
        return False, "Docker is not installed.", docker_install_hint()
    rc, out = run(["docker", "info"])
    if rc != 0:
        return (
            False,
            "Docker binary found but the daemon is not reachable.",
            "Daemon not running or no permission:\n"
            "  sudo systemctl start docker\n"
            "  # if 'permission denied' talking to the docker socket:\n"
            "  sudo usermod -aG docker $USER   # then log out and back in\n"
            f"(docker info said: {out.splitlines()[0] if out else '<no output>'})",
        )
    return True, f"Docker OK ({path}), daemon reachable.", None


def docker_install_hint():
    if is_linux():
        return (
            "Install Docker Engine (Linux):\n"
            "  curl -fsSL https://get.docker.com | sh\n"
            "  sudo usermod -aG docker $USER   # then log out and back in\n"
            "See https://docs.docker.com/engine/install/ for distro-specific steps.\n"
            "If you cannot get root/sudo (e.g. a locked-down sandbox), Docker cannot "
            "be installed here — this skill cannot run a real pipeline in that case."
        )
    return "Install Docker Desktop: https://docs.docker.com/get-docker/"


def check_nextflow():
    path = shutil.which("nextflow")
    if not path:
        return (
            False,
            "Nextflow is not installed.",
            "Install Nextflow:\n"
            "  curl -s https://get.nextflow.io | bash\n"
            "  mkdir -p ~/bin && mv nextflow ~/bin/\n"
            "  export PATH=\"$HOME/bin:$PATH\"   # add to ~/.bashrc too",
        )
    rc, out = run(["nextflow", "-version"])
    m = re.search(r"version\s+(\d+)\.(\d+)", out)
    if not m:
        return (
            False,
            f"Nextflow found ({path}) but version could not be parsed from: {out!r}",
            "Try: nextflow self-update",
        )
    ver = (int(m.group(1)), int(m.group(2)))
    if ver < MIN_NEXTFLOW:
        return (
            False,
            f"Nextflow {ver[0]}.{ver[1]:02d} found, but >= "
            f"{MIN_NEXTFLOW[0]}.{MIN_NEXTFLOW[1]:02d} is required.",
            "Update: nextflow self-update",
        )
    return True, f"Nextflow {ver[0]}.{ver[1]:02d} OK ({path}).", None


def check_java():
    path = shutil.which("java")
    if not path:
        return (
            False,
            "Java is not installed (required by Nextflow).",
            "Install OpenJDK 11+ (Linux, Debian/Ubuntu):\n"
            "  sudo apt-get update && sudo apt-get install -y openjdk-17-jre-headless\n"
            "Other distros: use your package manager to install a JRE >= 11, "
            "or a user-local install via https://adoptium.net/ if you lack sudo.",
        )
    rc, out = run(["java", "-version"])
    # java -version prints to stderr, format varies: 'openjdk version "17.0.9"'
    m = re.search(r'version "(\d+)(?:\.(\d+))?', out)
    if not m:
        return (
            False,
            f"Java found ({path}) but version could not be parsed from: {out!r}",
            "Verify manually with: java -version",
        )
    major = int(m.group(1))
    # legacy versioning: "1.8.0_xxx" reports major=1 -> treat second group as major
    if major == 1 and m.group(2):
        major = int(m.group(2))
    if major < MIN_JAVA:
        return (
            False,
            f"Java {major} found, but >= {MIN_JAVA} is required.",
            "Install a newer JRE (see Docker/Nextflow install notes above) and "
            "ensure it is first on PATH, or set NXF_JAVA_HOME.",
        )
    return True, f"Java {major} OK ({path}).", None


def check_sra_tools():
    prefetch = shutil.which("prefetch")
    fasterq = shutil.which("fasterq-dump")
    if prefetch and fasterq:
        return True, f"sra-tools OK (prefetch={prefetch}, fasterq-dump={fasterq}).", None
    return (
        False,
        "sra-tools (prefetch / fasterq-dump) not found.",
        "Only needed if downloading SRA data BY ACCESSION rather than by direct "
        "URL (see references/geo_sra_acquisition.md). Install via bioconda:\n"
        "  mamba install -c bioconda -c conda-forge sra-tools\n"
        "  # or conda install -c bioconda -c conda-forge sra-tools",
    )


def main():
    checks = [
        ("Docker", check_docker, True),
        ("Nextflow", check_nextflow, True),
        ("Java", check_java, True),
        ("sra-tools (optional)", check_sra_tools, False),
    ]

    print(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print("-" * 60)

    all_required_pass = True
    for label, fn, required in checks:
        ok, msg, fix = fn()
        status = "PASS" if ok else ("FAIL" if required else "WARN (optional)")
        print(f"[{status}] {label}: {msg}")
        if not ok and fix:
            print("  Fix:")
            for line in fix.splitlines():
                print(f"    {line}")
        if not ok and required:
            all_required_pass = False
        print()

    print("-" * 60)
    if all_required_pass:
        print("All required checks passed. Safe to proceed to Step 2 (select pipeline).")
        return 0
    print(
        "One or more REQUIRED checks failed. Do NOT proceed to run a pipeline — "
        "fix the issues above first. Report this status to the user verbatim; "
        "do not simulate or estimate pipeline output in this state."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
