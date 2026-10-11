# RFdiffusion2

[RFdiffusion2](https://github.com/RosettaCommons/RFdiffusion2) designs protein
backbones around an atom-level description of an enzyme active site and its
small-molecule ligands. ToolUniverse reaches it as a remote tool: a provider
runs an MCP server next to the GPU, and clients call the `rfdiffusion2_design`
operation through that server.

The tool covers the backbone design stage (`rf_diffusion/run_inference.py`).
Sequence fitting with LigandMPNN and refolding with Chai-1 are separate
RFdiffusion2 pipeline stages that this tool does not run.

## Provider setup

### Requirements

- Linux with an NVIDIA GPU. A 180-residue design with two ligands used under
  5 GB of GPU memory.
- [Apptainer](https://apptainer.org) or Singularity. Without root access,
  `conda install -c conda-forge apptainer squashfuse` gives a working rootless
  install.
- About 17 GB of disk for the container image and model weights.

### 1. Install RFdiffusion2

```bash
git clone https://github.com/RosettaCommons/RFdiffusion2.git /opt/RFdiffusion2
cd /opt/RFdiffusion2
python setup.py   # downloads the container images and model weights
```

`setup.py` also downloads the LigandMPNN and Chai-1 images (about 31 GB in
total). The tool needs only `rf_diffusion/exec/bakerlab_rf_diffusion_aa.sif`
and `rf_diffusion/model_weights/RFD_173.pt`.

### 2. Install ToolUniverse

```bash
pip install tooluniverse
```

### 3. Configure and start the server

```bash
export RFDIFFUSION2_WORKDIR=/opt/RFdiffusion2
export RFDIFFUSION2_COMMAND="apptainer exec --nv $RFDIFFUSION2_WORKDIR/rf_diffusion/exec/bakerlab_rf_diffusion_aa.sif rf_diffusion/run_inference.py"
export RFDIFFUSION2_INPUT_ROOT=/srv/rfdiffusion2/inputs

python -m tooluniverse.remote.rfdiffusion2.rfdiffusion2_mcp_server
```

The server listens on `http://127.0.0.1:8033/mcp`. Set `TOOLUNIVERSE_MCP_HOST`
and `TOOLUNIVERSE_MCP_PORT` to change that. Binding to a non-loopback host
requires `TOOLUNIVERSE_API_TOKEN`; the server refuses to start without it.

| Variable | Required | Meaning |
| --- | --- | --- |
| `RFDIFFUSION2_COMMAND` | yes | Command that runs `run_inference.py`. The tool appends the Hydra overrides and runs it from `RFDIFFUSION2_WORKDIR`. |
| `RFDIFFUSION2_WORKDIR` | yes | RFdiffusion2 checkout. It is also added to `PYTHONPATH`. |
| `RFDIFFUSION2_INPUT_ROOT` | yes | Directory of input PDB files callers may name. Files outside it are rejected. |
| `RFDIFFUSION2_CHECKPOINT` | no | Model weights. Defaults to `rf_diffusion/model_weights/RFD_173.pt` in the checkout. |
| `RFDIFFUSION2_CONFIG_NAME` | no | Hydra config name. Defaults to `aa`. |
| `RFDIFFUSION2_JOB_ROOT` | no | Parent of the per-job scratch directories. Defaults to the system temporary directory (`TMPDIR`, usually `/tmp`). |

Apptainer mounts the home directory, `/tmp`, and the working directory by
default. If the checkout, the input directory, or the job root live elsewhere,
add `--bind /that/path` to `RFDIFFUSION2_COMMAND`.

The checkpoint, the input directory, and the job root are passed to
RFdiffusion2 as Hydra overrides, so their paths may contain only letters,
digits, `.`, `_`, `-`, and `/`. The server reports any other path as a
provider configuration error.

The server runs one design job at a time. A call that arrives while another
design is running waits for it, and that wait counts against the call's
`timeout_seconds`; if the call cannot start in time it returns a busy error.
Each job gets a private scratch directory that is deleted when the call
returns, and everything the command started is stopped with it.

### Input files

Callers name an input PDB by its path relative to `RFDIFFUSION2_INPUT_ROOT`,
such as `mcsa_41/M0584_1ldm.pdb`. Absolute paths and `..` segments are
rejected, and file names may contain only letters, digits, `.`, `_`, and `-`.
The file holds the motif residues and the ligands, and it must contain the ORI
`HETATM` atom that RFdiffusion2 uses to position the design; see the
RFdiffusion2 documentation on ORI tokens. RFdiffusion2's own
`rf_diffusion/benchmark/input` directory is a ready-made input root for trying
the tool.

## Client setup

```bash
export RFDIFFUSION2_MCP_SERVER_HOST=127.0.0.1
```

```python
from tooluniverse import ToolUniverse

tu = ToolUniverse()
tu.load_tools(categories=["mcp_auto_loader_rfdiffusion2"])

result = tu.run(
    {
        "name": "mcp_rfdiffusion2_design",
        "arguments": {
            "contig_map": "46,A106-106,59,A166-166,2,A169-169,23,A193-193,46",
            "input_pdb": "mcsa_41/M0584_1ldm.pdb",
            "ligand": "NAD,OXM",
            "contig_atoms": {
                "A106": "NE,CD,CZ",
                "A166": "OD1,CG",
                "A169": "NH2,CZ",
                "A193": "NE2,CD2,CE1",
            },
            "contig_as_guidepost": True,
            "seed": 43,
        },
    }
)
design = result["data"]["designs"][0]
open(f"{design['name']}.pdb", "w").write(design["pdb"])
```

The loader registers the operation as `mcp_rfdiffusion2_design`.

## Parameters

| Parameter | Type | Default | Meaning |
| --- | --- | --- | --- |
| `contig_map` | string | required | Contig string. Numbers are lengths of new backbone; chain-prefixed ranges are motif residues from `input_pdb`. |
| `input_pdb` | string | required | PDB file name relative to the provider input directory. |
| `ligand` | string | none | Comma-separated ligand residue names to design around, such as `NAD,OXM`. |
| `contig_atoms` | object | none | Motif residue to comma-separated atom names, for an atom-level motif. |
| `contig_as_guidepost` | boolean | `false` | Let RFdiffusion2 choose the sequence positions of the motif residues. |
| `num_designs` | integer | `1` | Number of backbones, 1 to 4. |
| `inference_steps` | integer | model default (100) | Flow-matching steps, 10 to 200. |
| `seed` | integer | random | Seed for a reproducible run. |
| `return_structure` | boolean | `true` | Include the PDB text of each design. |
| `timeout_seconds` | integer | `900` | Maximum time for the call, up to 900, including any wait for a running design. |
| `dry_run` | boolean | `false` | Validate the arguments, including that `input_pdb` exists, and return the Hydra overrides without running. |

Unknown parameters and out-of-range values are rejected. A call that would
exceed the 15-minute limit should ask for fewer designs or fewer steps.

## Output

```json
{
  "status": "success",
  "data": {
    "num_designs": 1,
    "runtime_seconds": 187.8,
    "designs": [
      {
        "name": "design_0-atomized-bb-False",
        "pdb_bytes": 67392,
        "num_residues": 180,
        "num_atoms": 970,
        "chains": ["A"],
        "ligands": ["NAD", "OXM"],
        "residues_with_side_chain_atoms": ["A66:ARG", "A84:ARG", "A111:ASP", "A123:HIS"],
        "pdb": "ATOM      1  N   ALA A   1 ..."
      }
    ]
  }
}
```

Newly designed residues are backbone-only and written as alanine. The residues
listed in `residues_with_side_chain_atoms` are the scaffolded motif residues.

A failed call returns `{"status": "error", "error": "..."}` with a sanitized
message. The provider checks every design before returning it: a missing,
oversized, or malformed PDB, or one with non-finite coordinates, is an error
rather than a partial success. RFdiffusion2's own log stays on the provider.

## Validating a deployment

`scripts/remote_validation/rfdiffusion2_live_validation.py` connects through
ToolUniverse, checks discovery and the input boundaries, runs the active-site
design above, and re-parses the returned PDB independently:

```bash
export RFDIFFUSION2_MCP_SERVER_HOST=127.0.0.1
python scripts/remote_validation/rfdiffusion2_live_validation.py \
    --out rfdiffusion2_validation \
    --reference-pdb /opt/RFdiffusion2/rf_diffusion/benchmark/input/mcsa_41/M0584_1ldm.pdb
```

It expects the provider input root to be RFdiffusion2's
`rf_diffusion/benchmark/input`. It exits non-zero unless every check passes,
and writes the design and a `report.json`.

## Not covered

- LigandMPNN sequence design and Chai-1 refolding.
- Protein-binder hotspots, symmetry, partial diffusion, and other RFdiffusion2
  options outside the parameters above.
- Uploading an input PDB with the call; inputs are provider-side files.
- Platform relay sharing (`tu remote share`); only a direct MCP connection has
  been validated.
