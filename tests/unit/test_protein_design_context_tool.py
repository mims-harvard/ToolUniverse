"""Analytic ablation controls, incomplete matrices and real SDK dispatch."""

import copy
import hashlib
import json
import math
import re
from pathlib import Path

import jsonschema
import pytest

from tooluniverse import ToolUniverse
from tooluniverse.protein_design_context_tool import ProteinDesignContextTool

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads(
    (ROOT / "src/tooluniverse/data/protein_design_context_tools.json").read_text()
)[0]


def request():
    return copy.deepcopy(CONFIG["test_examples"][0])


def calculate(args=None):
    result = ProteinDesignContextTool(CONFIG).run(request() if args is None else args)
    jsonschema.validate(result, CONFIG["return_schema"])
    return result


def vector(parent_probability, mutant_probability, alphabet="ACDEFGHIKLMNPQRSTVWY"):
    """Build a normalized analytic categorical distribution, not model data."""
    other = (1 - parent_probability - mutant_probability) / (len(alphabet) - 2)
    return [
        math.log(
            parent_probability
            if a == "A"
            else mutant_probability
            if a == "V"
            else other
        )
        for a in alphabet
    ]


def digest(label):
    return hashlib.sha256(label.encode()).hexdigest()


def add_pose(args, family, value, label):
    """Add a distinct analytic coordinate hypothesis for every checkpoint."""
    pose = {"source_family": family, "pose_sha256": digest(label)}
    args["expected_poses"].append(pose)
    for checkpoint in args["expected_checkpoints"]:
        context = copy.deepcopy(args["contexts"][0])
        context.update(pose, checkpoint_sha256=checkpoint)
        context["full_complex"]["log_probabilities"] = [
            vector(0.05, 0.05 * math.exp(value))
        ]
        args["contexts"].append(context)


def test_analytic_context_effect_and_scope():
    """The exact odds ratio is two; no physical affinity claim follows."""
    data = calculate()["data"]
    row = data["rows"][0]
    assert row["receptor_context_effect_nats"] == pytest.approx(math.log(2))
    assert row["unpaired_sample_range_nats"] == pytest.approx([math.log(2)] * 2)
    assert data["family_checkpoint_summary"][0]["all_pose_sample_ranges_positive"]
    assert data["coverage"]["declared_matrix_complete"]
    assert not data["coordinate_identity_verified"] and not data["binding_verified"]
    assert "not binding free energy" in " ".join(data["limitations"])


def test_generic_sequence_prior_cancels():
    """A bound improvement also present without receptor has zero context effect."""
    args = request()
    args["contexts"][0]["receptor_deleted"]["log_probabilities"] = [vector(0.05, 0.1)]
    row = calculate(args)["data"]["rows"][0]
    assert row["full_mean_delta_nats"] > 0
    assert row["deleted_mean_delta_nats"] > 0
    assert row["receptor_context_effect_nats"] == 0


def test_unpaired_samples_do_not_cancel_by_array_index():
    """Equal decoding order indices do not justify paired noise subtraction."""
    args = request()
    full, deleted = (
        args["contexts"][0]["full_complex"],
        args["contexts"][0]["receptor_deleted"],
    )
    full["log_probabilities"] = [vector(0.05, 0.1), vector(0.05, 0.2)]
    deleted["log_probabilities"] = [vector(0.05, 0.05), vector(0.05, 0.1)]
    row = calculate(args)["data"]["rows"][0]
    assert row["receptor_context_effect_nats"] == pytest.approx(math.log(2))
    assert row["unpaired_sample_range_nats"] == pytest.approx([0, math.log(4)])
    deleted["log_probabilities"].reverse()
    reversed_row = calculate(args)["data"]["rows"][0]
    assert (
        reversed_row["unpaired_sample_range_nats"] == row["unpaired_sample_range_nats"]
    )
    deleted["log_probabilities"].append(vector(0.05, 0.05))
    assert calculate(args)["status"] == "success"


def test_family_balance_and_checkpoints_are_not_replications():
    """All samples remain visible without pooling families by sample count."""
    args = request()
    first_family = args["expected_poses"][0]["source_family"]
    add_pose(args, first_family, -math.log(2), "opposing same-family pose")
    add_pose(args, "second-source-family", math.log(4), "second family pose")
    extra = digest("related scorer weights")
    args["expected_checkpoints"].append(extra)
    for context in list(args["contexts"]):
        args["contexts"].append({**copy.deepcopy(context), "checkpoint_sha256": extra})
    data = calculate(args)["data"]
    assert len(data["rows"]) == 6
    assert data["coverage"]["source_family_count"] == 2
    assert data["coverage"]["checkpoint_count"] == 2
    assert data["coverage"]["scorer_family_count"] == 1
    first = next(
        s
        for s in data["family_checkpoint_summary"]
        if s["source_family"] == first_family
    )
    assert first["pose_count"] == 2
    assert first["equal_pose_mean_context_effect_nats"] == pytest.approx(0, abs=1e-14)
    assert not first["all_pose_sample_ranges_positive"]
    assert not first["all_pose_sample_ranges_negative"]


