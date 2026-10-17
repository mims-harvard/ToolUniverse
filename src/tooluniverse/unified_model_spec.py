"""Core of the unified ML-model interface: task specs, backend adapters, score calibration.

ToolUniverse wraps many interchangeable predictors. Nine different tools answer
"how damaging is this missense variant?", six answer "fold this sequence", and
so on -- but each one takes different arguments, returns a differently shaped
payload, and reports a score on its own scale in its own direction. A caller who
wants a second opinion, and anyone who wants to *benchmark* these models against
each other, has to hand-write that translation every time.

This module is the translation layer, expressed as data rather than code:

``TaskSpec``
    A prediction problem (``variant_effect``, ``structure_prediction``,
    ``molecular_property``, ``binding_affinity``) with one canonical input shape,
    one canonical output shape, and the metric suite that scores it.

``BackendSpec``
    One model behind a task. It names an existing ToolUniverse tool, maps
    canonical input onto that tool's arguments, maps the tool's reply back onto
    the canonical output, and declares how to read its score.

``ScoreTransform``
    The piece that makes cross-model comparison possible at all. Backends
    disagree about scale *and* direction: CADD PHRED runs 0..99 with high =
    damaging, an ESM-2 log-likelihood ratio is unbounded with *negative* =
    damaging, AlphaMissense is already 0..1. A transform maps each onto a
    common ``normalized_score`` in [0, 1] where higher always means "more of
    the task's positive class".

    ``normalized_score`` is a documented monotone re-scaling, **not** a
    probability and not a claim that two models are calibrated to each other.
    It exists so that scores can be ranked, plotted and correlated on one axis.
    Every record keeps the backend-native ``score`` and its ``score_type``
    alongside it, and rank-based metrics (AUROC, Spearman) are computed on the
    native score so that the choice of transform cannot change a benchmark
    result.

Adding a backend is normally a JSON entry in
``data/unified_model_backends.json`` -- no Python. Backends whose payload is too
irregular for a declarative map (dbNSFP's per-transcript score arrays, for one)
name a normalizer function in ``unified_model_normalizers`` instead.
"""

from __future__ import annotations

import json
import math
import os
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

_REGISTRY_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "unified_model_backends.json"
)

_registry_lock = threading.Lock()
_registry_cache: Optional["ModelRegistry"] = None

# jsonpath-ng compilation is not free and the same handful of paths are applied
# to every item of a benchmark run, so keep the parsed expressions.
_path_cache: Dict[str, Any] = {}
_path_cache_lock = threading.Lock()


class UnifiedModelConfigError(ValueError):
    """The backend registry itself is malformed -- a bug in our config, not in a call."""


# --------------------------------------------------------------------------- #
# Path extraction
# --------------------------------------------------------------------------- #
def _compile_path(expr: str):
    with _path_cache_lock:
        cached = _path_cache.get(expr)
    if cached is not None:
        return cached
    from jsonpath_ng.ext import parse as _parse

    compiled = _parse(expr if expr.startswith("$") else "$." + expr)
    with _path_cache_lock:
        _path_cache[expr] = compiled
    return compiled


_AGGREGATORS: Dict[str, Callable[[List[Any]], Any]] = {
    "first": lambda vs: vs[0],
    "last": lambda vs: vs[-1],
    "max": lambda vs: max(vs),
    "min": lambda vs: min(vs),
    "mean": lambda vs: sum(vs) / len(vs),
    "list": lambda vs: list(vs),
    # "abs_max" picks the most extreme value regardless of sign -- the right
    # choice for a signed effect score (a -4.1 LLR is a stronger call than
    # +0.2), where plain max() would return the least interesting transcript.
    "abs_max": lambda vs: max(
        vs, key=lambda v: abs(v) if isinstance(v, (int, float)) else 0
    ),
}


