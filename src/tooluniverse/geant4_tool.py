"""GEANT4 depth-dose simulation, through one fixed application.

A general GEANT4 tool would mean handing a caller a geometry language, a
physics list and a macro file -- an arbitrary-code surface. This tool instead
ships a single application (``data/geant4/depth_dose.cc``): a beam fired into
a slab of one NIST material, scored in equal depth bins. Only the numbers
below vary, so there is nothing to inject.

The application is compiled on first use against whatever GEANT4 the operator
installed, and cached under ``~/.tooluniverse/geant4`` keyed by the source and
the toolkit version, so a toolkit upgrade rebuilds rather than silently
running a stale binary.
"""

import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool

# Particles the shipped application can fire. G4ParticleGun would accept more,
# but each name here is one whose physics the QBBC list covers well and whose
# depth-dose profile means something.
_PARTICLES = (
    "proton",
    "neutron",
    "e-",
    "e+",
    "gamma",
    "alpha",
    "mu-",
    "mu+",
    "pi-",
    "pi+",
    "deuteron",
    "triton",
    "He3",
    "C12",
    "O16",
)

# NIST material names, which G4NistManager builds without a geometry file.
_MATERIALS = (
    "G4_WATER",
    "G4_AIR",
    "G4_A-150_TISSUE",
    "G4_ADIPOSE_TISSUE_ICRP",
    "G4_BONE_COMPACT_ICRU",
    "G4_BONE_CORTICAL_ICRP",
    "G4_BRAIN_ICRP",
    "G4_LUNG_ICRP",
    "G4_MUSCLE_SKELETAL_ICRP",
    "G4_SKIN_ICRP",
    "G4_TISSUE_SOFT_ICRP",
    "G4_PMMA",
    "G4_POLYETHYLENE",
    "G4_POLYSTYRENE",
    "G4_GRAPHITE",
    "G4_ALUMINUM_OXIDE",
    "G4_Al",
    "G4_Si",
    "G4_Ti",
    "G4_Fe",
    "G4_Cu",
    "G4_W",
    "G4_Pb",
    "G4_CESIUM_IODIDE",
    "G4_SODIUM_IODIDE",
    "G4_BGO",
    "G4_CONCRETE",
    "G4_Galactic",
)

_ENERGY_MEV = (0.001, 100000.0)
_THICKNESS_CM = (0.01, 500.0)
_BINS = (1, 2000)
_EVENTS = (1, 200000)
_TIMEOUT_SECONDS = (1, 1800)
_DEFAULT_TIMEOUT = 600

_SOURCE = Path(__file__).parent / "data" / "geant4" / "depth_dose.cc"
_CACHE_ENV = "TOOLUNIVERSE_GEANT4_CACHE"
_CONFIG_ENV = "GEANT4_CONFIG"

_INSTALL_HINT = (
    "Install GEANT4 and put geant4-config on PATH, or set GEANT4_CONFIG to it. "
    "A self-contained install needs no root: "
    "`micromamba create -p ~/geant4-env -c conda-forge geant4` provides both the "
    "toolkit and its physics data."
)


class _SimulationError(RuntimeError):
    """A failure the caller can act on, already worded for them."""


def _number(arguments: Dict[str, Any], key: str, default: float, bounds) -> float:
    low, high = bounds
    value = arguments.get(key, default)
    if value is None:
        value = default
    try:
        value = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a number between {low} and {high}.")
    if not low <= value <= high:
        raise ValueError(f"{key} must be between {low} and {high}, not {value:g}.")
    return value


def _whole(arguments: Dict[str, Any], key: str, default: int, bounds) -> int:
    low, high = bounds
    value = arguments.get(key, default)
    if value is None:
        value = default
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{key} must be a whole number between {low} and {high}.")
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{key} must be a whole number between {low} and {high}.")
    if number != int(number):
        raise ValueError(f"{key} must be a whole number, not {value}.")
    number = int(number)
    if not low <= number <= high:
        raise ValueError(f"{key} must be between {low} and {high}, not {number}.")
    return number


def _choice(arguments: Dict[str, Any], key: str, default: str, allowed) -> str:
    value = arguments.get(key) or default
    if value not in allowed:
        raise ValueError(f"{key} must be one of: {', '.join(allowed)}. Got {value!r}.")
    return value


