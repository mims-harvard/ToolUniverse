import os
import pprint
import subprocess
import tempfile
import yaml
import json
import shutil
from .base_tool import BaseTool
from .tool_registry import register_tool


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
        protein_sequence = arguments.get("protein_sequence")
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
        sequences = [{"protein": {"id": "A", "sequence": protein_sequence}}]

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
        arguments = arguments or {}
        if not arguments.get("protein_sequence"):
            return {
                "status": "error",
                "error": "The 'protein_sequence' parameter is required.",
            }

        # Create a temporary directory to store input and output files
        with tempfile.TemporaryDirectory() as temp_dir:
            input_filename = "boltz_input"
            input_yaml_path = os.path.join(temp_dir, f"{input_filename}.yaml")
            output_dir = os.path.join(temp_dir, "results")
            os.makedirs(output_dir, exist_ok=True)

            # Build and write the input YAML file
            yaml_data = self._build_yaml_input(arguments)
            with open(input_yaml_path, "w") as f:
                yaml.dump(yaml_data, f, sort_keys=False)

            # Construct the command-line arguments for Boltz
            command = [
                "boltz",
                "predict",
                input_yaml_path,
                "--out_dir",
                output_dir,
                "--use_msa_server",
                "--override",  # Override existing results if any
            ]

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
            results = {}

            # 3. structure .cif
            if arguments.get("return_structure", False):
                structure_file = os.path.join(
                    prediction_folder, f"{input_filename}_model_0.cif"
                )
                if os.path.exists(structure_file):
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
                with open(affinity_file, "r", encoding="utf-8") as f:
                    results["affinity_prediction"] = json.load(f)
            else:
                results["affinity_error"] = f"Missing {os.path.basename(affinity_file)}"

            return results


if __name__ == "__main__":
    # Example usage
    tool = Boltz2DockingTool(tool_config={})
    query = {
        "protein_sequence": "ACDEFGHIKLMNPQRSTVWY",
        "ligands": [
            {"id": "LIG1", "smiles": "C1=CC=CC=C1"},
        ],
        "use_potentials": False,
        "diffusion_samples": 1,
        "return_structure": False,
    }
    result = tool.run(query)
    pprint.pprint(result)