def extract(payload: Any, spec: Any) -> Any:
    """Pull one canonical field out of a backend's raw reply.

    ``spec`` is either a path string or ``{"path": ..., "agg": ..., "default": ...}``.
    Many bioinformatics payloads carry a *list* where a scalar is wanted -- one
    score per transcript, one per model seed -- so ``agg`` says which one the
    canonical record should carry. Without an explicit ``agg`` a multi-valued
    match collapses to its first element, which is what a caller reading a
    single number expects.
    """
    if spec is None:
        return None
    mul = None
    if isinstance(spec, str):
        path, agg, default = spec, "first", None
    elif isinstance(spec, dict):
        if "const" in spec:
            return spec["const"]
        path = spec.get("path")
        agg = spec.get("agg", "first")
        default = spec.get("default")
        mul = spec.get("mul")
        if path is None:
            return default
    else:
        raise UnifiedModelConfigError(f"Unsupported output_map entry: {spec!r}")

    try:
        matches = [m.value for m in _compile_path(path).find(payload)]
    except Exception:
        return default

    # Flatten one level: a path ending at a list field yields a single match
    # whose value is that list, and the aggregator wants the elements.
    if len(matches) == 1 and isinstance(matches[0], list):
        matches = matches[0]

    values = [_coerce_number(v) for v in matches if v is not None]
    if not values:
        return default
    if mul is not None:
        # Backends disagree about the units of the *same* quantity: ESMFold
        # reports mean pLDDT on 0..1 while NVIDIA NIM and AlphaFold report the
        # same statistic on 0..100. Reconciling that here, rather than in the
        # consumer, is the whole point of a canonical output -- otherwise a
        # comparison table silently puts 0.9 next to 90.
        # Rounded: 0.58 * 100 is 57.99999999999999 in binary floating point,
        # and a pLDDT printed to 14 decimal places reads as false precision on
        # a statistic that is only meaningful to about one.
        values = [
            round(v * mul, 6)
            if isinstance(v, (int, float)) and not isinstance(v, bool)
            else v
            for v in values
        ]
    if agg == "list":
        return values
    if len(values) == 1:
        return values[0]

    fn = _AGGREGATORS.get(agg)
    if fn is None:
        raise UnifiedModelConfigError(f"Unknown aggregator {agg!r}")
    try:
        return fn(values)
    except (TypeError, ValueError):
        # Heterogeneous or non-numeric values: fall back rather than blow up a
        # whole benchmark run over one odd record.
        return values[0]


def render(template: Any, context: Dict[str, Any]) -> Any:
    """Fill a backend's argument template from the resolved canonical input.

    A template that is exactly one placeholder (``"{genomic.pos}"``) yields the
    referenced value with its **type intact** -- a genomic position has to reach
    the backend as an int, not as ``"7577121"``. Anything else is string
    interpolation (``"{protein.ref_aa}{protein.position}{protein.alt_aa}"`` ->
    ``"R175H"``). A placeholder with no value resolves to ``None`` so that
    ``BackendSpec.build_arguments`` can drop the key.
    """
    if isinstance(template, dict):
        return {k: render(v, context) for k, v in template.items()}
    if isinstance(template, list):
        return [render(v, context) for v in template]
    if not isinstance(template, str):
        return template

    stripped = template.strip()
    if stripped.startswith("{") and stripped.endswith("}") and stripped.count("{") == 1:
        return _lookup(context, stripped[1:-1])

    out = []
    i = 0
    while i < len(template):
        ch = template[i]
        if ch == "{":
            close = template.find("}", i)
            if close == -1:
                out.append(template[i:])
                break
            value = _lookup(context, template[i + 1 : close])
            if value is None:
                return None
            out.append(str(value))
            i = close + 1
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _lookup(context: Dict[str, Any], dotted: str) -> Any:
    node: Any = context
    for part in dotted.split("."):
        if isinstance(node, dict):
            node = node.get(part)
        elif isinstance(node, list):
            try:
                node = node[int(part)]
            except (ValueError, IndexError):
                return None
        else:
            return None
        if node is None:
            return None
    return node


