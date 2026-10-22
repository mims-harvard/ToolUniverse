"""User-facing tools for the unified ML-model interface.

Two tool classes, and the asymmetry between them is deliberate:

``UnifiedModelPredictTool``
    The agent-facing one, registered once per task so that a catalogue shows
    ``predict_variant_effect`` with a concrete schema rather than one generic
    endpoint behind a ``task`` string. It takes one backend id, a list, or
    ``"all"``, plus a ``list_models`` flag -- the three tools this replaced
    (``predict``, ``compare``, ``list``) shared 13 of their 18 parameters and
    ran the same resolver, so they are one tool with a wider ``models``
    argument. ``data/unified_model_tools.json`` declares the four instances.
``UnifiedModelBenchmarkTool``
    Maintainer-facing, and deliberately NOT in the catalogue: a benchmark run
    costs hundreds of backend calls against a public dataset, which is a thing
    a maintainer decides to spend rather than a thing an agent reaches for
    mid-task. No JSON declares it; ``scripts/run_model_benchmark.py``
    constructs it directly.

The design rule running through both: **a backend that could not answer is
reported, never dropped.** Silently omitting failures is what turns a
comparison into a misleading one -- four models agreeing looks conclusive until
you learn the other six were skipped because the input never resolved.
"""

from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional, Tuple

from .base_tool import BaseTool
from .tool_registry import register_tool
from .unified_model_resolvers import ResolutionError, ensure_context, get_resolver
from .unified_model_spec import BackendSpec, TaskSpec, load_registry

_DEFAULT_WORKERS = 6

# One lock per backend id, for backends that cannot be called concurrently.
# Keyed by id rather than per-engine so that the guarantee holds even when
# several tools share the process.
_backend_locks: Dict[str, threading.Lock] = {}
_backend_locks_guard = threading.Lock()


def _lock_for(backend_id: str) -> threading.Lock:
    with _backend_locks_guard:
        lock = _backend_locks.get(backend_id)
        if lock is None:
            lock = threading.Lock()
            _backend_locks[backend_id] = lock
        return lock


_shared_tu = None
_shared_tu_lock = threading.Lock()


def _get_tooluniverse(injected=None):
    """Reuse one ToolUniverse rather than building one per call.

    ``load_tools()`` parses every config in the package; doing that inside each
    ``run()`` would dominate the cost of a comparison and make a benchmark over
    a few hundred variants unusable.
    """
    global _shared_tu
    if injected is not None:
        return injected
    with _shared_tu_lock:
        if _shared_tu is None:
            from .execute_function import ToolUniverse

            instance = ToolUniverse()
            instance.load_tools()
            _shared_tu = instance
        return _shared_tu


