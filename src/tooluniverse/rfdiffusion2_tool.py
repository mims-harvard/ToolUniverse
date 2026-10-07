"""Provider-side RFdiffusion2 wrapper for the ToolUniverse remote tool.

RFdiffusion2 (https://github.com/RosettaCommons/RFdiffusion2) ships as an
Apptainer image plus a source checkout, so this module never imports it. It
turns a bounded set of caller arguments into Hydra overrides, runs the
provider's configured ``run_inference.py`` command in a private job directory,
and returns the designed backbones only after every PDB has been parsed and
checked. Raw process output never reaches the caller.
"""

from __future__ import annotations

import logging
import math
import os
import re
import shlex
import signal
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_tool import BaseTool
from .remote_data_path import resolve_remote_data_path
from .tool_registry import register_tool

logger = logging.getLogger(__name__)

COMMAND_ENV = "RFDIFFUSION2_COMMAND"
WORKDIR_ENV = "RFDIFFUSION2_WORKDIR"
CHECKPOINT_ENV = "RFDIFFUSION2_CHECKPOINT"
CONFIG_NAME_ENV = "RFDIFFUSION2_CONFIG_NAME"
INPUT_ROOT_ENV = "RFDIFFUSION2_INPUT_ROOT"
JOB_ROOT_ENV = "RFDIFFUSION2_JOB_ROOT"

# ToolUniverse credentials the inference process has no use for.
_WITHHELD_ENV = ("TOOLUNIVERSE_API_TOKEN", "TOOLUNIVERSE_SERVICE_KEY")

_DEFAULT_CONFIG_NAME = "aa"
_DEFAULT_CHECKPOINT = ("rf_diffusion", "model_weights", "RFD_173.pt")
_OUTPUT_STEM = "design"

_MAX_CONTIG_CHARS = 512
_MAX_INPUT_PDB_CHARS = 512
_MAX_CONTIG_ATOM_RESIDUES = 32
_MAX_DESIGNS = 4
_MIN_STEPS, _MAX_STEPS = 10, 200
_MAX_SEED = 2**31 - 1
_DEFAULT_TIMEOUT, _MAX_TIMEOUT = 900, 900
_MAX_PDB_BYTES = 5_000_000
_MAX_PDB_ATOMS = 200_000
_LOG_TAIL_BYTES = 4000
_TERMINATE_GRACE_SECONDS = 15
# RFdiffusion2 refuses an input structure without its ORI positioning atom.
_MISSING_ORI_MARKER = "ORI HETATM token is required"

# Every pattern is applied with fullmatch: ``$`` would also accept a trailing
# newline, and these allowlists are all that keeps caller text inside the
# quoting of a Hydra override.
_CONTIG_PATTERN = re.compile(r"[A-Za-z0-9,/ \-]+")
_LIGAND_PATTERN = re.compile(r"[A-Za-z0-9]{1,5}(,[A-Za-z0-9]{1,5})*")
_RESIDUE_PATTERN = re.compile(r"[A-Za-z][0-9]{1,4}")
_ATOMS_PATTERN = re.compile(r"[A-Z0-9]{1,4}(,[A-Z0-9]{1,4})*")
# A relative file name in which no segment is "." or "..".
_INPUT_PDB_SEGMENT = r"\.*[A-Za-z0-9_\-][A-Za-z0-9._\-]*"
_INPUT_PDB_PATTERN = re.compile(rf"{_INPUT_PDB_SEGMENT}(/{_INPUT_PDB_SEGMENT})*")
_HYDRA_PATH_PATTERN = re.compile(r"[A-Za-z0-9._/\-]+")
_CONFIG_NAME_PATTERN = re.compile(r"[A-Za-z0-9_]+")
_DESIGN_FILE_PATTERN = re.compile(rf"{_OUTPUT_STEM}_([0-9]+)(-[A-Za-z0-9_\-]+)?\.pdb")
_REQUIRED_BACKBONE_ATOMS = frozenset({"N", "CA", "C"})
_BACKBONE_ATOMS = frozenset({"N", "CA", "C", "O", "CB", "OXT"})