# --------------------------------------------------------------------------- #
# Score calibration
# --------------------------------------------------------------------------- #
@dataclass
class ScoreTransform:
    """Maps a backend-native score onto [0, 1], higher = more positive class.

    ``kind`` is one of:

    ``identity``
        Already 0..1 in the right direction (AlphaMissense pathogenicity).
    ``linear``
        Clamped rescale between ``lo`` and ``hi`` (CADD PHRED over 0..40 --
        40 rather than the theoretical 99 because essentially the entire
        deleterious mass sits below it, and a 0..99 range would squash every
        real call into the bottom third).
    ``logistic``
        ``1 / (1 + exp(-(x - x0) / k))`` for unbounded signed scores such as an
        ESM-2 log-likelihood ratio, where a hard clamp would throw away the
        tails that matter most.
    ``categorical``
        A label, not a number (ACMG classes, AMP/ASCO/CAP tiers): ``map`` gives
        each label its position on the same 0..1 axis.
    ``none``
        Deliberately not normalized. Used where a common axis would be a lie --
        a docking ``ΔG`` in kcal/mol and a DiffDock confidence logit are not two
        views of one quantity. These backends still report ``score`` and
        ``score_type``, and the compare/benchmark layers group them by unit
        rather than averaging across them.

    ``invert`` flips the axis and is applied last, for the backends where
    *lower* means more damaging (every log-likelihood-ratio model).
    """

    kind: str = "none"
    lo: Optional[float] = None
    hi: Optional[float] = None
    x0: float = 0.0
    k: float = 1.0
    invert: bool = False
    map: Dict[str, float] = field(default_factory=dict)

    @classmethod
    def from_config(cls, cfg: Optional[Dict[str, Any]]) -> "ScoreTransform":
        if not cfg:
            return cls()
        known = {f for f in ("kind", "lo", "hi", "x0", "k", "invert", "map")}
        unknown = set(cfg) - known
        if unknown:
            raise UnifiedModelConfigError(
                f"Unknown ScoreTransform keys: {sorted(unknown)}"
            )
        return cls(**cfg)

    def to_unit(self, score: Any) -> Optional[float]:
        if self.kind == "none" or score is None:
            return None

        if self.kind == "categorical":
            key = str(score).strip().lower()
            for label, value in self.map.items():
                if str(label).strip().lower() == key:
                    return _clamp(1.0 - value if self.invert else value)
            return None

        try:
            x = float(score)
        except (TypeError, ValueError):
            return None
        if math.isnan(x) or math.isinf(x):
            return None

        if self.kind == "identity":
            unit = x
        elif self.kind == "linear":
            if self.lo is None or self.hi is None or self.hi == self.lo:
                raise UnifiedModelConfigError(
                    "linear ScoreTransform needs distinct 'lo' and 'hi'"
                )
            unit = (x - self.lo) / (self.hi - self.lo)
        elif self.kind == "logistic":
            if self.k == 0:
                raise UnifiedModelConfigError("logistic ScoreTransform needs k != 0")
            # Guard the exponent: a large |z| overflows math.exp long before it
            # changes the answer, which is 0.0 or 1.0 either way.
            z = (x - self.x0) / self.k
            if z < -60:
                unit = 0.0
            elif z > 60:
                unit = 1.0
            else:
                unit = 1.0 / (1.0 + math.exp(-z))
        else:
            raise UnifiedModelConfigError(f"Unknown ScoreTransform kind {self.kind!r}")

        unit = _clamp(unit)
        return 1.0 - unit if self.invert else unit