class _Caller:
    """Calls ToolUniverse tools, memoizing identical calls within one run.

    A comparison fans out to backends that legitimately share an underlying
    tool -- REVEL, VEST4 and MetaRNN all read one MyVariant reply -- and a
    benchmark repeats inputs across backends. Deduplicating here means the
    registry can stay naive about it.
    """

    def __init__(self, tooluniverse):
        self._tu = tooluniverse
        self._cache: Dict[str, Any] = {}
        self._lock = threading.Lock()
        self.calls_made = 0
        self.calls_saved = 0

    def __call__(
        self, tool_name: str, arguments: Dict[str, Any], bypass_cache: bool = False
    ) -> Any:
        key = f"{tool_name}:{json.dumps(arguments, sort_keys=True, default=str)}"
        if not bypass_cache:
            with self._lock:
                if key in self._cache:
                    self.calls_saved += 1
                    return self._cache[key]
        try:
            result = self._tu.run_one_function(
                {"name": tool_name, "arguments": arguments}
            )
        except Exception as exc:  # a sub-tool must never abort the whole run
            result = {"status": "error", "error": f"{type(exc).__name__}: {exc}"}
        with self._lock:
            self._cache[key] = result
            self.calls_made += 1
        return result

    def fresh(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Re-issue a call, ignoring any memoized result (used by retries)."""
        return self(tool_name, arguments, bypass_cache=True)


# --------------------------------------------------------------------------- #
# Engine
# --------------------------------------------------------------------------- #
class UnifiedModelEngine:
    """Resolve once, fan out to backends, return canonical records."""

    def __init__(self, tooluniverse=None):
        self.tu = _get_tooluniverse(tooluniverse)
        self.registry = load_registry()

    # -------------------------------------------------------------- resolve #
    def resolve(
        self, task: TaskSpec, arguments: Dict[str, Any], caller: _Caller
    ) -> Dict[str, Any]:
        resolver = get_resolver(task.resolver or task.id)
        return resolver(arguments, caller)

    # ------------------------------------------------------------- selection #
    def select(
        self,
        task: TaskSpec,
        resolved: Dict[str, Any],
        requested: Optional[List[str]],
        caller: _Caller,
    ) -> Tuple[List[BackendSpec], List[Dict[str, str]]]:
        """Split the candidate backends into runnable ones and skipped ones.

        Every skip carries a reason in the caller's terms -- a missing API key,
        an unsupported property, an input that did not resolve -- because
        "eight of fourteen models ran" is only interpretable alongside why the
        other six did not.
        """
        runnable: List[BackendSpec] = []
        skipped: List[Dict[str, str]] = []
        prop = resolved.get("property")

        for spec in self.registry.resolve_backends(task.id, requested):
            if spec.property_map:
                specialized = spec.for_property(prop) if prop else None
                if specialized is None:
                    skipped.append(
                        {
                            "backend": spec.id,
                            "model": spec.display_name,
                            "reason": "unsupported_property",
                            "detail": (
                                f"{spec.display_name} does not predict '{prop}'. It "
                                f"covers: {', '.join(spec.properties[:12])}"
                                + ("..." if len(spec.properties) > 12 else "")
                            ),
                        }
                    )
                    continue
                spec = specialized

            if spec.requires_key() and not spec.key_available():
                skipped.append(
                    {
                        "backend": spec.id,
                        "model": spec.display_name,
                        "reason": "missing_api_key",
                        "detail": f"Set {spec.api_key} to enable this backend.",
                    }
                )
                continue

            # A backend reading a lazily-fetched shared payload triggers that
            # fetch now, so the requirement check below sees the real state.
            # This keys off `needs` as well as `from_context`: a backend can
            # depend on a lazy payload while reading it through its input_map
            # rather than wholesale (Evo 2 takes only the `dna` field of the
            # genome window), and keying off from_context alone left those
            # skipped as "input_not_resolved" for a payload nobody fetched.
            wanted = set(spec.needs)
            if spec.from_context:
                wanted.add(spec.from_context)
            for key in wanted:
                root = key.split(".", 1)[0]
                if root not in resolved and _is_lazy_context(task.id, root):
                    ensure_context(resolved, root, caller)

            missing = spec.missing_requirements(resolved)
            if missing:
                skipped.append(
                    {
                        "backend": spec.id,
                        "model": spec.display_name,
                        "reason": "input_not_resolved",
                        "detail": (
                            f"Needs {', '.join(missing)}, which could not be derived "
                            "from the input supplied."
                        ),
                    }
                )
                continue
            runnable.append(spec)

        return runnable, skipped

    # --------------------------------------------------------------- execute #
    def run_backend(
        self, spec: BackendSpec, resolved: Dict[str, Any], caller: _Caller
    ) -> Dict[str, Any]:
        """Run one backend and return its canonical record. Never raises."""
        if not spec.thread_safe:
            with _lock_for(spec.id):
                return self._run_backend_inner(spec, resolved, caller)
        return self._run_backend_inner(spec, resolved, caller)

    def _run_backend_inner(
        self, spec: BackendSpec, resolved: Dict[str, Any], caller: _Caller
    ) -> Dict[str, Any]:
        started = time.time()
        record: Dict[str, Any] = {
            "backend": spec.id,
            "model": spec.display_name,
            "model_family": spec.model.get("family"),
            "tool": spec.tool,
            "calibration": spec.calibration,
            "group": spec.group,
        }
        try:
            if spec.from_context:
                payload = resolved.get(spec.from_context)
                arguments = None
                record["source"] = (
                    f"read from the cached {spec.tool} payload fetched during "
                    "input resolution (no additional request)"
                )
            else:
                arguments = spec.build_arguments(resolved)
                payload = caller(spec.tool, arguments)

            error = _payload_error(payload)
            if error:
                record.update({"status": "error", "error": error})
                if arguments is not None:
                    record["arguments"] = arguments
                return record

            fields = spec.normalize(payload)
            record.update(fields)
            if arguments is not None:
                record["arguments"] = arguments
            record["status"] = (
                "success" if fields.get("score") is not None else "no_score"
            )
            if record["status"] == "no_score":
                # The cause differs by backend kind, and guessing wrong sends
                # the reader down the wrong path: a precomputed predictor is
                # usually missing the entry, while a model computing live is
                # usually a mapping or input fault on our side.
                if spec.cost == "local_model" or spec.from_context is None:
                    cause = (
                        "It computes live, so this is more likely a mapping or "
                        "input problem than a missing entry -- check "
                        "'resolved_input' and the backend's output paths."
                    )
                else:
                    cause = (
                        "It serves a precomputed table, so this variant is most "
                        "likely absent from it."
                    )
                record["error"] = (
                    f"{spec.display_name} was reachable but returned no score for "
                    f"this input. {cause}"
                )
            if spec.citation_text:
                record["citation"] = spec.citation_text
            if spec.notes:
                record["notes"] = spec.notes
        except Exception as exc:
            record.update({"status": "error", "error": f"{type(exc).__name__}: {exc}"})
        finally:
            record["latency_s"] = round(time.time() - started, 3)
        return record

    def run_many(
        self,
        specs: List[BackendSpec],
        resolved: Dict[str, Any],
        caller: _Caller,
        max_workers: int = _DEFAULT_WORKERS,
    ) -> List[Dict[str, Any]]:
        if not specs:
            return []
        if len(specs) == 1:
            return [self.run_backend(specs[0], resolved, caller)]

        results: Dict[str, Dict[str, Any]] = {}
        with ThreadPoolExecutor(max_workers=min(max_workers, len(specs))) as pool:
            futures = {
                pool.submit(self.run_backend, spec, resolved, caller): spec
                for spec in specs
            }
            for future in as_completed(futures):
                spec = futures[future]
                try:
                    results[spec.id] = future.result()
                except Exception as exc:
                    results[spec.id] = {
                        "backend": spec.id,
                        "model": spec.display_name,
                        "status": "error",
                        "error": f"{type(exc).__name__}: {exc}",
                    }
        # Preserve the registry's order so repeated runs are diffable.
        return [results[spec.id] for spec in specs if spec.id in results]


def _score_against_reference(
    records: List[Dict[str, Any]], resolved: Dict[str, Any]
) -> None:
    """Add measured lDDT to every prediction that returned coordinates.

    pLDDT is what a folder *claims*; lDDT is what it achieved. Reporting both
    also exposes miscalibration -- ESMFold on ubiquitin scored lDDT 97.8 while
    reporting pLDDT 91.0, i.e. honestly underconfident -- which a leaderboard
    built on pLDDT alone could never show.
    """
    reference = resolved.get("reference_structure")
    if not reference:
        return
    from .unified_model_metrics import dockq, lddt, parse_atoms_by_chain

    multichain = len(parse_atoms_by_chain(reference)) > 1

    for record in records:
        structure = record.get("structure")
        if not isinstance(structure, str) or not structure:
            continue
        try:
            result = lddt(structure, reference)
        except Exception as exc:
            record["lddt_error"] = f"{type(exc).__name__}: {exc}"
            continue
        if not result:
            record["lddt_error"] = (
                "No residues matched the reference by chain and number, so lDDT "
                "could not be computed."
            )
            continue
        record["lddt"] = result["lddt"]
        record["lddt_coverage"] = result["coverage"]
        record["n_residues_scored"] = result["n_residues_scored"]
        plddt = record.get("mean_plddt")
        if isinstance(plddt, (int, float)):
            # Positive = the model was more confident than it was accurate.
            record["calibration_gap"] = round(plddt - result["lddt"] * 100, 2)

        # lDDT judges a fold; it says nothing about whether two chains were put
        # together correctly. For a multi-chain reference, score the interface
        # too -- that is the question for complexes, binders and docking.
        if multichain:
            try:
                interface = dockq(structure, reference)
            except Exception as exc:
                record["dockq_error"] = f"{type(exc).__name__}: {exc}"
                continue
            if interface:
                record["dockq"] = interface["dockq"]
                record["dockq_quality"] = interface["quality"]
                record["fnat"] = interface["fnat"]
                record["irms"] = interface["irms"]
                record["lrms"] = interface["lrms"]


def _is_lazy_context(task_id: str, key: str) -> bool:
    """True when ``key`` names a payload the resolver fetches on demand."""
    from .unified_model_resolvers import CONTEXT_PROVIDERS

    return key in (CONTEXT_PROVIDERS.get(task_id) or {})


def _payload_error(payload: Any) -> Optional[str]:
    if payload is None:
        return "Backend returned no payload."
    if isinstance(payload, dict):
        if payload.get("status") == "error":
            return str(payload.get("error") or "Backend reported an error.")
        if "error" in payload and payload.get("status") != "success":
            return str(payload["error"])
    if isinstance(payload, str) and payload.startswith("Error:"):
        return payload
    return None


# --------------------------------------------------------------------------- #
# Consensus
# --------------------------------------------------------------------------- #
def summarize(records: List[Dict[str, Any]], task: TaskSpec) -> Dict[str, Any]:
    """Agreement across backends for a single input.

    Two things are deliberately kept out of the headline consensus.

    *Different questions.* SpliceAI scores splicing disruption and CancerVar
    scores somatic oncogenicity; neither is answering "is this missense change
    damaging to protein function". Averaging them in made TP53 R175H -- which
    every germline predictor calls pathogenic -- report ``agreement: weak``
    with SpliceAI as an outlier, when the real finding was unanimity among the
    models that were asked the same thing. Secondary groups are reported in
    full, under their own heading.

    *Different units.* Backends whose transform is deliberately ``none`` (a
    kcal/mol binding energy, a diffusion confidence logit) have no common axis,
    so they are listed but never folded into an average.
    """
    primary = [r for r in records if r.get("group", "primary") == "primary"]
    secondary = [r for r in records if r.get("group", "primary") != "primary"]

    summary = _summarize_group(primary, task)
    summary["n_backends_run"] = len(records)

    if secondary:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for record in secondary:
            groups.setdefault(record.get("group"), []).append(record)
        summary["other_questions"] = {
            name: {
                "backends": [r.get("backend") for r in members],
                "calls": {
                    r.get("backend"): r.get("call")
                    for r in members
                    if r.get("status") == "success"
                },
                "scores": {
                    r.get("backend"): r.get("score")
                    for r in members
                    if r.get("status") == "success"
                },
            }
            for name, members in groups.items()
        }
        summary["other_questions_note"] = (
            "These backends answer a different question from the primary group, so "
            "they are reported separately and are not part of the consensus. "
            "Disagreement with the primary call is expected and is not evidence "
            "against it."
        )
    return summary


def _summarize_group(records: List[Dict[str, Any]], task: TaskSpec) -> Dict[str, Any]:
    scored = [r for r in records if r.get("status") == "success"]
    normalized = [
        r for r in scored if isinstance(r.get("normalized_score"), (int, float))
    ]
    calls = [r.get("call") for r in scored if r.get("call")]

    summary: Dict[str, Any] = {
        "n_primary_backends": len(records),
        "n_succeeded": len(scored),
        "n_failed": len(records) - len(scored),
    }

    if normalized:
        values = [r["normalized_score"] for r in normalized]
        mean = sum(values) / len(values)
        summary["consensus_normalized_score"] = round(mean, 4)
        summary["normalized_score_range"] = [
            round(min(values), 4),
            round(max(values), 4),
        ]
        summary["n_in_consensus"] = len(normalized)
        spread = max(values) - min(values)
        summary["spread"] = round(spread, 4)
        # A wide spread is the single most useful signal a multi-model call
        # produces: it says the models genuinely disagree, which is a reason to
        # look at the variant rather than to trust the average.
        summary["agreement"] = (
            "strong" if spread <= 0.25 else "moderate" if spread <= 0.5 else "weak"
        )
        outliers = [
            r["backend"]
            for r in normalized
            if abs(r["normalized_score"] - mean) > max(0.3, spread * 0.6)
        ]
        if outliers:
            summary["outliers"] = outliers

    excluded = [r["backend"] for r in scored if r.get("normalized_score") is None]
    if excluded:
        summary["excluded_from_consensus"] = excluded
        summary["excluded_reason"] = (
            "These backends report a quantity with no common axis (raw units, or a "
            "class label), so they are shown but not averaged."
        )

    if calls:
        tally: Dict[str, int] = {}
        for call in calls:
            tally[call] = tally.get(call, 0) + 1
        summary["call_tally"] = tally
        majority = max(tally.items(), key=lambda kv: kv[1])
        summary["majority_call"] = majority[0]
        summary["majority_fraction"] = round(majority[1] / len(calls), 3)
        summary["unanimous"] = len(tally) == 1
        if task.positive_class:
            summary["positive_class"] = task.positive_class

    return summary


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #
class _UnifiedBase(BaseTool):
    """Shared plumbing: bind the task from config, build the engine lazily."""

    def __init__(self, tool_config: Optional[Dict[str, Any]] = None, tooluniverse=None):
        super().__init__(tool_config or {})
        self.tool_config = tool_config or {}
        self._injected_tu = tooluniverse
        self._engine: Optional[UnifiedModelEngine] = None

    @property
    def engine(self) -> UnifiedModelEngine:
        if self._engine is None:
            self._engine = UnifiedModelEngine(self._injected_tu)
        return self._engine

    def _task(self, arguments: Dict[str, Any]) -> TaskSpec:
        task_id = (self.tool_config.get("fields") or {}).get("task") or arguments.get(
            "task"
        )
        if not task_id:
            raise KeyError(
                "No task bound to this tool and none supplied. Pass 'task' or use "
                "one of the task-specific tools."
            )
        return self.engine.registry.task(task_id)


@register_tool("UnifiedModelPredictTool")
class UnifiedModelPredictTool(_UnifiedBase):
    """The single agent-facing tool per task: run one model, or all of them.

    This absorbed what used to be three separate tools. ``predict`` and
    ``compare`` shared 13 of their 18 parameters and ran the identical
    resolution path -- the only real difference was whether ``backend`` held
    one id or several, which is a parameter, not a tool. ``list`` had a single
    parameter and is now a flag.

    Benchmarking deliberately does NOT live here. It takes a dataset rather
    than an input, returns a leaderboard rather than a prediction, and costs
    minutes and hundreds of billable API calls; that is a maintainer's
    operation, not something an agent solving a task should be able to trigger
    by setting a flag. It stays available in Python via
    ``UnifiedModelBenchmarkTool`` and ``scripts/run_model_benchmark.py``.
    """

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = dict(arguments or {})
        try:
            task = self._task(args)
        except KeyError as exc:
            return {"status": "error", "error": str(exc)}

        if args.get("list_models"):
            return self._list_models(task, args)

        caller = _Caller(self.engine.tu)
        try:
            resolved = self.engine.resolve(task, args, caller)
        except ResolutionError as exc:
            return {"status": "error", "error": str(exc), "task": task.id}
        except Exception as exc:
            return {
                "status": "error",
                "error": f"Input resolution failed: {type(exc).__name__}: {exc}",
                "task": task.id,
            }

        requested = _as_list(args.get("backend") or args.get("backends"))
        runnable, skipped = self.engine.select(task, resolved, requested, caller)
        if not runnable:
            return {
                "status": "error",
                "task": task.id,
                "error": _no_model_error(task, skipped),
                "skipped": skipped,
                "input": _public_resolved(resolved),
                "resolution_notes": resolved.get("notes") or None,
            }

        records = self.engine.run_many(
            runnable, resolved, caller, int(args.get("max_workers") or _DEFAULT_WORKERS)
        )
        # Score accuracy against the reference BEFORE the bulky coordinates are
        # dropped, or include_raw=false would silently disable the measurement.
        _score_against_reference(records, resolved)

        if not args.get("include_raw"):
            for record in records:
                record.pop("structure", None)
                record.pop("pose", None)

        table = [
            {
                "backend": r.get("backend"),
                "model": r.get("model"),
                "score": r.get("score"),
                "score_type": r.get("score_type"),
                "units": r.get("score_units"),
                "normalized_score": r.get("normalized_score"),
                "call": r.get("call"),
                "call_label": r.get("call_label"),
                "lddt": r.get("lddt"),
                "calibration_gap": r.get("calibration_gap"),
                "dockq": r.get("dockq"),
                "dockq_quality": r.get("dockq_quality"),
                "calibration": r.get("calibration"),
                "status": r.get("status"),
                "error": r.get("error"),
            }
            for r in records
        ]

        # A reply is only a success if some model actually produced a score.
        # Reporting "success" while every prediction carries an error invites a
        # caller to read the envelope and not the contents.
        n_scored = sum(1 for r in records if r.get("status") == "success")
        out: Dict[str, Any] = {
            "status": "success" if n_scored else "no_score",
            "task": task.id,
            "input": _public_resolved(resolved),
            "predictions": table,
            "skipped": skipped,
            "resolution_notes": resolved.get("notes") or None,
            "resolution_sources": sorted(set(resolved.get("sources") or [])),
            "efficiency": {
                "tool_calls_made": caller.calls_made,
                "tool_calls_deduplicated": caller.calls_saved,
            },
        }
        if not n_scored:
            out["error"] = (
                f"{len(records)} model(s) ran but none returned a score. "
                + "; ".join(
                    f"{r['backend']}: {r.get('error')}"
                    for r in records
                    if r.get("error")
                )[:400]
            )
        # A consensus over one model is noise, so it is only reported when
        # several actually ran.
        if len(records) > 1:
            out["summary"] = summarize(records, task)
            out["interpretation_guide"] = (
                "'score' is each model's native output on its own scale; "
                "'normalized_score' is a monotone 0-1 rescaling for side-by-side "
                "reading, not a probability. Check 'calibration': 'heuristic' means "
                "the threshold is our estimate, not the model's published cutoff. A "
                "wide 'spread' in the summary means the models genuinely disagree."
            )
        if args.get("include_details", True):
            out["details"] = records
        return out

    # ------------------------------------------------------------------ #
    def _list_models(self, task: TaskSpec, args: Dict[str, Any]) -> Dict[str, Any]:
        """The catalogue, with no input and no computation."""
        registry = self.engine.registry
        backends = []
        for spec in registry.backends_for(task.id):
            entry = {
                "backend": spec.id,
                "model": spec.display_name,
                "family": spec.model.get("family"),
                "underlying_tool": spec.tool,
                "score_type": spec.score_type,
                "units": spec.score_units,
                "direction": (
                    None
                    if spec.higher_is_positive is None
                    else ("higher = more " + (task.positive_class or "positive"))
                    if spec.higher_is_positive
                    else ("lower = more " + (task.positive_class or "positive"))
                ),
                "calibration": spec.calibration,
                "cost": spec.cost,
                "requires_api_key": spec.api_key,
                "available_now": spec.key_available(),
                # Whether this backend's output mapping has ever been checked
                # against a real response. A False here means the score, if one
                # comes back, has not been confirmed to be the right field.
                "output_verified": spec.output_verified,
                "citation": spec.model.get("citation"),
                "url": spec.model.get("url"),
            }
            if spec.property_map:
                entry["properties"] = spec.properties
            if not spec.output_verified and spec.output_unverified_reason:
                entry["output_unverified_reason"] = spec.output_unverified_reason
            if spec.notes and args.get("include_notes", True):
                entry["notes"] = spec.notes
            backends.append(entry)

        return {
            "status": "success",
            "task": task.id,
            "title": task.title,
            "description": task.description,
            "canonical_output": task.output_fields,
            "positive_class": task.positive_class,
            "n_models": len(backends),
            "n_available_now": sum(1 for b in backends if b["available_now"]),
            "models": backends,
        }


def _no_model_error(task: TaskSpec, skipped: List[Dict[str, str]]) -> str:
    """A self-contained explanation of why nothing ran.

    The message has to carry the reasons itself. It previously said "see
    'skipped' for why" -- but the CLI renders only the error string and drops
    sibling fields, so it pointed the reader at something they could not see.
    """
    if not skipped:
        return f"No {task.id} model could run on this input."

    by_reason: Dict[str, List[Dict[str, str]]] = {}
    for entry in skipped:
        by_reason.setdefault(entry.get("reason", "unknown"), []).append(entry)

    parts = []
    for reason, entries in sorted(by_reason.items(), key=lambda kv: -len(kv[1])):
        names = ", ".join(e["backend"] for e in entries[:4])
        if len(entries) > 4:
            names += f" and {len(entries) - 4} more"
        detail = entries[0].get("detail", "")
        parts.append(f"{len(entries)} skipped ({reason}: {names}) -- {detail}")

    keys = sorted(
        {
            e["detail"].split("Set ", 1)[1].split(" ", 1)[0]
            for e in skipped
            if e.get("reason") == "missing_api_key" and "Set " in e.get("detail", "")
        }
    )
    hint = f" Setting {' or '.join(keys)} would enable more models." if keys else ""
    return f"No {task.id} model could run on this input. " + " ".join(parts) + hint


def _as_list(value: Any) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def _public_resolved(resolved: Dict[str, Any]) -> Dict[str, Any]:
    """Echo what the input resolved to, without the bulky cached payloads.

    Showing the resolution is not decoration: when models disagree, the first
    question is whether they were all scoring the same variant, and this is the
    answer to it.
    """
    hidden = {
        "protvar",
        "vep",
        "dbnsfp",
        "protvar_canonical",
        "vep_consequence",
        "sequence",
        "sequences",
        # Reported separately as 'resolution_notes'/'resolution_sources'.
        "notes",
        "sources",
    }
    public = {
        k: v
        for k, v in resolved.items()
        if k not in hidden and not k.startswith("_") and v not in (None, {}, [])
    }
    if resolved.get("sequence"):
        public["sequence_length"] = len(resolved["sequence"])
    if resolved.get("sequences"):
        public["chain_lengths"] = [len(seq) for seq in resolved["sequences"]]
    return public


@register_tool("UnifiedModelBenchmarkTool")
class UnifiedModelBenchmarkTool(_UnifiedBase):
    """Score every backend for a task over a public dataset and rank them.

    The output is a leaderboard, but the parts around it are what make it
    trustworthy: per-backend coverage (so a model cannot win by only answering
    the easy items), leakage warnings (so a model cannot win by having been
    trained on the labels), and a between-model correlation matrix (so two
    models that are 0.98 correlated are not read as independent evidence).
    """

    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        args = dict(arguments or {})
        from . import unified_model_datasets as datasets_module

        try:
            task = self._task(args)
        except KeyError as exc:
            return {"status": "error", "error": str(exc)}

        if args.get("list_datasets"):
            return {"status": "success", "datasets": datasets_module.catalogue()}

        caller = _Caller(self.engine.tu)
        dataset_name = args.get("dataset")
        if not dataset_name:
            return {
                "status": "error",
                "error": (
                    "No 'dataset' given. Call with list_datasets=true to see what is "
                    "available for this task."
                ),
                "datasets": datasets_module.catalogue(),
            }

        options = {
            key: args[key]
            for key in (
                "assay",
                "property",
                "path",
                "label_field",
                "gene",
                "limit",
                "seed",
                "task",
            )
            if args.get(key) is not None
        }
        options.setdefault("limit", int(args.get("limit") or 50))
        if dataset_name == "clinvar_missense":
            options["caller"] = caller

        try:
            dataset = datasets_module.load(dataset_name, **options)
        except Exception as exc:
            return {"status": "error", "error": f"Could not load dataset: {exc}"}

        if not dataset.items:
            return {
                "status": "error",
                "error": f"Dataset {dataset_name!r} loaded but produced no scorable items.",
                "dataset": dataset.describe(),
            }
        if dataset.task not in (task.id, "unknown", "any"):
            return {
                "status": "error",
                "error": (
                    f"Dataset {dataset_name!r} is for task {dataset.task!r}, but this "
                    f"tool benchmarks {task.id!r}."
                ),
            }

        requested = _as_list(args.get("backends") or args.get("backend"))
        item_workers = int(args.get("item_workers") or 3)
        backend_workers = int(args.get("max_workers") or 4)

        results, skip_tally = self._score_dataset(
            task, dataset, requested, caller, item_workers, backend_workers
        )
        return self._report(
            task, dataset, results, skip_tally, caller, args, datasets_module
        )

    # ------------------------------------------------------------------ #
    def _score_dataset(
        self, task, dataset, requested, caller, item_workers, backend_workers
    ):
        """Run every backend over every item, keeping results index-aligned.

        Alignment is the whole contract here: ``results[backend][i]`` must
        correspond to ``dataset.items[i]`` even when an item fails to resolve
        or a backend is skipped for it, because coverage and every metric are
        computed from those positions.
        """
        n = len(dataset.items)
        results: Dict[str, List[Optional[Dict[str, Any]]]] = {}
        skip_tally: Dict[str, Dict[str, int]] = {}

        def score_one(
            index: int,
        ) -> Tuple[int, Dict[str, Dict[str, Any]], List[Dict[str, str]]]:
            item = dict(dataset.items[index])
            item.pop("label", None)
            item.pop("continuous_label", None)
            try:
                resolved = self.engine.resolve(task, item, caller)
            except Exception as exc:
                return index, {}, [{"backend": "*", "reason": f"unresolved: {exc}"}]
            runnable, skipped = self.engine.select(task, resolved, requested, caller)
            records = self.engine.run_many(runnable, resolved, caller, backend_workers)
            for record in records:
                record.pop("structure", None)
                record.pop("pose", None)
                record.pop("arguments", None)
                record.pop("notes", None)
            return index, {r["backend"]: r for r in records}, skipped

        rows: List[Optional[Dict[str, Dict[str, Any]]]] = [None] * n
        with ThreadPoolExecutor(max_workers=max(1, item_workers)) as pool:
            futures = [pool.submit(score_one, i) for i in range(n)]
            for future in as_completed(futures):
                try:
                    index, by_backend, skipped = future.result()
                except Exception:
                    continue
                rows[index] = by_backend
                for entry in skipped:
                    bucket = skip_tally.setdefault(entry["backend"], {})
                    bucket[entry["reason"]] = bucket.get(entry["reason"], 0) + 1

        seen: List[str] = []
        for row in rows:
            for backend in row or {}:
                if backend not in seen:
                    seen.append(backend)
        for backend in seen:
            results[backend] = [(row or {}).get(backend) for row in rows]
        return results, skip_tally

    # ------------------------------------------------------------------ #
    def _report(
        self, task, dataset, results, skip_tally, caller, args, datasets_module
    ):
        from . import unified_model_metrics as metrics_module

        labels = dataset.labels
        continuous = [item.get("continuous_label") for item in dataset.items]
        if not any(v is not None for v in continuous):
            continuous = None
        n = len(dataset.items)
        label_type = dataset.label_type
        task_type = "binary_score" if label_type == "binary" else "regression"
        positive_call = task.positive_class or "positive"
        leakage = datasets_module.LEAKAGE_RISK.get(dataset.id, {})
        requested_metrics = _as_list(args.get("metrics"))

        # A multi-property backend's direction, units and calibration live on
        # its *specialized* spec, not the base one. ADMET-AI's base entry
        # declares transform "none" (it has no single score), so looking up the
        # base spec reported higher_is_positive=None and silently dropped AUROC
        # and AUPRC from every ADMET benchmark -- the exact metrics the TDC
        # leaderboard is scored on.
        dataset_property = next(
            (i.get("property") for i in dataset.items if i.get("property")), None
        )

        def effective(backend_id):
            spec = self.engine.registry.backend(task.id, backend_id)
            if spec.property_map and dataset_property:
                return spec.for_property(dataset_property) or spec
            return spec

        leaderboard = []
        for backend_id, records in results.items():
            try:
                spec = effective(backend_id)
                direction = spec.higher_is_positive
                display = spec.display_name
                calibration = spec.calibration
                group = spec.group
            except KeyError:
                direction, display, calibration, group = (
                    True,
                    backend_id,
                    "unknown",
                    "primary",
                )

            scored = metrics_module.evaluate(
                records,
                labels,
                direction,
                positive_call,
                task_type,
                n,
                requested_metrics,
                continuous_labels=continuous,
            )
            row = {
                "backend": backend_id,
                "model": display,
                "group": group,
                "calibration": calibration,
                **scored,
            }
            if backend_id in leakage:
                row["leakage_warning"] = leakage[backend_id]
            errors = [r.get("error") for r in records if r and r.get("error")]
            if errors:
                row["example_error"] = errors[0][:200]
                row["n_errors"] = len(errors)
            leaderboard.append(row)

        primary = task.primary_metric if label_type == "binary" else "spearman"
        if requested_metrics:
            primary = requested_metrics[0]
        # A model that answered three items can top any metric, so anything
        # below half coverage sorts last regardless of its score.
        leaderboard.sort(
            key=lambda r: (
                r.get("group") == "primary",
                (r.get("coverage") or 0) >= 0.5,
                r.get(primary) if isinstance(r.get(primary), (int, float)) else -1,
            ),
            reverse=True,
        )

        report: Dict[str, Any] = {
            "status": "success",
            "task": task.id,
            "dataset": dataset.describe(),
            "ranked_by": primary,
            "leaderboard": leaderboard,
            "n_backends_scored": len(leaderboard),
            "tool_calls": {
                "made": caller.calls_made,
                "deduplicated": caller.calls_saved,
            },
        }

        directions = {}
        for backend_id in results:
            try:
                directions[backend_id] = effective(backend_id).higher_is_positive
            except KeyError:
                directions[backend_id] = True
        correlation = _model_correlation(results, directions)
        if correlation:
            report["model_correlation"] = correlation
            report["model_correlation_note"] = (
                "Spearman correlation between backends over the items both scored, "
                "after orienting every score so that higher means more of the "
                "positive class. High positive values mean the models are not "
                "independent evidence -- REVEL is an ensemble that includes SIFT "
                "and PolyPhen-2, and several of these share training data. A "
                "negative value means genuine disagreement, not a difference in "
                "sign convention."
            )

        if skip_tally:
            report["skipped_counts"] = skip_tally
        if leakage:
            affected = [
                row["backend"] for row in leaderboard if row.get("leakage_warning")
            ]
            if affected:
                report["leakage_warning"] = (
                    f"{len(affected)} backend(s) in this leaderboard have seen labels from "
                    f"{dataset.id} in training or consult it at query time: "
                    f"{', '.join(affected)}. Their scores here measure recall of the "
                    "answer key, not predictive skill, and should not be compared with "
                    "the rest. proteingym_dms uses experimental measurements and has no "
                    "such overlap."
                )
        report["caveats"] = [
            "Rank metrics (AUROC, AUPRC, Spearman) are computed on each backend's "
            "native score and its declared direction, never on normalized_score, so "
            "the heuristic calibrations cannot affect the ranking.",
            "Threshold metrics (accuracy, MCC, F1) use each backend's own cutoff; "
            "where 'calibration' is 'heuristic' that cutoff is our estimate, so a low "
            "accuracy beside a high AUROC means a mis-set threshold, not a weak model.",
            "'coverage' is the fraction of items a backend actually scored. Compare "
            "models on it before comparing them on anything else.",
        ]
        if continuous is not None:
            report["caveats"].append(
                "'spearman' here is against the measured continuous value, which is "
                "the metric ProteinGym itself ranks models on; AUROC uses the "
                "dataset's own binarization of that same measurement."
            )
        if args.get("include_per_item"):
            report["per_item"] = [
                {
                    "id": dataset.items[i].get("id"),
                    "label": labels[i],
                    "scores": {
                        backend: (records[i] or {}).get("score")
                        for backend, records in results.items()
                    },
                }
                for i in range(n)
            ]
        return report


def _model_correlation(
    results: Dict[str, List[Optional[Dict[str, Any]]]],
    directions: Optional[Dict[str, Optional[bool]]] = None,
) -> Dict[str, Dict[str, float]]:
    """Pairwise Spearman between backends, over the items both of them scored.

    Scores are oriented by each backend's declared direction first. Without
    that step the matrix measures sign conventions rather than agreement:
    AlphaMissense (higher = damaging) against ESM-1v (a log-likelihood ratio,
    lower = damaging) came out at -0.897 on a set where the two agree almost
    perfectly. That reads as "these models contradict each other" -- the exact
    opposite of the truth, and precisely the conclusion this matrix exists to
    support.

    Backends with no ranking direction at all (categorical classifiers) are
    left out rather than assumed to point upwards.
    """
    from . import unified_model_metrics as metrics_module

    directions = directions or {}
    backends = [b for b in results if directions.get(b, True) is not None]
    if len(backends) < 2:
        return {}

    def oriented(backend: str, index: int) -> Optional[float]:
        value = (results[backend][index] or {}).get("score")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value) if directions.get(backend, True) else -float(value)

    matrix: Dict[str, Dict[str, float]] = {}
    for i, left in enumerate(backends):
        for right in backends[i + 1 :]:
            usable = [
                (a, b)
                for a, b in (
                    (oriented(left, k), oriented(right, k))
                    for k in range(len(results[left]))
                )
                if a is not None and b is not None
            ]
            if len(usable) < 5:
                continue
            rho = metrics_module.spearman(
                [a for a, _ in usable], [b for _, b in usable]
            )
            if rho is not None:
                matrix.setdefault(left, {})[right] = round(rho, 3)
    return matrix