_ALLOWED_ARGUMENTS = frozenset(
    {
        "contig_map",
        "input_pdb",
        "ligand",
        "contig_atoms",
        "contig_as_guidepost",
        "num_designs",
        "inference_steps",
        "seed",
        "return_structure",
        "timeout_seconds",
        "dry_run",
    }
)


class _ProviderFailure(Exception):
    """A failure whose message is safe to show to a remote caller."""


def _bounded_integer(arguments, name, default, minimum, maximum):
    value = arguments.get(name)
    if value is None:
        return default
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"'{name}' must be an integer from {minimum} to {maximum}.")
    return value


def _boolean(arguments, name, default):
    value = arguments.get(name)
    if value is None:
        return default
    if type(value) is not bool:
        raise ValueError(f"'{name}' must be a boolean.")
    return value


def _validate_arguments(arguments: Any) -> Dict[str, Any]:
    if not isinstance(arguments, dict):
        raise ValueError("Arguments must be an object.")
    unknown = sorted(set(arguments) - _ALLOWED_ARGUMENTS)
    if unknown:
        raise ValueError(f"Unknown arguments: {', '.join(unknown)}.")

    contig_map = arguments.get("contig_map")
    if (
        not isinstance(contig_map, str)
        or len(contig_map) > _MAX_CONTIG_CHARS
        or not _CONTIG_PATTERN.fullmatch(contig_map)
        or not contig_map.strip()
    ):
        raise ValueError(
            "'contig_map' is required and may contain only letters, digits, "
            "commas, slashes, hyphens, and spaces."
        )

    input_pdb = arguments.get("input_pdb")
    if (
        not isinstance(input_pdb, str)
        or len(input_pdb) > _MAX_INPUT_PDB_CHARS
        or not _INPUT_PDB_PATTERN.fullmatch(input_pdb)
    ):
        raise ValueError(
            "'input_pdb' is required: the name of a PDB file relative to the "
            "provider input directory, using letters, digits, '.', '_', '-', "
            "and '/'."
        )

    ligand = arguments.get("ligand")
    if ligand is not None and (
        not isinstance(ligand, str) or not _LIGAND_PATTERN.fullmatch(ligand)
    ):
        raise ValueError(
            "'ligand' must be comma-separated residue names such as 'NAD,OXM'."
        )

    contig_atoms = arguments.get("contig_atoms")
    if contig_atoms is not None:
        if (
            not isinstance(contig_atoms, dict)
            or not 1 <= len(contig_atoms) <= _MAX_CONTIG_ATOM_RESIDUES
        ):
            raise ValueError(
                "'contig_atoms' must map 1 to "
                f"{_MAX_CONTIG_ATOM_RESIDUES} motif residues to atom names."
            )
        for residue, atoms in contig_atoms.items():
            if not isinstance(residue, str) or not _RESIDUE_PATTERN.fullmatch(residue):
                raise ValueError("'contig_atoms' keys must be residues such as 'A106'.")
            if not isinstance(atoms, str) or not _ATOMS_PATTERN.fullmatch(atoms):
                raise ValueError(
                    "'contig_atoms' values must be comma-separated atom names "
                    "such as 'NE,CD,CZ'."
                )

    return {
        "contig_map": contig_map,
        "input_pdb": input_pdb,
        "ligand": ligand,
        "contig_atoms": contig_atoms,
        "contig_as_guidepost": _boolean(arguments, "contig_as_guidepost", False),
        "num_designs": _bounded_integer(arguments, "num_designs", 1, 1, _MAX_DESIGNS),
        "inference_steps": _bounded_integer(
            arguments, "inference_steps", None, _MIN_STEPS, _MAX_STEPS
        ),
        "seed": _bounded_integer(arguments, "seed", None, 0, _MAX_SEED),
        "return_structure": _boolean(arguments, "return_structure", True),
        "timeout_seconds": _bounded_integer(
            arguments, "timeout_seconds", _DEFAULT_TIMEOUT, 1, _MAX_TIMEOUT
        ),
        "dry_run": _boolean(arguments, "dry_run", False),
    }


