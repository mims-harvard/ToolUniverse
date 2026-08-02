# Complete VSD Evaluation Branch

The `vsd-complete-evaluation-suite` branch is a reviewer-facing test assembly.
It starts from current `main`, merges the complete stacked VSD implementation
from PRs #416-#419, #421, and #423-#432, and merges the independent
administrator-only Docker implementation from #420.

The branch is not a replacement for the isolated review order. It exists so a
reviewer can install, run, and inspect every pending VSD capability in one tree.

## Five New Value Studies

`examples/vsd/growth_value_portfolio.py` adds five deterministic studies based
on research workflows documented by ToolUniverse:

1. Precision oncology molecular evidence
2. Pregnancy pharmacovigilance signal governance
3. Rare-disease natural-history cohorts
4. Infectious-disease genomic surveillance
5. Multi-omics drug repurposing

Each case audits the real ToolUniverse registry, reuses existing capabilities,
isolates one provider-specific gap, records three local demand observations,
exports one explicitly reviewed sanitized proposal, inspects an authenticated
OpenAPI contract, verifies three records, refuses publication before approval,
publishes and explicitly loads the new tool, executes across credential
rotation, resolves the original demand, detects breaking drift, suspends fresh
loading, and requires reviewed repair before reactivation.

The providers are deterministic fixtures because controlled datasets and
private credentials cannot be committed. Registry search, workflow planning,
demand storage, proposal export, contract inspection, promotion, verification,
publication, ToolUniverse loading, execution, credential lookup, lifecycle,
and audit behavior all use production code.

## Run The Portfolio

From the repository root:

```console
uv sync --group dev
PYTHONPATH=src TOOLUNIVERSE_CACHE_PERSIST=false \
  uv run python examples/vsd/growth_value_portfolio.py
```

The command writes:

- `examples/vsd/artifacts/growth_value_portfolio.md`
- `examples/vsd/artifacts/growth_value_portfolio.json`
- one Markdown report and JSON ledger for each of the five studies

Run the automated artifact, determinism, tamper, secret, and integration checks:

```console
PYTHONPATH=src TOOLUNIVERSE_CACHE_PERSIST=false \
  uv run pytest tests/unit/test_vsd_growth_value_portfolio.py -q --no-cov
```

Run every cumulative VSD test:

```console
PYTHONPATH=src TOOLUNIVERSE_CACHE_PERSIST=false \
  uv run pytest tests/unit/test_vsd*.py -q --no-cov --timeout=600
```

## Docker Boundary

The five scientific studies do not provision containers. Docker lifecycle
remains an administrator-only control plane and is tested separately:

```console
uv run pytest tests/unit/test_docker_llm_provision.py \
  tests/unit/test_docker_llm_cli.py \
  tests/unit/test_docker_llm_case_study.py -q --no-cov
```

The real-container smoke requires Linux, a running Docker daemon, and the
reviewed fixture image build described in
`docs/dev_docs/DOCKER_LLM_ADMIN_VALIDATION.md`. Its checked evidence proves
loopback-only binding, a read-only root filesystem, dropped capabilities, no
new privileges, no bind mounts, CPU/memory/PID limits, a ToolUniverse request,
and complete cleanup.

## Evidence Totals

- 5 new scientific domains
- 110 new end-to-end study assertions
- 15 representative verification executions
- 15 post-verification fresh-runtime executions
- 5 credential rotations
- 5 explicit demand closures
- 5 breaking-drift suspension and recovery cycles
- 6 formats in the existing cross-format proof
- 1 independent real-container administrator boundary

These results validate software behavior and governance. They do not validate
the scientific truth of fixture records, establish clinical or public-health
recommendations, or certify a provider merely because it appears in discovery.
