import os
import pprint
import subprocess
import tempfile
import yaml
import json
import shutil
import math
from .base_tool import BaseTool
from .tool_registry import register_tool


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
        if not isinstance(representation, str) or not 1 <= len(
            representation.strip()
        ) <= 4096:
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
        raise ValueError("'step_scale' must be a finite number greater than 0 and at most 10.")
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
        """
        Initializes the BoltzDockingTool.
        Checks if the 'boltz' command is available in the system's PATH.
        """
        super().__init__(tool_config)
        if not shutil.which("boltz"):
            raise EnvironmentError(
                "The 'boltz' command is not found. "
                "Please ensure the 'boltz' package is installed and accessible in the system's PATH. "
                "Installation guide: https://github.com/jwohlwend/boltz"
            )

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

            # --- Parse the output files ---
            # 1. locate the Boltz run folder under your out_dir
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
            if len(root_dirs) > 1:
                # you could pick the latest by timestamp instead of the first
                run_dir_name = sorted(root_dirs)[-1]
            else:
                run_dir_name = root_dirs[0]

            run_root = os.path.join(output_dir, run_dir_name)

            # 2. now point at predictions/<input_filename>
            prediction_folder = os.path.join(run_root, "predictions", input_filename)
            results = {
                "msa_mode": (
                    "server" if arguments["use_msa_server"] else "single_sequence"
                )
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