def _hydra_path(path: Path, setting: str) -> str:
    """Return a path that is safe as an unquoted Hydra override value.

    Hydra would read a comma as a sweep, ``${...}`` as an interpolation, and
    reject brackets and quotes, so such a path is refused rather than passed.
    """
    text = str(path)
    if not _HYDRA_PATH_PATTERN.fullmatch(text):
        raise _ProviderFailure(
            f"The provider must use a plain path, without spaces or "
            f"punctuation, for {setting}."
        )
    return text


def _design_overrides(arguments: Dict[str, Any], input_pdb: str) -> List[str]:
    """Hydra overrides derived from caller input.

    Every caller value was validated against a character allowlist that has no
    quote, bracket, backslash, or ``$``, so the quoting below cannot be
    escaped. ``input_pdb`` is unquoted and must already be Hydra-safe.
    """
    overrides = [
        f"contigmap.contigs=['{arguments['contig_map']}']",
        f"inference.num_designs={arguments['num_designs']}",
        f"inference.contig_as_guidepost={arguments['contig_as_guidepost']}",
        f"inference.input_pdb={input_pdb}",
    ]
    if arguments["ligand"] is not None:
        overrides.append(f"inference.ligand='{arguments['ligand']}'")
    if arguments["contig_atoms"] is not None:
        atoms = ",".join(
            f"'{residue}':'{names}'"
            for residue, names in arguments["contig_atoms"].items()
        )
        overrides.append(f'contigmap.contig_atoms="{{{atoms}}}"')
    if arguments["inference_steps"] is not None:
        overrides.append(f"diffuser.T={arguments['inference_steps']}")
    if arguments["seed"] is not None:
        overrides.append("inference.deterministic=True")
        overrides.append(f"inference.seed_offset={arguments['seed']}")
    return overrides


def _resolve_input_pdb(name: str) -> str:
    try:
        resolved = resolve_remote_data_path(
            name, allowed_suffixes={".pdb"}, root_env=INPUT_ROOT_ENV
        )
    except ValueError as exc:
        # The resolver's messages never contain provider paths.
        raise _ProviderFailure(f"'input_pdb': {exc}.") from None
    return _hydra_path(resolved, INPUT_ROOT_ENV)


def _provider_configuration() -> Dict[str, Any]:
    try:
        command = shlex.split(os.getenv(COMMAND_ENV, ""))
    except ValueError:
        command = []
    workdir_value = os.getenv(WORKDIR_ENV, "").strip()
    if not command or not workdir_value or not Path(workdir_value).is_dir():
        raise _ProviderFailure(
            f"The provider must configure {COMMAND_ENV} and {WORKDIR_ENV}."
        )
    # The command runs from the checkout, so a path relative to the server's
    # own directory would point somewhere else there.
    workdir = Path(workdir_value).resolve()

    checkpoint_value = os.getenv(CHECKPOINT_ENV, "").strip()
    checkpoint = (
        Path(checkpoint_value).resolve()
        if checkpoint_value
        else workdir.joinpath(*_DEFAULT_CHECKPOINT)
    )
    if not checkpoint.is_file():
        raise _ProviderFailure(
            f"The provider must configure {CHECKPOINT_ENV} with model weights."
        )

    config_name = os.getenv(CONFIG_NAME_ENV, "").strip() or _DEFAULT_CONFIG_NAME
    if not _CONFIG_NAME_PATTERN.fullmatch(config_name):
        raise _ProviderFailure(f"The provider must fix {CONFIG_NAME_ENV}.")

    job_root = None
    job_root_value = os.getenv(JOB_ROOT_ENV, "").strip()
    if job_root_value:
        if not Path(job_root_value).is_dir():
            raise _ProviderFailure(f"The provider must fix {JOB_ROOT_ENV}.")
        job_root = Path(job_root_value).resolve()

    return {
        "command": command,
        "workdir": workdir,
        "checkpoint": _hydra_path(checkpoint, CHECKPOINT_ENV),
        "config_name": config_name,
        "job_root": job_root,
    }


