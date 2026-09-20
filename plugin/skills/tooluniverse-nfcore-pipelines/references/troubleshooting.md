# Troubleshooting nf-core / Nextflow Runs

## Docker permission denied

```
permission denied while trying to connect to the Docker daemon socket
```

Fix: `sudo usermod -aG docker $USER`, then fully log out and back in (a new
shell alone is not enough — group membership is re-read at login). Verify
with `docker info` before retrying the pipeline.

## Docker daemon not running

```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

Fix: `sudo systemctl start docker`. On some minimal/container hosts, Docker
cannot run at all (no privileged access) — in that case use `-profile
singularity` if Singularity/Apptainer is available, or report to the user
that neither container runtime works in this environment and a real
pipeline run is not possible here.

## Out of memory / process killed

Nextflow reports a process failed with exit code 137 (OOM-killed). Either:
- Reduce resource requests: add `--max_memory '16.GB' --max_cpus 4` etc. to
  the run command, or
- Run on a host with more RAM — some steps (STAR genome indexing/alignment,
  GATK) need tens of GB for a human genome.

## HPC / Singularity

Replace `-profile docker` with `-profile singularity` (or a site-specific
config if the institution provides one, e.g. `-profile singularity,slurm`).
Nextflow can submit to SLURM/PBS/LSF via `-profile` + `process.executor` —
this generally needs a site-specific config file; do not assume a generic
profile works without checking the institution's documentation or existing
Nextflow config.

## Resuming a failed/interrupted run

```bash
nextflow run nf-core/<pipeline> -resume
```

`-resume` reuses cached results from completed processes (matched by their
input hash) and only re-runs what failed or changed. Always include
`-resume` even on what you believe is a fresh run — it costs nothing if
there is no prior cache, and saves hours if there is.

## Test profile fails

If `-profile test,docker` fails, the problem is environmental (network
egress to pull containers/reference data, resource limits, or a broken
Docker/Nextflow install) — it is not a data problem, since the test profile
uses pipeline-bundled toy data. Fix the environment (see Docker checks
above) before troubleshooting anything about the user's real samples.

## Checking a run actually completed successfully

Never report success from Nextflow's live progress output alone — that only
shows step-by-step progress, not the pipeline's final verdict, and process
retries can look alarming while ultimately succeeding.

```bash
grep "Pipeline completed successfully" .nextflow.log
ls results/multiqc/multiqc_report.html   # or test_output/ for the test profile
```

Both must be true before reporting outputs to the user.