@pytest.mark.parametrize(
    "field",
    [
        "ligand_backbone_sha256",
        "ligand_sequence_sha256",
        "protocol_sha256",
        "design_positions",
    ],
)
def test_mismatched_pair_rejected(field):
    """Independent free folds cannot masquerade as matched deletion controls."""
    args = request()
    args["contexts"][0]["receptor_deleted"][field] = (
        [1, 2] if field == "design_positions" else digest("different")
    )
    assert "identical" in calculate(args)["error"]


@pytest.mark.parametrize(
    "failure", ["missing", "extra", "duplicate", "alias", "checkpoint", "unknown"]
)
def test_incomplete_or_ambiguous_matrix_rejected(failure):
    """Do not silently drop failures, poses, weights, or coordinate aliases."""
    args = request()
    if failure == "missing":
        args["contexts"] = []
    elif failure == "extra":
        args["contexts"] *= 2
    elif failure == "alias":
        args["expected_poses"] *= 2
    elif failure == "checkpoint":
        args["expected_checkpoints"] *= 2
    elif failure == "unknown":
        args["contexts"][0]["pose_sha256"] = digest("undeclared")
    else:
        add_pose(args, "second", 0, "another pose")
        args["contexts"][1] = copy.deepcopy(args["contexts"][0])
    assert calculate(args)["status"] == "error"


@pytest.mark.parametrize(
    "bad",
    [
        [0.0] * 20,
        [math.log(0.05)] * 19,
        [float("nan")] * 20,
        [float("inf")] * 20,
        [True] * 20,
        [-1000.0] * 20,
        [1.0] * 20,
        None,
    ],
)
def test_invalid_probabilities_rejected(bad):
    """Masked zeros, logits, incomplete alphabets and nonfinite values fail."""
    args = request()
    args["contexts"][0]["full_complex"]["log_probabilities"] = [bad]
    assert calculate(args)["status"] == "error"


@pytest.mark.parametrize(
    "field,bad",
    [
        ("position", True),
        ("position", 0),
        ("parent_residue", "X"),
        ("mutant_residue", "A"),
        ("alphabet", "A" * 20),
        ("scoring_mode", "backbone_only"),
        ("scorer_family", " "),
    ],
)
def test_invalid_contract_rejected(field, bad):
    """Reject ambiguous sequence indexing and incompatible scoring modes."""
    args = request()
    args[field] = bad
    assert calculate(args)["status"] == "error"


def test_x_is_normalized_but_cannot_be_a_mutation():
    """Full native alphabets can include X without treating it as a design."""
    args = request()
    args["alphabet"] += "X"
    for label, p in (("full_complex", 0.1), ("receptor_deleted", 0.05)):
        args["contexts"][0][label]["log_probabilities"] = [
            vector(0.05, p, args["alphabet"])
        ]
    assert calculate(args)["data"]["rows"][0][
        "receptor_context_effect_nats"
    ] == pytest.approx(math.log(2))


def test_real_sdk_dispatch_and_wrapper():
    """Exercise registration, runtime input validation and generated wrapper."""
    tu = ToolUniverse()
    tu.load_tools(include_tools=[CONFIG["name"]])
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": request()}, use_cache=False
    )
    jsonschema.validate(result, CONFIG["return_schema"])
    assert result["data"]["rows"][0]["receptor_context_effect_nats"] == pytest.approx(
        math.log(2)
    )
    from tooluniverse.tools import Protein_compare_receptor_context

    assert Protein_compare_receptor_context(**request())["status"] == "success"


def test_sdk_validation_error_matches_declared_schema():
    """Framework validation errors may add diagnostic fields to the envelope."""
    tu = ToolUniverse()
    tu.load_tools(include_tools=[CONFIG["name"]])
    args = request()
    args["position"] = False
    result = tu.run_one_function(
        {"name": CONFIG["name"], "arguments": args}, use_cache=False
    )
    assert result["status"] == "error"
    jsonschema.validate(result, CONFIG["return_schema"])


def test_alphabet_permutation_and_unequal_sample_counts():
    """Alphabet order is explicit and sample lengths need not match."""
    args = request()
    args["alphabet"] = args["alphabet"][::-1]
    for label in ("full_complex", "receptor_deleted"):
        args["contexts"][0][label]["log_probabilities"][0].reverse()
    args["contexts"][0]["full_complex"]["log_probabilities"] *= 3
    row = calculate(args)["data"]["rows"][0]
    assert row["receptor_context_effect_nats"] == pytest.approx(math.log(2))


def test_mask_mismatch_between_source_poses_rejected():
    """A different design mask changes the conditional comparison protocol."""
    args = request()
    add_pose(args, "second-source", 0, "another geometry")
    for label in ("full_complex", "receptor_deleted"):
        args["contexts"][1][label]["design_positions"] = [1, 2]
    assert "all contexts" in calculate(args)["error"]


def test_reference_snippets_execute_verbatim():
    """The documented analytic control must run through the registered route."""
    reference = (
        ROOT
        / "skills/tooluniverse-protein-design-campaign/references/model-disagreement.md"
    )
    blocks = re.findall(r"```python\n(.*?)\n```", reference.read_text(), re.S)
    assert blocks
    for block in blocks:
        namespace = {}
        exec(block, namespace)
        result = namespace["result"]
        assert result["status"] == "success"
        assert result["data"]["rows"][0][
            "receptor_context_effect_nats"
        ] == pytest.approx(math.log(2))
