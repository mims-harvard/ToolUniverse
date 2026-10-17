import os
import pprint
import subprocess
import tempfile
import yaml
import json
import shutil
import math
from .base_tool import BaseTool
from .logging_config import get_logger
from .tool_registry import register_tool

logger = get_logger(__name__)


_ALLOWED_AMINO_ACIDS = frozenset("ACDEFGHIKLMNPQRSTVWY")
_MAX_PROTEIN_LENGTH = 4096
_MAX_LIGANDS = 8
_MAX_STRUCTURE_BYTES = 5_000_000
_MAX_AFFINITY_BYTES = 1_000_000


def _bounded_integer(arguments, name, default, minimum, maximum):
    value = arguments.get(name, default)
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"'{name}' must be an integer from {minimum} to {maximum}.")
    return value


def _validate_boltz_arguments(arguments):
    if not isinstance(arguments, dict):
        raise ValueError("Arguments must be an object.")

    normalized = dict(arguments)
    sequence = normalized.get("sequence", normalized.get("protein_sequence"))
    if not isinstance(sequence, str) or not sequence.strip():
        raise ValueError("The 'sequence' parameter is required.")
    sequence = sequence.strip().upper()
    if len(sequence) > _MAX_PROTEIN_LENGTH:
        raise ValueError(
            f"'sequence' must contain at most {_MAX_PROTEIN_LENGTH} amino acids."
        )
    if set(sequence) - _ALLOWED_AMINO_ACIDS:
        raise ValueError("'sequence' must use the 20 standard amino-acid letters.")
    normalized["sequence"] = sequence
    normalized.pop("protein_sequence", None)

    ligands = normalized.get("ligands")
    if not isinstance(ligands, list) or not 1 <= len(ligands) <= _MAX_LIGANDS:
        raise ValueError(f"'ligands' must contain 1 to {_MAX_LIGANDS} entries.")
    clean_ligands = []
    for index, ligand in enumerate(ligands):
        if not isinstance(ligand, dict):
            raise ValueError(f"Ligand at index {index} must be an object.")
        ligand_id = ligand.get("id")
        if not isinstance(ligand_id, str) or not 1 <= len(ligand_id.strip()) <= 64:
            raise ValueError(
                f"Ligand at index {index} must have a nonempty 'id' of at most 64 characters."
            )
        smiles = ligand.get("smiles")
        ccd = ligand.get("ccd")
        if (smiles is None) == (ccd is None):
            raise ValueError(
                f"Ligand at index {index} must provide exactly one of 'smiles' or 'ccd'."
            )
        representation = smiles if smiles is not None else ccd
        representation_name = "smiles" if smiles is not None else "ccd"
        if (
            not isinstance(representation, str)
            or not 1 <= len(representation.strip()) <= 4096
        ):
            raise ValueError(
                f"Ligand at index {index} has an invalid '{representation_name}'."
            )
        clean_ligands.append(
            {
                "id": ligand_id.strip(),
                representation_name: representation.strip(),
            }
        )
    normalized["ligands"] = clean_ligands

    normalized["recycling_steps"] = _bounded_integer(
        normalized, "recycling_steps", 3, 0, 20
    )
    normalized["sampling_steps"] = _bounded_integer(
        normalized, "sampling_steps", 200, 1, 2000
    )
    normalized["diffusion_samples"] = _bounded_integer(
        normalized, "diffusion_samples", 1, 1, 16
    )
    step_scale = normalized.get("step_scale", 1.638)
    if (
        isinstance(step_scale, bool)
        or not isinstance(step_scale, (int, float))
        or not math.isfinite(step_scale)
        or not 0 < step_scale <= 10
    ):
        raise ValueError(
            "'step_scale' must be a finite number greater than 0 and at most 10."
        )
    normalized["step_scale"] = float(step_scale)
    for name, default in (
        ("use_potentials", False),
        ("return_structure", False),
        ("use_msa_server", True),
    ):
        value = normalized.get(name, default)
        if type(value) is not bool:
            raise ValueError(f"'{name}' must be a boolean.")
        normalized[name] = value

    for name in ("constraints", "templates"):
        if name in normalized and (
            not isinstance(normalized[name], list) or len(normalized[name]) > 100
        ):
            raise ValueError(f"'{name}' must be an array with at most 100 entries.")

    return normalized