def _coerce_number(value: Any) -> Any:
    """Read a number that arrived as a string.

    Confirmed live against SpliceAI, which returns its delta scores as
    ``"0.002"`` rather than ``0.002``. Left as-is, such a value compares and
    sorts as text -- ``"0.9" < "0.11"`` -- which would quietly corrupt every
    threshold and every benchmark metric downstream.
    """
    if isinstance(value, str):
        token = value.strip()
        if token and token[0] in "+-.0123456789":
            try:
                return (
                    float(token)
                    if ("." in token or "e" in token.lower())
                    else int(token)
                )
            except ValueError:
                return value
    return value


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# --------------------------------------------------------------------------- #
# Specs
# --------------------------------------------------------------------------- #
@dataclass
class BackendSpec:
    """One model behind one task."""

    id: str
    task: str
    tool: str
    model: Dict[str, Any] = field(default_factory=dict)
    input_map: Dict[str, Any] = field(default_factory=dict)
    output_map: Dict[str, Any] = field(default_factory=dict)
    needs: List[str] = field(default_factory=list)
    score_field: str = "score"
    score_type: str = ""
    score_units: Optional[str] = None
    transform: ScoreTransform = field(default_factory=ScoreTransform)
    call: Dict[str, Any] = field(default_factory=dict)
    api_key: Optional[str] = None
    normalizer: Optional[str] = None
    # Several backends are already paid for by the resolver. One
    # ``ProtVar_map_variant`` call returns AlphaMissense, EVE, ESM-1v, popEVE
    # *and* CADD alongside the coordinate mapping, so a backend that names
    # ``from_context`` reads that cached payload instead of re-issuing a
    # request -- five models for one round trip rather than six.
    from_context: Optional[str] = None
    # Where this backend's decision threshold and calibration range came from:
    # "published" (the model's own paper/docs) or "heuristic" (our estimate,
    # set from observed score ranges). Surfaced on every prediction so that a
    # caller can tell a real cutoff from a plausible one.
    calibration: str = "heuristic"
    # Free-form arguments for this backend's normalizer function.
    params: Dict[str, Any] = field(default_factory=dict)
    # Which question the backend actually answers. Backends in different
    # groups are reported separately rather than averaged: SpliceAI scores
    # splicing disruption and CancerVar scores somatic oncogenicity, so a
    # near-zero SpliceAI score on a damaging missense variant is agreement
    # about a different question, not dissent about this one. Folding them
    # into one consensus made a unanimous call look contested.
    group: str = "primary"
    # False for backends that run a model *in this process* rather than over
    # HTTP. Confirmed the hard way: ADMET-AI (chemprop + Lightning) raises
    # "pop from empty list" when two items are scored concurrently through one
    # instance, and a benchmark run at item_workers=2 lost 23 of 24 molecules
    # to it -- reported as coverage 0.042 rather than as a crash, so the
    # leaderboard still produced a confident-looking AUPRC from a single
    # surviving prediction. The engine serializes these per backend; HTTP
    # backends stay parallel.
    thread_safe: bool = True
    # True when this backend's output mapping has been checked against a real
    # response, not merely written from a schema. The distinction is not
    # cosmetic: three mappings in this registry were wrong in ways that
    # produced a plausible empty result rather than an error, and each was only
    # caught by seeing an actual payload. An unverified mapping is a claim, not
    # a fact, and callers deserve to know which they are getting.
    output_verified: bool = False
    output_unverified_reason: str = ""
    supports: Dict[str, Any] = field(default_factory=dict)
    # A multi-property backend (ADMET-AI splits 40-odd endpoints across nine
    # tools) maps each canonical property id onto the tool and field that
    # answer it. ``for_property`` collapses that into an ordinary
    # single-purpose spec before anything else in the pipeline sees it, so the
    # executor never has to know the difference.
    property_map: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    notes: str = ""
    cost: str = "unknown"

    @classmethod
    def from_config(cls, cfg: Dict[str, Any]) -> "BackendSpec":
        cfg = dict(cfg)
        for required in ("id", "task", "tool"):
            if not cfg.get(required):
                raise UnifiedModelConfigError(
                    f"Backend entry missing required key {required!r}: {cfg!r}"
                )
        cfg["transform"] = ScoreTransform.from_config(cfg.get("transform"))
        known = {f.name for f in cls.__dataclass_fields__.values()}
        unknown = set(cfg) - known
        if unknown:
            raise UnifiedModelConfigError(
                f"Backend {cfg['id']!r} has unknown keys: {sorted(unknown)}"
            )
        return cls(**cfg)

    # ------------------------------------------------------------------ #
    @property
    def display_name(self) -> str:
        return self.model.get("name") or self.id

    @property
    def citation_text(self) -> Optional[str]:
        """The model's own citation, carried onto every prediction it makes.

        A comparison table that names nine models without saying what they are
        invites the reader to treat them as nine independent opinions. Several
        are not: REVEL is an ensemble over thirteen predictors including SIFT
        and PolyPhen-2, both of which also appear here in their own right.
        """
        return self.model.get("citation")

    @property
    def uses_cached_payload(self) -> bool:
        """True when the resolver already fetched this backend's answer."""
        return bool(self.from_context)

    @property
    def higher_is_positive(self) -> Optional[bool]:
        """Direction of the *native* score, or None if it has no ranking sense.

        Rank-based benchmark metrics (AUROC, Spearman) run on the native score
        and use this flag, never on ``normalized_score``. That separation is
        deliberate: the normalization for several backends is a documented
        heuristic, and a leaderboard whose ordering could be changed by
        re-tuning a logistic midpoint would not be measuring the models.
        """
        if self.transform.kind in ("none", "categorical"):
            return None
        return not self.transform.invert

    @property
    def properties(self) -> List[str]:
        """Canonical property ids this backend can answer (multi-property only)."""
        return sorted(self.property_map)

    def for_property(self, prop: str) -> Optional["BackendSpec"]:
        """Specialize a multi-property backend to one property.

        Returns ``None`` when this backend does not cover ``prop`` -- which the
        caller reports as "not supported by this model" rather than as a
        failure, since no model covers every ADMET endpoint.
        """
        if not self.property_map:
            return self
        entry = self.property_map.get(str(prop).lower().strip())
        if entry is None:
            return None

        import dataclasses

        overrides: Dict[str, Any] = {"property_map": {}}
        if entry.get("tool"):
            overrides["tool"] = entry["tool"]
        if entry.get("from_context"):
            overrides["from_context"] = entry["from_context"]
        if entry.get("input_map"):
            overrides["input_map"] = entry["input_map"]
        if entry.get("path"):
            overrides["output_map"] = {**self.output_map, "score": entry["path"]}
        elif entry.get("output_map"):
            overrides["output_map"] = entry["output_map"]
        if entry.get("transform") is not None:
            overrides["transform"] = ScoreTransform.from_config(entry["transform"])
        if entry.get("call") is not None:
            overrides["call"] = entry["call"]
        if entry.get("score_type"):
            overrides["score_type"] = entry["score_type"]
        if entry.get("units") is not None:
            overrides["score_units"] = entry["units"]
        if entry.get("normalizer"):
            overrides["normalizer"] = entry["normalizer"]
        if entry.get("calibration"):
            overrides["calibration"] = entry["calibration"]
        return dataclasses.replace(self, **overrides)

    def missing_requirements(self, resolved: Dict[str, Any]) -> List[str]:
        """Which canonical representations this backend needs but did not get.

        A backend keyed on genomic coordinates cannot score a variant supplied
        only as a protein change until the resolver has filled those in. Saying
        so by name is what lets the compare layer report "skipped: needs
        genomic coordinates" instead of passing ``None`` down to an API and
        surfacing whatever error it happens to raise.
        """
        return [rep for rep in self.needs if not _lookup(resolved, rep)]

    def requires_key(self) -> bool:
        return bool(self.api_key)

    def key_available(self) -> bool:
        if not self.api_key:
            return True
        return bool(os.environ.get(self.api_key))

    def build_arguments(self, resolved: Dict[str, Any]) -> Dict[str, Any]:
        """Canonical input -> this backend's tool arguments.

        Keys whose template could not be filled are dropped rather than sent as
        ``None``: an optional argument left out is a default, while an explicit
        ``None`` is a validation error at most tools.
        """
        args: Dict[str, Any] = {}
        for key, template in self.input_map.items():
            value = render(template, resolved)
            if value is not None:
                args[key] = value
        return args

    def normalize(self, payload: Any) -> Dict[str, Any]:
        """Backend reply -> canonical prediction fields.

        Returns a dict with at least ``score``, ``normalized_score`` and
        ``call``; task-specific extras (pLDDT, units, classification) come from
        ``output_map`` and land beside them.
        """
        if self.normalizer:
            # importlib, not ``from . import ...``: the package defines a
            # module-level ``__getattr__`` for lazy tool loading, and a
            # submodule import that has not happened yet routes through it,
            # which logs a spurious "tool not found in lazy registry" warning
            # on every single normalized prediction.
            import importlib

            module = importlib.import_module(".unified_model_normalizers", __package__)
            fn = getattr(module, self.normalizer, None)
            if fn is None:
                raise UnifiedModelConfigError(
                    f"Backend {self.id!r} names unknown normalizer {self.normalizer!r}"
                )
            fields = fn(payload, self)
        else:
            fields = {
                name: extract(payload, spec) for name, spec in self.output_map.items()
            }

        score = fields.get(self.score_field)
        fields["score"] = score
        fields["score_type"] = self.score_type
        if self.score_units:
            fields["score_units"] = self.score_units
        fields["normalized_score"] = self.transform.to_unit(score)
        call, label = self._make_call(fields, score)
        fields["call"] = call
        if label is not None and label != call:
            # The domain word ("penetrant", "mutagenic") is what a reader
            # wants; the uniform word is what metrics need. Keep both rather
            # than making one audience lose the other.
            fields["call_label"] = label
        return fields

    def _make_call(self, fields: Dict[str, Any], score: Any) -> tuple:
        """The categorical verdict as ``(uniform_call, domain_label)``.

        ``call`` must use one vocabulary across every backend of a task,
        because that is what ``TaskSpec.positive_class`` is matched against
        when a benchmark builds its confusion matrix. ADMET-AI's natural words
        differ per endpoint -- "penetrant" for BBB, "mutagenic" for Ames,
        "inhibitor" for CYP -- and under a per-endpoint vocabulary the matrix
        found zero predicted positives and reported accuracy, MCC and F1 as
        though the model had never once predicted the positive class. Silently
        wrong numbers on the TDC leaderboard, which is that task's whole point.

        A backend may therefore declare ``above_label``/``below_label`` to keep
        its domain word; it is returned separately and surfaces as
        ``call_label`` while ``call`` stays uniform.
        """
        cfg = self.call
        if not cfg:
            return None, None
        source = cfg.get("from", "raw")

        if source == "field":
            raw_label = fields.get(cfg.get("field", "classification"))
            if raw_label is None:
                return None, None
            mapping = cfg.get("map") or {}
            key = str(raw_label).strip().lower()
            for label, mapped in mapping.items():
                if str(label).strip().lower() == key:
                    return mapped, str(raw_label)
            return cfg.get("default", str(raw_label)), str(raw_label)

        value = score if source == "raw" else fields.get("normalized_score")
        if value is None:
            return None, None
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None, None
        threshold = cfg.get("threshold")
        if threshold is None:
            return None, None
        if value >= float(threshold):
            return cfg.get("above", "positive"), cfg.get("above_label")
        return cfg.get("below", "negative"), cfg.get("below_label")