def _signal_process_group(process: subprocess.Popen, signum: int) -> None:
    try:
        if hasattr(os, "killpg"):
            os.killpg(process.pid, signum)
        else:
            process.send_signal(signum)
    except OSError:
        pass


def _stop_process_group(process: subprocess.Popen) -> None:
    # The container runtime forks the real inference process, so the whole
    # group is signalled. SIGTERM comes first because a bare SIGKILL stops the
    # runtime from unmounting its image and leaves its FUSE helper running.
    if process.poll() is None:
        _signal_process_group(process, signal.SIGTERM)
        try:
            process.wait(timeout=_TERMINATE_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            pass
    _signal_process_group(process, getattr(signal, "SIGKILL", signal.SIGTERM))
    try:
        process.wait(timeout=_TERMINATE_GRACE_SECONDS)
    except subprocess.TimeoutExpired:
        logger.error("RFdiffusion2 process %s did not exit when killed", process.pid)


def _run_provider_command(
    command: List[str], cwd: str, env: Dict[str, str], log_path: Path, timeout: int
) -> int:
    with open(log_path, "wb") as log_file:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            return process.wait(timeout=timeout)
        finally:
            # Also on a normal exit: nothing the command started may outlive
            # the call and keep holding the GPU.
            _stop_process_group(process)


def _log_tail(log_path: Path) -> str:
    try:
        with open(log_path, "rb") as log_file:
            log_file.seek(0, os.SEEK_END)
            log_file.seek(max(0, log_file.tell() - _LOG_TAIL_BYTES))
            return log_file.read().decode("utf-8", errors="replace")
    except OSError:
        return ""


def _summarize_pdb(text: str) -> Dict[str, Any]:
    """Parse a designed PDB, failing closed unless every protein residue has a
    complete, unambiguous backbone with finite coordinates."""
    invalid = _ProviderFailure("RFdiffusion2 produced an invalid design.")
    residue_names: Dict[tuple, str] = {}
    residue_atoms: Dict[tuple, set] = {}
    ligands = set()
    atom_count = 0
    for line in text.splitlines():
        record = line[:6].strip()
        if record not in ("ATOM", "HETATM"):
            continue
        atom_count += 1
        if atom_count > _MAX_PDB_ATOMS:
            raise invalid
        try:
            coordinates = (float(line[30:38]), float(line[38:46]), float(line[46:54]))
        except ValueError:
            raise invalid from None
        if not all(math.isfinite(value) for value in coordinates):
            raise invalid
        residue_name = line[17:20].strip()
        if record == "HETATM":
            ligands.add(residue_name)
            continue
        key = (line[21].strip(), line[22:27].strip())
        atom_name = line[12:16].strip()
        atoms = residue_atoms.setdefault(key, set())
        if atom_name in atoms:
            raise invalid
        atoms.add(atom_name)
        residue_names[key] = residue_name
    if not residue_atoms or any(
        not _REQUIRED_BACKBONE_ATOMS <= atoms for atoms in residue_atoms.values()
    ):
        raise invalid
    return {
        "num_residues": len(residue_atoms),
        "num_atoms": atom_count,
        "chains": sorted({chain for chain, _ in residue_atoms}),
        "ligands": sorted(ligands),
        "residues_with_side_chain_atoms": [
            f"{chain}{number}:{residue_names[(chain, number)]}"
            for (chain, number), atoms in residue_atoms.items()
            if atoms - _BACKBONE_ATOMS
        ],
    }


def _collect_designs(
    job_dir: Path, num_designs: int, return_structure: bool
) -> List[Dict[str, Any]]:
    found: Dict[int, Path] = {}
    for path in sorted(job_dir.iterdir()):
        match = _DESIGN_FILE_PATTERN.fullmatch(path.name)
        if not match or not path.is_file():
            continue
        index = int(match.group(1))
        if index in found:
            # A configuration that writes several variants of one design is
            # not supported; returning one of them would misreport the job.
            raise _ProviderFailure(
                "RFdiffusion2 produced an unexpected set of designs."
            )
        found[index] = path
    if sorted(found) != list(range(num_designs)):
        # A zero exit code does not prove a design was written, so a missing
        # artifact must not look like a successful job.
        raise _ProviderFailure(
            "RFdiffusion2 did not produce the requested number of designs."
        )
    designs = []
    for index in range(num_designs):
        path = found[index]
        invalid = _ProviderFailure("RFdiffusion2 produced an invalid design.")
        if path.stat().st_size > _MAX_PDB_BYTES:
            raise invalid
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeError):
            raise invalid from None
        design = {"name": path.stem, "pdb_bytes": len(raw)}
        design.update(_summarize_pdb(text))
        if return_structure:
            design["pdb"] = text
        designs.append(design)
    return designs


