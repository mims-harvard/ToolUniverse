# RFdiffusion2 Remote Tool

## Validation and deployment status (2026-10-06)

> RFdiffusion2 (commit `d365cbf`, official `bakerlab_rf_diffusion_aa.sif` image and `RFD_173.pt` weights) ran on one NVIDIA RTX 5000 Ada (32 GB) under rootless Apptainer 1.5.4. Through a direct loopback MCP connection, ToolUniverse discovered `rfdiffusion2_design` and completed the upstream `active_site_unindexed_atomic` demo (lactate dehydrogenase 1LDM with NAD and oxamate) in 188 seconds. The returned 180-residue backbone kept both ligands and all four active-site residues, and its motif atoms superimpose on the input at 0.09 A RMSD. Reduced-step, two-design, and ligand-only runs also returned valid designs. Platform relay sharing (`tu remote share`), non-loopback binding, multi-GPU or concurrent load, and the LigandMPNN and Chai-1 pipeline stages were not tested; keep this deployment private.

- Operation: `rfdiffusion2_design`
- Start: `python -m tooluniverse.remote.rfdiffusion2.rfdiffusion2_mcp_server`
- Endpoint: `http://127.0.0.1:8033/mcp`
- Provider configuration: `RFDIFFUSION2_COMMAND`, `RFDIFFUSION2_WORKDIR`, and `RFDIFFUSION2_INPUT_ROOT` are required. Keep the container image, weights, and job scratch space outside Git. The server runs one design at a time; a call that cannot start within its own timeout gets a busy error.
- End-to-end check: `python scripts/remote_validation/rfdiffusion2_live_validation.py --out rfdiffusion2_validation --reference-pdb "$RFDIFFUSION2_WORKDIR/rf_diffusion/benchmark/input/mcsa_41/M0584_1ldm.pdb"` (the reference PDB enables the motif RMSD check)

Non-loopback binding requires `TOOLUNIVERSE_API_TOKEN`; otherwise keep the server on loopback.

This implementation is not in the `tu remote share` catalog or the shared setup-skill preflight, because neither could be exercised without a Platform service key.

See the [setup and usage guide](../../../../docs/tools/remote/rfdiffusion2.md) for installation, parameters, and output format.