@dataclass
class TaskSpec:
    """A prediction problem with one canonical input and output shape."""

    id: str
    title: str = ""
    description: str = ""
    prediction_type: str = "score"  # score | regression | structure | affinity
    positive_class: Optional[str] = None
    resolver: Optional[str] = None
    input_schema: Dict[str, Any] = field(default_factory=dict)
    output_fields: Dict[str, str] = field(default_factory=dict)
    default_metrics: List[str] = field(default_factory=list)
    primary_metric: Optional[str] = None
    datasets: List[str] = field(default_factory=list)

    @classmethod
    def from_config(cls, task_id: str, cfg: Dict[str, Any]) -> "TaskSpec":
        cfg = dict(cfg)
        cfg["id"] = task_id
        known = {f.name for f in cls.__dataclass_fields__.values()}
        unknown = set(cfg) - known
        if unknown:
            raise UnifiedModelConfigError(
                f"Task {task_id!r} has unknown keys: {sorted(unknown)}"
            )
        return cls(**cfg)


@dataclass
class ModelRegistry:
    tasks: Dict[str, TaskSpec]
    backends: Dict[str, List[BackendSpec]]

    def task(self, task_id: str) -> TaskSpec:
        spec = self.tasks.get(task_id)
        if spec is None:
            raise KeyError(
                f"Unknown task {task_id!r}. Known tasks: {sorted(self.tasks)}"
            )
        return spec

    def backends_for(self, task_id: str) -> List[BackendSpec]:
        self.task(task_id)  # raises on an unknown task
        return list(self.backends.get(task_id, []))

    def backend(self, task_id: str, backend_id: str) -> BackendSpec:
        for spec in self.backends_for(task_id):
            if spec.id == backend_id:
                return spec
        known = [s.id for s in self.backends_for(task_id)]
        raise KeyError(
            f"Unknown backend {backend_id!r} for task {task_id!r}. Available: {known}"
        )

    def resolve_backends(
        self, task_id: str, requested: Optional[List[str]] = None
    ) -> List[BackendSpec]:
        """Pick backends by id, or every backend for the task when unspecified."""
        if not requested:
            return self.backends_for(task_id)
        if isinstance(requested, str):
            requested = [requested]
        if len(requested) == 1 and str(requested[0]).lower() == "all":
            return self.backends_for(task_id)
        return [self.backend(task_id, b) for b in requested]


def load_registry(force: bool = False) -> ModelRegistry:
    """Parse and cache ``data/unified_model_backends.json``."""
    global _registry_cache
    with _registry_lock:
        if _registry_cache is not None and not force:
            return _registry_cache
        with open(_REGISTRY_FILE, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        tasks = {
            task_id: TaskSpec.from_config(task_id, cfg)
            for task_id, cfg in (raw.get("tasks") or {}).items()
        }
        backends: Dict[str, List[BackendSpec]] = {}
        seen = set()
        for entry in raw.get("backends") or []:
            spec = BackendSpec.from_config(entry)
            if spec.task not in tasks:
                raise UnifiedModelConfigError(
                    f"Backend {spec.id!r} names unknown task {spec.task!r}"
                )
            key = (spec.task, spec.id)
            if key in seen:
                raise UnifiedModelConfigError(
                    f"Duplicate backend id {spec.id!r} for task {spec.task!r}"
                )
            seen.add(key)
            backends.setdefault(spec.task, []).append(spec)

        _registry_cache = ModelRegistry(tasks=tasks, backends=backends)
        return _registry_cache