def _geant4_config() -> str:
    configured = os.environ.get(_CONFIG_ENV)
    if configured:
        if not os.access(configured, os.X_OK):
            raise _SimulationError(
                f"{_CONFIG_ENV} points at {configured}, which is not executable. "
                + _INSTALL_HINT
            )
        return configured
    found = shutil.which("geant4-config")
    if not found:
        raise _SimulationError("GEANT4 was not found. " + _INSTALL_HINT)
    return found


def _ask(config: str, *flags: str) -> str:
    result = subprocess.run(
        [config, *flags], capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        raise _SimulationError(
            f"`geant4-config {' '.join(flags)}` failed: {result.stderr.strip()[:300]}"
        )
    return result.stdout.strip()


def _dataset_environment(config: str) -> Tuple[Dict[str, str], List[str]]:
    """Point GEANT4 at its physics data, repairing paths that do not exist.

    ``geant4-config --datasets`` prints the directory the toolkit was *built*
    expecting. Packaged builds do not always install it there -- conda-forge
    installs ``ENSDFSTATE3.0`` while the toolkit asks for ``G4ENSDFSTATE3.0``,
    and GEANT4 then aborts at startup with "ENSDFSTATE.dat is not found". A
    variable the operator has already exported wins; otherwise take the
    advertised path when it exists, and when it does not, look for the one
    directory beside it whose name differs only by that ``G4`` prefix.
    """
    environment: Dict[str, str] = {}
    unresolved: List[str] = []
    for line in _ask(config, "--datasets").splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        _name, variable, path = parts[0], parts[1], parts[2]
        if os.environ.get(variable):
            continue
        directory = Path(path)
        if not directory.is_dir():
            stem = directory.name
            candidates = [stem[2:]] if stem.startswith("G4") else ["G4" + stem]
            for candidate in candidates:
                sibling = directory.parent / candidate
                if sibling.is_dir():
                    directory = sibling
                    break
        if directory.is_dir():
            environment[variable] = str(directory)
        else:
            unresolved.append(f"{variable} ({path})")
    return environment, unresolved


def _compiler() -> str:
    for name in (os.environ.get("CXX"), "c++", "g++", "clang++"):
        if name and shutil.which(name):
            return shutil.which(name)
    raise _SimulationError(
        "No C++ compiler was found, and the GEANT4 application has to be "
        "compiled once. Install g++ or clang++, or set CXX."
    )


def _cache_root() -> Path:
    configured = os.environ.get(_CACHE_ENV)
    root = Path(configured) if configured else Path.home() / ".tooluniverse" / "geant4"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build(config: str) -> Tuple[Path, str]:
    """Return the cached executable, compiling it if this is the first run."""
    if not _SOURCE.is_file():
        raise _SimulationError(
            f"The simulation source is missing from the installation ({_SOURCE})."
        )
    version = _ask(config, "--version")
    source = _SOURCE.read_bytes()
    fingerprint = hashlib.sha256(source + version.encode()).hexdigest()[:16]
    executable = _cache_root() / f"depth_dose_{fingerprint}"
    if executable.is_file() and os.access(executable, os.X_OK):
        return executable, version

    flags = _ask(config, "--cflags").split() + _ask(config, "--libs").split()
    partial = executable.with_suffix(f".{os.getpid()}")
    command = [_compiler(), "-O2", str(_SOURCE), "-o", str(partial), *flags]
    result = subprocess.run(command, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        partial.unlink(missing_ok=True)
        raise _SimulationError(
            "The GEANT4 application did not compile against this installation: "
            + (result.stderr.strip()[-400:] or "no compiler output")
        )
    # Rename last, so a concurrent caller either sees no binary or a whole one.
    partial.replace(executable)
    return executable, version


def _summarise(data: Dict[str, Any]) -> Dict[str, Any]:
    """Pick out what a depth-dose curve is usually read for."""
    bins = data.get("edep_mev_per_bin") or []
    width = data.get("bin_width_cm") or 0.0
    events = data.get("events") or 0
    summary: Dict[str, Any] = {}
    if bins and width:
        peak = max(range(len(bins)), key=lambda index: bins[index])
        summary["peak_bin"] = peak
        summary["peak_depth_cm"] = round((peak + 0.5) * width, 4)
        summary["peak_edep_mev"] = bins[peak]
        # The depth beyond which nothing is deposited: the practical range.
        last = max(
            (index for index, value in enumerate(bins) if value > 0), default=None
        )
        if last is not None:
            summary["last_depth_with_dose_cm"] = round((last + 1) * width, 4)
    if events:
        summary["edep_mev_per_event"] = round(
            float(data.get("total_edep_mev", 0.0)) / events, 6
        )
    return summary


@register_tool("Geant4DepthDoseTool")
class Geant4DepthDoseTool(BaseTool):
    """Run one Monte Carlo depth-dose simulation with GEANT4."""

    def __init__(self, tool_config: Dict[str, Any], **kwargs):
        super().__init__(tool_config)

    def run(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        arguments = arguments or {}
        try:
            settings = self._validate(arguments)
        except ValueError as error:
            return {"status": "error", "error": str(error)}

        try:
            config = _geant4_config()
            executable, version = _build(config)
            data = self._simulate(config, executable, settings)
        except _SimulationError as error:
            return {"status": "error", "error": str(error)}
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": (
                    f"The simulation did not finish within "
                    f"{settings['timeout_seconds']} seconds. Ask for fewer events, "
                    "fewer bins, or a longer timeout_seconds."
                ),
            }

        data["geant4_version"] = version
        data["summary"] = _summarise(data)
        return {"status": "success", "data": data}

    @staticmethod
    def _validate(arguments: Dict[str, Any]) -> Dict[str, Any]:
        settings = {
            "particle": _choice(arguments, "particle", "proton", _PARTICLES),
            "material": _choice(arguments, "material", "G4_WATER", _MATERIALS),
            "energy_mev": _number(arguments, "energy_mev", 150.0, _ENERGY_MEV),
            "thickness_cm": _number(arguments, "thickness_cm", 20.0, _THICKNESS_CM),
            "bins": _whole(arguments, "bins", 100, _BINS),
            "events": _whole(arguments, "events", 200, _EVENTS),
            "timeout_seconds": _whole(
                arguments, "timeout_seconds", _DEFAULT_TIMEOUT, _TIMEOUT_SECONDS
            ),
        }
        return settings

    @staticmethod
    def _simulate(
        config: str, executable: Path, settings: Dict[str, Any]
    ) -> Dict[str, Any]:
        datasets, unresolved = _dataset_environment(config)
        environment = dict(os.environ)
        environment.update(datasets)
        library = str(Path(config).resolve().parent.parent / "lib")
        if Path(library).is_dir():
            existing = environment.get("LD_LIBRARY_PATH")
            environment["LD_LIBRARY_PATH"] = (
                f"{library}:{existing}" if existing else library
            )

        command = [
            str(executable),
            "--particle",
            settings["particle"],
            "--material",
            settings["material"],
            "--energy-mev",
            repr(settings["energy_mev"]),
            "--thickness-cm",
            repr(settings["thickness_cm"]),
            "--bins",
            str(settings["bins"]),
            "--events",
            str(settings["events"]),
        ]
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=settings["timeout_seconds"],
            env=environment,
        )
        parsed = _extract(result.stdout)
        if parsed is None:
            reason = _reason(result, unresolved)
            raise _SimulationError(reason)
        return parsed


def _extract(output: str) -> Optional[Dict[str, Any]]:
    match = re.search(r"RESULT_JSON_START\s*(\{.*?\})\s*RESULT_JSON_END", output, re.S)
    if not match:
        return None
    try:
        return json.loads(match.group(1))
    except json.JSONDecodeError:
        return None


def _reason(result: subprocess.CompletedProcess, unresolved: List[str]) -> str:
    """Say why the run produced no result, naming the missing data if that is it."""
    text = f"{result.stdout}\n{result.stderr}"
    if "is not found" in text or "must be set" in text:
        missing = ", ".join(unresolved) if unresolved else "its physics data"
        return (
            "GEANT4 could not read its physics data, so the simulation aborted "
            f"before scoring anything ({missing}). Install the GEANT4 data sets, "
            "or export the G4*DATA variables for this process."
        )
    if "unknown material" in text:
        return "This GEANT4 build does not know that material."
    if "unknown particle" in text:
        return "This GEANT4 build does not know that particle."
    tail = (result.stderr.strip() or result.stdout.strip())[-400:]
    return (
        f"The simulation returned no result. {tail}"
        if tail
        else ("The simulation returned no result and said nothing.")
    )