@register_tool("RFDiffusion2Tool")
class RFDiffusion2Tool(BaseTool):
    """Run RFdiffusion2 backbone design through a provider-configured command."""

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            validated = _validate_arguments(arguments or {})
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}

        try:
            input_pdb = _resolve_input_pdb(validated["input_pdb"])
            if validated["dry_run"]:
                # The caller's own file name is echoed: the resolved path
                # would disclose the provider's filesystem layout.
                data = {
                    "dry_run": True,
                    "overrides": _design_overrides(validated, validated["input_pdb"]),
                }
            else:
                data = self._run_provider(validated, input_pdb)
            return {"status": "success", "data": data}
        except _ProviderFailure as exc:
            return {"status": "error", "error": str(exc)}
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "RFdiffusion2 timed out on the provider.",
            }
        except Exception:
            logger.exception("RFdiffusion2 provider error")
            return {
                "status": "error",
                "error": "RFdiffusion2 failed due to an internal provider error.",
            }

    def _run_provider(
        self, arguments: Dict[str, Any], input_pdb: str
    ) -> Dict[str, Any]:
        provider = _provider_configuration()
        workdir = str(provider["workdir"])

        env = {
            name: value
            for name, value in os.environ.items()
            if name not in _WITHHELD_ENV
        }
        env["PYTHONPATH"] = os.pathsep.join(
            part for part in (workdir, env.get("PYTHONPATH", "")) if part
        )

        # A cleanup failure must not replace the result of a finished job.
        with tempfile.TemporaryDirectory(
            prefix="rfdiffusion2_", dir=provider["job_root"], ignore_cleanup_errors=True
        ) as tmp:
            job_dir = Path(tmp).resolve()
            full_command = [
                *provider["command"],
                f"--config-name={provider['config_name']}",
                f"inference.ckpt_path={provider['checkpoint']}",
                "inference.output_prefix="
                + _hydra_path(job_dir / _OUTPUT_STEM, JOB_ROOT_ENV),
                f"hydra.run.dir={job_dir / 'hydra'}",
                *_design_overrides(arguments, input_pdb),
            ]
            log_path = job_dir / "provider.log"
            started = time.monotonic()
            try:
                returncode = _run_provider_command(
                    full_command, workdir, env, log_path, arguments["timeout_seconds"]
                )
            except OSError:
                logger.exception("RFdiffusion2 command could not be started")
                raise _ProviderFailure(
                    f"The provider must fix {COMMAND_ENV}."
                ) from None
            if returncode != 0:
                log_tail = _log_tail(log_path)
                logger.error(
                    "RFdiffusion2 exited with code %s; log tail:\n%s",
                    returncode,
                    log_tail,
                )
                if _MISSING_ORI_MARKER in log_tail:
                    raise _ProviderFailure(
                        "RFdiffusion2 needs an ORI HETATM atom in 'input_pdb' to "
                        "position the design."
                    )
                raise _ProviderFailure("RFdiffusion2 failed on the provider.")
            designs = _collect_designs(
                job_dir, arguments["num_designs"], arguments["return_structure"]
            )
            return {
                "num_designs": len(designs),
                "runtime_seconds": round(time.monotonic() - started, 1),
                "designs": designs,
            }