@register_tool("Boltz2DockingTool")
class Boltz2DockingTool(BaseTool):
    """
    Tool to perform protein-ligand docking and affinity prediction using the local Boltz-2 model.
    This tool constructs a YAML input file, runs the `boltz predict` command,
    and parses the output to return the predicted structure and affinity.
    """

    def __init__(self, tool_config: dict):
        """Initializes the BoltzDockingTool and checks that some path can run.

        Either route will do. The subprocess route needs `boltz` on this
        process's PATH; the resident route does not, and must not -- it runs the
        model in its own environment precisely because that environment's pinned
        stack (torch 2.12.0+cu130, triton 3.7.0, numpy 1.26.4) does not coexist
        with ToolUniverse's. Requiring `boltz` here would make a correctly
        separated deployment fail at construction.
        """
        super().__init__(tool_config)
        if shutil.which("boltz"):
            return
        problem = self._resident_unavailable_reason()
        if problem is None:
            return
        raise EnvironmentError(
            "Boltz-2 can be reached by neither route. "
            "The 'boltz' command is not on PATH (installation guide: "
            "https://github.com/jwohlwend/boltz), and the resident worker is "
            f"not available either: {problem}"
        )

    def _resident_unavailable_reason(self):
        """None when a resident worker could be started, else why it could not."""
        if not self._resident_enabled():
            return f"{self._RESIDENT_ENV} is set to off"
        try:
            from tooluniverse.remote_resident import backend

            worker = backend.worker_for_provider_dir(
                os.path.join(os.path.dirname(__file__), "remote", "boltz")
            )
            worker.manifest.python_executable()
        except Exception as exc:  # noqa: BLE001 - the reason is the message
            return f"{type(exc).__name__}: {exc}"
        return None

    def _build_yaml_input(self, arguments: dict) -> dict:
        """Constructs the YAML data structure for the Boltz input."""
        protein_sequence = arguments["sequence"]
        ligands = arguments.get("ligands", [])

        # The first ligand is assumed to be the binder for affinity prediction
        if not ligands:
            raise ValueError(
                "At least one ligand must be provided in the 'ligands' list."
            )

        binder_id = ligands[0].get("id")
        if not binder_id:
            raise ValueError("The first ligand in the list must have a valid 'id'.")

        # --- Sequences Section ---
        protein = {"id": "A", "sequence": protein_sequence}
        if not arguments["use_msa_server"]:
            # Boltz's documented explicit single-sequence mode. Do not silently
            # fall back when the external MSA provider is unavailable because
            # that changes the scientific execution mode.
            protein["msa"] = "empty"
        sequences = [{"protein": protein}]

        for i, ligand_data in enumerate(ligands):
            chain_id = ligand_data.get("id")
            if not chain_id:
                raise ValueError(f"Ligand at index {i} must have an 'id' key.")

            entry = {"id": chain_id}
            if "smiles" in ligand_data:
                entry["smiles"] = ligand_data["smiles"]
            elif "ccd" in ligand_data:
                entry["ccd"] = ligand_data["ccd"]
            else:
                raise ValueError(
                    f"Ligand at index {i} must have a 'smiles' or 'ccd' key."
                )
            sequences.append({"ligand": entry})

        # --- Properties Section (for Affinity) ---
        properties = [{"affinity": {"binder": binder_id}}]

        # --- Final YAML Structure ---
        yaml_input = {"version": 1, "sequences": sequences, "properties": properties}

        # Add optional fields
        if "constraints" in arguments:
            yaml_input["constraints"] = arguments["constraints"]
        if "templates" in arguments:
            yaml_input["templates"] = arguments["templates"]

        return yaml_input

    def run(self, arguments: dict | None = None, timeout: int = 1200) -> dict:
        """
        Executes the Boltz prediction.

        Args:
            arguments (dict): A dictionary containing the necessary inputs.
                - protein_sequence (str): The amino acid sequence of the protein.
                - ligands (list[dict]): A list of ligands, each with a 'smiles' or 'ccd' key.
                - constraints (list[dict], optional): Covalent bonds or other constraints.
                - templates (list[dict], optional): Structural templates.
                - other optional boltz CLI flags (e.g., 'recycling_steps').
            timeout (int): The maximum time in seconds to wait for the Boltz command to complete.

        Returns
            dict: A dictionary containing the path to the predicted structure and affinity data, or an error.
        """
        try:
            arguments = _validate_boltz_arguments(arguments or {})
        except ValueError as exc:
            return {"status": "error", "error": str(exc)}
        if type(timeout) is not int or not 1 <= timeout <= 7200:
            return {
                "status": "error",
                "error": "'timeout' must be an integer from 1 to 7200 seconds.",
            }
        try:
            return self._run_provider(arguments, timeout)
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "error": "Boltz prediction timed out on the provider.",
            }
        except subprocess.CalledProcessError:
            return {
                "status": "error",
                "error": "Boltz prediction failed on the provider.",
            }
        except Exception:
            return {
                "status": "error",
                "error": "Boltz prediction failed due to an internal provider error.",
            }

    def _collect_results(
        self, prediction_folder: str, input_filename: str, arguments: dict
    ) -> dict:
        """The tool's answer, read off the files a prediction wrote.

        Shared by both execution paths so that a held worker and a subprocess
        are indistinguishable to a caller: same keys, same size limits, same
        fail-closed rule when the affinity artifact is missing.
        """
        results = {
            "msa_mode": ("server" if arguments["use_msa_server"] else "single_sequence")
        }

        # 3. structure .cif
        if arguments.get("return_structure", False):
            structure_file = os.path.join(
                prediction_folder, f"{input_filename}_model_0.cif"
            )
            if os.path.exists(structure_file):
                if os.path.getsize(structure_file) > _MAX_STRUCTURE_BYTES:
                    results["structure_error"] = (
                        "Predicted structure exceeds the public output limit"
                    )
                else:
                    with open(structure_file, "r", encoding="utf-8") as f:
                        results["predicted_structure"] = f.read()
                    results["structure_format"] = "cif"
            else:
                results["structure_error"] = (
                    f"Missing {os.path.basename(structure_file)}"
                )

        # 4. affinity .json
        affinity_file = os.path.join(
            prediction_folder, f"affinity_{input_filename}.json"
        )
        if os.path.exists(affinity_file):
            if os.path.getsize(affinity_file) > _MAX_AFFINITY_BYTES:
                return {
                    "status": "error",
                    "error": "Boltz produced an invalid affinity prediction.",
                    "msa_mode": results["msa_mode"],
                }
            else:
                try:
                    with open(affinity_file, "r", encoding="utf-8") as f:
                        affinity = json.load(f)
                    json.dumps(affinity, allow_nan=False)
                    results["affinity_prediction"] = affinity
                except (OSError, UnicodeError, ValueError, json.JSONDecodeError):
                    return {
                        "status": "error",
                        "error": "Boltz produced an invalid affinity prediction.",
                        "msa_mode": results["msa_mode"],
                    }
        else:
            # Boltz 2.2.1 may exit zero after skipping an input whose MSA
            # request failed. Missing the required affinity artifact must
            # therefore fail closed instead of looking like a successful
            # docking result to MCP and Platform callers.
            return {
                "status": "error",
                "error": "Boltz did not produce an affinity prediction.",
                "msa_mode": results["msa_mode"],
            }

        return results

    def _predict_subprocess(
        self,
        input_yaml_path: str,
        output_dir: str,
        input_filename: str,
        arguments: dict,
        timeout: int,
    ):
        """One `boltz predict` process, as this tool has always run it.

        Pays weight load, CUDA context and kernel compilation on every request
        -- ~110 s for a 330-residue protein with a ligand on this project's GB10
        box. It stays as the path taken when no resident worker is configured or
        the resident one cannot start, so a deployment without the model
        environment keeps working exactly as before.
        """
        # Construct the command-line arguments for Boltz
        command = [
            "boltz",
            "predict",
            input_yaml_path,
            "--out_dir",
            output_dir,
            "--override",  # Override existing results if any
            # Multiprocessing data-loader workers can deadlock when Boltz is
            # launched from a long-lived MCP worker process.  A single
            # in-process loader is slower at high throughput but reliable
            # for this one-request-at-a-time provider wrapper.
            "--num_workers",
            "0",
        ]

        if arguments["use_msa_server"]:
            command.append("--use_msa_server")

        # Add optional command-line flags from arguments
        for key in [
            "recycling_steps",
            "diffusion_samples",
            "sampling_steps",
            "step_scale",
        ]:
            if key in arguments:
                command.extend([f"--{key}", str(arguments[key])])

        if arguments.get("use_potentials", False):
            command.append("--use_potentials")

        # Execute the Boltz command
        subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=True,  # Will raise CalledProcessError on non-zero exit codes
        )

        # locate the Boltz run folder under out_dir
        root_dirs = [
            d
            for d in os.listdir(output_dir)
            if os.path.isdir(os.path.join(output_dir, d))
        ]
        if not root_dirs:
            return {
                "status": "error",
                "error": "No Boltz run folder found under out_dir",
            }
        run_dir_name = sorted(root_dirs)[-1]
        return os.path.join(output_dir, run_dir_name, "predictions", input_filename)

    # A deployment turns the held worker off with TOOLUNIVERSE_BOLTZ_RESIDENT=0.
    # Anything else, including unset, tries it and falls back.
    _RESIDENT_ENV = "TOOLUNIVERSE_BOLTZ_RESIDENT"

    def _resident_enabled(self) -> bool:
        return os.environ.get(self._RESIDENT_ENV, "1").strip().lower() not in (
            "0",
            "false",
            "no",
            "off",
        )

    def _predict(
        self,
        yaml_data: dict,
        input_yaml_path: str,
        output_dir: str,
        input_filename: str,
        arguments: dict,
        timeout: int,
    ):
        """Run one prediction; return its predictions/ directory, or an error dict.

        The held worker first, the subprocess if it is not available. Falling
        back is not a silent downgrade of correctness -- the two paths were
        verified to agree bit for bit on this project's box, structure
        (mean |dCA| 0.000 A) and affinity (identical to 16 significant figures)
        -- it is a downgrade of speed only, from ~47 s to ~110 s per request,
        and the reason is logged.
        """
        if self._resident_enabled():
            try:
                return self._predict_resident(
                    yaml_data, output_dir, input_filename, arguments
                )
            except Exception as exc:  # noqa: BLE001 - any reason falls back
                logger.info(
                    "Boltz resident worker unavailable (%s: %s); using a "
                    "subprocess for this request",
                    type(exc).__name__,
                    exc,
                )
        return self._predict_subprocess(
            input_yaml_path, output_dir, input_filename, arguments, timeout
        )

    def _predict_resident(
        self,
        yaml_data: dict,
        output_dir: str,
        input_filename: str,
        arguments: dict,
    ) -> str:
        """One prediction on the worker that holds the model between requests."""
        from tooluniverse.remote_resident import backend

        worker = backend.worker_for_provider_dir(
            os.path.join(os.path.dirname(__file__), "remote", "boltz")
        )
        options = {
            k: arguments[k]
            for k in (
                "recycling_steps",
                "sampling_steps",
                "diffusion_samples",
                "step_scale",
                "use_potentials",
                "use_msa_server",
            )
            if k in arguments
        }
        reply = worker.request(
            {
                "op": "predict",
                "yaml": yaml.safe_dump(yaml_data, sort_keys=False),
                "out_dir": output_dir,
                "name": input_filename,
                "seed": int(arguments.get("seed", 0)),
                "options": options,
            }
        )
        result = reply["result"]
        logger.info(
            "Boltz resident prediction: %s (peak reserved %.2f GiB)",
            result.get("timing"),
            result.get("peak_reserved_gib", float("nan")),
        )
        return os.path.join(result["out_dir"], "predictions", input_filename)

    def _run_provider(self, arguments: dict, timeout: int) -> dict:
        # Create a temporary directory to store input and output files
        with tempfile.TemporaryDirectory() as temp_dir:
            input_filename = "boltz_input"
            input_yaml_path = os.path.join(temp_dir, f"{input_filename}.yaml")
            output_dir = os.path.join(temp_dir, "results")
            os.makedirs(output_dir, exist_ok=True)

            # Build and write the input YAML file
            yaml_data = self._build_yaml_input(arguments)
            with open(input_yaml_path, "w") as f:
                yaml.safe_dump(yaml_data, f, sort_keys=False)

            prediction_folder = self._predict(
                yaml_data,
                input_yaml_path,
                output_dir,
                input_filename,
                arguments,
                timeout,
            )
            if isinstance(prediction_folder, dict):
                return prediction_folder  # a named failure from the chosen path
            return self._collect_results(prediction_folder, input_filename, arguments)


if __name__ == "__main__":
    # Example usage
    tool = Boltz2DockingTool(tool_config={})
    query = {
        "sequence": "ACDEFGHIKLMNPQRSTVWY",
        "ligands": [
            {"id": "LIG1", "smiles": "C1=CC=CC=C1"},
        ],
        "use_potentials": False,
        "diffusion_samples": 1,
        "return_structure": False,
    }
    result = tool.run(query)
    pprint.pprint(result)
