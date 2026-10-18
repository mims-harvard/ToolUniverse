"""One held worker, the whole acceptance suite: ladder, mixed shapes, repeats.

This is the implementation of the acceptance test STANDARD.md section 6 and
section 14 describe. It exists as one script rather than three runs because
each separate run paid the model build again, and because the ORDER matters:

    verify_provider.py <slug> [--lengths 100,200,400,800] [--repeats 4]

1. The LADDER first and ASCENDING, in a worker nothing larger has touched.
   `peak_reserved_gib` is a running high-water mark in most of these workers,
   so a large request earlier in the session pins every later rung to its
   value. Taking esmc's ladder after a mixed phase made its 100-residue rung
   read 24.44 GiB where a clean ascending session reads 24.08.
2. Then MIXED shapes, which catch what only a rebuild exposes: genie3's
   upstream config is a module-level mutable permitting one model build per
   process, so its second DIFFERENT request raised while four identical ones
   could never have found it.
3. Then four consecutive IDENTICAL requests, which catch what only recurrence
   exposes: openfold3 passed a one-request smoke and died on request two,
   because a CUDA graph pool handle was kept after a dropped graph.

**Both halves are mandatory and they are not the same test.** openfold3_ob0
carried one defect of each kind, in two different layers. And note af2ig:
"vary the input" is not the instruction, "vary the ENGINE KEY" is -- if a
provider's key is not its input size, a length ladder rebuilds nothing and the
rebuild has to be exercised on whatever axis does change it.

The length rungs need a per-provider way to resize the smoke input, which is
what SHAPERS below is for. A provider with no shaper gets repeats only, and
**exits 2 saying so** rather than printing 4/4 and letting a reader take it for
a pass.

Run it from the repository root.
"""

import argparse
import json
import os
import shutil
import sys
import time
from pathlib import Path

# Importable without installing: the model environments are separate, but this
# driver runs in the repository's own interpreter.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from tooluniverse.remote_resident import backend, manifest as M  # noqa: E402

PROT = (
    "KKAVINGEQIRSISDLHQTLKKELALPEYYGENLDALWDALTGWVEYPLVLEWRQFEQSKQ"
    "LTENGAESVLQVFREAKAEGADITIILS"
)
DNA = "ACGTACGTAGCTAGCTAGGCTATCGATCGGATCGATCGTAGCTAGCTAGCTAGCATCGATC"


def _tile(base, n):
    return (base * (n // len(base) + 1))[:n]


def _json_seq(text, n, path, base=PROT):
    """Resize the first protein sequence found in a JSON document."""
    doc = json.loads(text)
    seq = _tile(base, n)
    cur = doc
    for key in path[:-1]:
        cur = cur[key]
    cur[path[-1]] = seq
    return json.dumps(doc)


def _e1_fasta(_text, n):
    """A parent of length n plus three single substitutions, ids matching.

    e1 validates that every mutant id spells its own 1-based substitution and
    that every record is the parent's length, so a resized input has to be
    generated rather than tiled.
    """
    parent = _tile(PROT, n)
    out = [">parent_%daa" % n, parent]
    for pos in (6, n // 2, n - 3):
        if pos < 1 or pos > n:
            continue
        orig = parent[pos - 1]
        new = "A" if orig != "A" else "G"
        out += [f">{orig}{pos}{new}", parent[: pos - 1] + new + parent[pos:]]
    return "\n".join(out) + "\n"


def _af3_json(text, n):
    """Resize af3_torch's sequence AND its inline single-sequence MSA together.

    The MSA is `>query\n<sequence>\n`, so leaving it at the old length would
    feed the model an alignment that does not match its own query.
    """
    doc = json.loads(text)
    seq = _tile(PROT, n)
    prot = doc["sequences"][0]["protein"]
    prot["sequence"] = seq
    prot["unpairedMsa"] = ">query" + chr(10) + seq + chr(10)
    return json.dumps(doc)


def _fasta_one(_text, n):
    """A single FASTA record of length n (atlasfold, rosettafold3-style inputs)."""
    return ">n%d" % n + chr(10) + _tile(PROT, n) + chr(10)


def _progen2_ctx(_text, n):
    """A ProGen2 context of n residues with its N-terminal marker.

    The worker refuses a one-sided terminal, so the markers at BOTH ends are part of the
    grammar rather than decoration.
    """
    return "1" + _tile(PROT, n) + "2" + chr(10)


def _esm_if1_backbone(text, n):
    """Resize esm_if1's input backbone to n residues.

    Inverse folding takes a STRUCTURE, so there is nothing to tile the way a
    sequence provider's shaper tiles residues, and the input cannot be resized
    by editing one string. It can still be resized meaningfully, which matters
    because what varies the work here is the encoder's length and the number of
    sequential decoder steps -- both a pure function of the residue count.

    The smoke carries the first 64 residues of chain C of 5YH2 as inline PDB.
    This rebuilds that PDB with exactly n residues: a truncation when n is
    smaller than what the record holds, and otherwise whole copies of the
    backbone translated 200 A apart along +x, renumbered consecutively, until n
    residues exist. The copies are far enough apart that the GVP encoder's kNN
    graph stays inside one of them, so every rung is a real backbone of real
    local geometry rather than a synthetic helix -- and the rungs above the
    record's length are explicitly a MEASUREMENT of cost, not a biological
    input.
    """
    doc = json.loads(text)
    chain = doc.get("chain") or "C"
    res, order = {}, []
    for line in doc["structure"].splitlines():
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        key = line[21:27]
        if key not in res:
            res[key] = []
            order.append(key)
        res[key].append(line)
    if not order:
        raise ValueError("esm_if1 shaper: the smoke input carries no ATOM records")

    out, serial, resseq = [], 0, 0
    while resseq < n:
        shift = 200.0 * (resseq // len(order))
        for key in order:
            if resseq >= n:
                break
            resseq += 1
            for line in res[key]:
                serial += 1
                x = float(line[30:38]) + shift
                out.append(
                    "%s%5d%s%s%4d %s%8.3f%s"
                    % (
                        line[:6],
                        serial,
                        line[11:21],
                        chain,
                        resseq,
                        line[27:30],
                        x,
                        # to the END of the line, not to column 54: biotite
                        # parses occupancy and B-factor and raises ValueError on
                        # a record that stops after the coordinates.
                        line[38:],
                    )
                )
    doc["structure"] = "\n".join(out) + "\nEND\n"
    doc["chain"] = chain
    return json.dumps(doc)


def _colabfold_a3m(_text, n):
    """A two-chain ColabFold complex a3m of n residues, MSA-free.

    THE HEADER, THE CONCATENATED QUERY AND EVERY ALIGNMENT ROW ARE WRITTEN FROM
    ONE LIST OF CHAINS, so they cannot disagree. af3_jax's shaper had to resize a
    sequence and its inline single-sequence MSA together; this dialect is the
    same hazard three times over -- the `#<lens>\t<cards>` header, the
    concatenated query on line 3 and each per-chain row's dash padding all encode
    the same lengths, and `unserialize_msa` splits every later row by ALIGNED
    COLUMN COUNT using the header's lengths. A header left at the old lengths
    does not fail; it silently slices the rows at the wrong offsets and hands the
    model an alignment of a different query.

    Two chains rather than one, deliberately: the provider forces the
    AlphaFold2-Multimer parameters (the only set it has digests for), and the
    smoke is a two-chain complex, so every rung keeps `is_complex` true and the
    paired/unpaired split exercised. The rung's length is the TOTAL, split in
    half, which is what the provider's budget envelope is quoted in.
    """
    a = _tile(PROT, (n + 1) // 2)
    b = _tile(PROT[7:] + PROT[:7], n - len(a))
    chains = [c for c in (a, b) if c]
    total = sum(len(c) for c in chains)
    labels = [str(101 + i) for i in range(len(chains))]
    lines = [
        "#"
        + ",".join(str(len(c)) for c in chains)
        + chr(9)
        + ",".join("1" for _ in chains),
        ">" + chr(9).join(labels),
        "".join(chains),
    ]
    start = 0
    for label, c in zip(labels, chains):
        lines.append(">" + label)
        lines.append("-" * start + c + "-" * (total - start - len(c)))
        start += len(c)
    return chr(10).join(lines) + chr(10)


def _af2ig_complex(text, n):
    """A two-chain binder-target complex of exactly n residues, as PDB text.

    af2ig takes a STRUCTURE, so there is no sequence to tile -- this is
    esm_if1's problem again, with one extra constraint that decides the whole
    function: dl_binder_design reads CHAIN 1 AS THE BINDER and everything after
    it as the target, and the scores this provider exists to produce
    (pae_interaction, plddt_binder, the two RMSDs) are slices at `binderlen`.
    A rung that collapsed to one chain would be a MONOMER prediction, which
    returns nulls for every interface score and exercises a different branch of
    `generate_scoredict`. So every rung keeps two chains and keeps the smoke's
    own binder:target ratio -- 87:108 in 1BRS barstar-barnase -- which means
    `binderlen` moves with the rung instead of staying at one tested value.

    THE RESIDUES ARE THE SMOKE'S OWN, not a synthetic helix. Rungs at or below
    the record's length are a truncation of it; longer rungs lay whole copies
    of each chain down 70 A apart along +x, which is the kit's OWN recipe for
    making larger inputs out of 1BRS ("tiled k:k, copies displaced 70 A along
    x, no contacts between copies" -- its PUBLIC_INPUTS_README). The copies are
    far enough apart to make no new contacts, and the amide-distance test
    upstream runs (`check_residue_distances`, 3.0 A) sees each join as a chain
    break and gives it AlphaFold's +200 residue-index offset, exactly as it
    does for the kit's own tilings. So a rung above 195 residues is a real
    measurement of what that length costs, and is explicitly not a biological
    complex.

    Columns are rewritten rather than reflowed: serial, chain id, residue
    number and x move, and everything from column 39 onward (occupancy, B
    factor, element) is carried through untouched, because upstream's parser
    reads fixed columns.
    """
    chains, order = {}, []
    for line in text.splitlines():
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        ch = line[21]
        if ch not in chains:
            chains[ch] = ([], {})
            order.append(ch)
        res_order, res = chains[ch]
        key = line[22:27]
        if key not in res:
            res[key] = []
            res_order.append(key)
        res[key].append(line)
    if len(order) < 2:
        raise ValueError("af2ig shaper: the smoke input is not a two-chain complex")

    src_binder, src_target = order[0], order[1]
    nat_b = len(chains[src_binder][0])
    nat_t = len(chains[src_target][0])
    want_b = max(1, min(n - 1, round(n * nat_b / float(nat_b + nat_t))))
    want_t = n - want_b

    out, serial = [], 0
    for out_chain, src_chain, want in (
        ("A", src_binder, want_b),
        ("B", src_target, want_t),
    ):
        res_order, res = chains[src_chain]
        resseq = 0
        while resseq < want:
            shift = 70.0 * (resseq // len(res_order))
            for key in res_order:
                if resseq >= want:
                    break
                resseq += 1
                for line in res[key]:
                    serial += 1
                    x = float(line[30:38]) + shift
                    out.append(
                        "%s%5d%s%s%4d %s%8.3f%s"
                        % (
                            line[:6],
                            serial,
                            line[11:21],
                            out_chain,
                            resseq,
                            line[27:30],
                            x,
                            line[38:],
                        )
                    )
        out.append("TER")
    return chr(10).join(out) + chr(10) + "END" + chr(10)


def _colabdesign_case(text, n):
    """A binder-design case of exactly n TOTAL TOKENS: target residues + binder length.

    colabdesign takes a STRUCTURE and a binder length, so nothing can be tiled the
    way a sequence provider's shaper tiles residues, and what the VRAM budget and
    the compile are a function of is the token count (prep.py: `_lengths =
    [target_len, binder_len]`), which is why the rung is quoted in tokens. The
    binder takes a third of the rung (capped at BindCraft's own 150) and the target
    the rest, so the ratio keeps both chains in play at every rung instead of a
    constant 30-residue binder against a growing target.

    The target is the smoke's own PD-L1 crop (chain A, residues 18-132, hotspot 56):
    a truncation of it below 115 residues (residue 56 stays inside, from rung 45
    up), and above 115 whole copies of the chain laid down 70 A apart along +x and
    renumbered consecutively -- the kit's own recipe for making larger inputs out of
    one structure. The copies make no contacts with each other, so a rung above
    115 target residues is a real measurement of what that token count costs and
    is explicitly not a biological target.

    The iteration counts stay the smoke's (soft 50 / temp 10 / hard 5 / greedy 5):
    the memory and the compile are functions of the shape, not of how many steps
    are taken at it, and 65 steps at 400 tokens is already the long rung.
    """
    doc = json.loads(text)
    binder = max(8, min(150, n // 3))
    want = n - binder
    chains, order = {}, []
    for line in doc["target_pdb"].splitlines():
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        key = line[22:27]
        if key not in chains:
            chains[key] = []
            order.append(key)
        chains[key].append(line)
    out, serial, resseq = [], 0, 0
    first = int(order[0][:4])
    while resseq < want:
        shift = 70.0 * (resseq // len(order))
        for key in order:
            if resseq >= want:
                break
            resseq += 1
            for line in chains[key]:
                serial += 1
                x = float(line[30:38]) + shift
                out.append(
                    "%s%5d%s%s%4d %s%8.3f%s"
                    % (
                        line[:6],
                        serial,
                        line[11:21],
                        "A",
                        first + resseq - 1,
                        line[27:30],
                        x,
                        line[38:],
                    )
                )
    doc["target_pdb"] = chr(10).join(out) + chr(10) + "END" + chr(10)
    doc["chain"] = "A"
    doc["binder_len"] = binder
    return json.dumps(doc)


def _complexa_design(text, n):
    """A binder-design request for a complex of n residues in total.

    Proteina-Complexa takes a TARGET STRUCTURE, so there is no sequence to tile
    -- this is esm_if1's and af2ig's problem again. What varies the cost is the
    pair tensor over (target crop + binder), so a rung of n keeps the smoke's
    own ratio, 115 target : 64 binder (PD-L1 crop A1-115, binder 64), and moves
    both: crop = round(n * 115 / 179), binder = n - crop.

    The target is the smoke's own PD-L1 residues. A crop at or below 115 is a
    truncation of it; a longer one lays down whole copies of the chain 100 A
    apart along +x, renumbered consecutively -- the same recipe af2ig's shaper
    uses -- so a rung above 115 target residues is a MEASUREMENT of what that
    length costs, and explicitly not a biological target. Columns are rewritten,
    not reflowed: serial, residue number and x move, and everything from column
    39 onward is carried through, because the reader takes fixed columns.

    The three hotspots (A37, A39, A49) sit inside every crop of 64 or more.
    The number of designs stays 1 and the steps stay at the smoke's: this is the
    length axis only. The ENGINE-KEY axes (num_steps, batch size, design count,
    seed, a different target) are NOT varied here, because this function is
    handed one number; they were exercised separately by a driver that changes
    each in turn and returns to request one (byte-identical) -- see the
    provider's verified_on.
    """
    doc = json.loads(text)
    res_order, res = [], {}
    for line in doc["target_pdb"].splitlines():
        if line.startswith("ENDMDL"):
            break
        if not line.startswith("ATOM") or len(line) < 54 or line[21] != "A":
            continue
        key = line[22:27]
        if key not in res:
            res[key] = []
            res_order.append(key)
        res[key].append(line)
    crop = max(64, min(300, round(n * 115 / 179)))
    binder = max(20, min(200, n - crop))
    out, serial, resseq = [], 0, 0
    while resseq < crop:
        shift = 100.0 * (resseq // len(res_order))
        for key in res_order:
            if resseq >= crop:
                break
            resseq += 1
            for line in res[key]:
                serial += 1
                out.append(
                    "%s%5d%s%4d %s%8.3f%s"
                    % (
                        line[:6],
                        serial,
                        line[11:22],
                        resseq,
                        line[27:30],
                        float(line[30:38]) + shift,
                        line[38:],
                    )
                )
    doc["target_pdb"] = chr(10).join(out) + chr(10) + "END" + chr(10)
    doc["target_input"] = "A1-%d" % crop
    doc["hotspot_residues"] = ["A37", "A39", "A49"]
    doc["binder_length"] = binder
    doc["num_designs"] = 1
    return json.dumps(doc)


def _gpnstar_vep(text, n):
    """A GPN-Star request of n variants whose BATCH SHAPE is n (capped at 64).

    The input is a JSON document of single-nucleotide variants scored against an
    alignment store, and a variant's `ref` has to equal the store's own base at that
    position or upstream refuses the request. So the variants cannot be tiled or
    invented the way a sequence provider's residues are: they are drawn from
    `gpnstar_realpos_128.json`, every position of the kit's sparse example store whose
    128-bp window lies inside a present chunk, with the ref read from the store by
    `gpnstar_realpos.py` (3,207 of them).

    WHAT THE RUNG VARIES, and why it is not simply the count: this provider's engine
    key is the kit's per-shape state -- the K/V route decision, the constants cached per
    shape -- and that is a function of the BATCH shape (batch_size x window), not of how
    many variants are in the request: 4,000 variants at batch 8 run one shape. So the
    rung sets batch_size = min(n, 64) as well, which makes the size axis the engine-key
    axis up to 64. Past 64 the batch shape stops changing and only the batch COUNT grows.
    The WINDOW axis, which also changes the shape, is exercised separately by
    gpnstar_window_axis.py.
    """
    import json as _json

    doc = _json.loads(text)
    # Shipped beside this script: see fixtures/README.md for why these cannot be
    # invented. A path from one machine's scratchpad lived here first, which is
    # the second time that has happened in this file.
    pool = _json.loads(
        (
            Path(__file__).resolve().parent
            / "fixtures"
            / "gpnstar_valid_positions_w128.json"
        ).read_text()
    )
    step = 7919  # coprime with 3207, so the n picks are distinct and spread over the chunks
    doc["variants"] = [pool[(i * step) % len(pool)] for i in range(n)]
    doc["window_size"] = 128
    doc["batch_size"] = max(1, min(n, 64))
    return _json.dumps(doc)


def _mosaic_design(text, n):
    """A binder-design request whose complex is n Boltz-2 TOKENS in total.

    mosaic's cost axis is the token count (target residues x copies + binder
    length) and each distinct count is its own XLA program, so the first request
    into a new count pays a compilation of minutes. n is TOTAL tokens: the rung
    keeps the smoke's binder length and tiles the smoke's barstar target out to
    n - binder residues (PROT here IS barstar). Rungs above 89 target residues
    are a measurement of cost, not a biological target. Steps, seed, copies and
    epitope stay the smoke's: this is the length axis only; the epitope and copy
    axes are exercised separately.
    """
    doc = json.loads(text)
    binder = int(doc.get("binder_length", 80))
    copies = int(doc.get("target_copies", 1))
    target = (n - binder) // copies
    if target < 1:
        raise ValueError("mosaic shaper: no target left after the binder")
    doc["target_sequence"] = _tile(PROT, target)
    return json.dumps(doc)


def _boltz_msa_mode(text):
    """The smoke's single-sequence line dropped, so the MSA server is used."""
    kept = [line for line in text.splitlines() if line.strip() != "msa: empty"]
    if len(kept) == len(text.splitlines()):
        raise ValueError(
            "boltz msa mode: the smoke no longer carries `msa: empty`, so this "
            "transform does not know what to drop -- re-derive it from the smoke"
        )
    return "\n".join(kept) + "\n"


def _apnovo_steps(text, n):
    """A campaign at n DENOISING STEPS -- apnovo's engine key is not its length.

    This is the af2ig case the module docstring names, in its sharpest form:
    a length ladder here would rebuild NOTHING and still print four green
    rungs. `run_generator.parse_and_prepare_diffusion_input` passes
    `max_num_res=512` as a LITERAL, so every design of every length is padded
    to the same 512 residues and compiled once -- which is also why this
    provider's measured peak does not move with the design length, and why
    `vram_budget_gb` could be quoted from one bucket at all.

    What does change the engine is `_get_compiled_trajectory(sampling_steps,
    num_partial_diffusion_steps)`, a module-level `functools.lru_cache` --
    the same SHAPE of hazard genie3 carried, where a module-level mutable
    permitted one build per process. So the rung is a step count, and the
    ladder is a real sequence of distinct XLA compilations.

    `Manifest` merges as `{**defaults, **entry}`, so the ENTRY wins over
    `defaults`: setting only the defaults block would leave any design that
    names its own step count untouched, and the ladder would silently run four
    rungs at one value. Both are written.

    Note the cache is `maxsize=8`. Four ladder rungs plus the smoke's own 50
    is five keys, so no rung is evicted by a later one during a run.
    """
    doc = json.loads(text)
    doc.setdefault("manifest", {}).setdefault("defaults", {})[
        "num_sampling_steps"
    ] = n
    for design in doc["manifest"].get("designs") or []:
        if "num_sampling_steps" in design:
            design["num_sampling_steps"] = n
    return json.dumps(doc)


def _ef2inv_case(text, n):
    """A warm-pass case of exactly n TOTAL TOKENS -- ef2inv's engine key.

    `n_tokens = len(target_seq) + st.binder_len` (worker:648), and that number
    is the key of the kit's composition memo: `fastkit.enable` returns every
    shape-bound CUDA-graph pool and memoised hidden state and RE-PLANS the
    backward checkpoint policy when it changes, while the same value
    re-installs nothing and says so in one line. So unlike apnovo, here the
    size IS the key -- but it is the token count of the COMPLEX, which is why
    the rung is quoted in tokens rather than residues.

    TWO DISCONTINUITIES MAKE THIS LADDER WORTH MORE THAN A CURVE. The trunk
    fwd+bwd graph pool is installed only at n_tokens <= 256
    (`POOL_MAX_TOKENS`), so a rung at 256 and one above it run structurally
    different compositions; and the checkpoint planner re-reads free memory
    and keeps as many pair blocks as fit, so its chosen policy is a per-rung
    fact. Suggested: `--lengths 135,195,256,300` -- the smoke's own size, the
    size the 28.03 GiB budget was quoted at, the last rung with the pool, and
    the tool layer's ceiling.

    THE TARGET HAS TO BE RENAMED, not just lengthened. `resolve_target`
    refuses a preset name carrying a `target_sequence` ("is a preset target;
    omit target_sequence") and refuses a non-preset name without one, so
    growing past the 115-residue pd-l1 preset means leaving the preset route
    entirely. The binder keeps input-design.json's own 80:195 share of the
    complex, so both chains grow instead of a fixed 20-residue binder against
    a swelling target.

    Kept at `pass: "warm"` deliberately. The design pass's length is a pinned
    module constant the kit refuses to see changed, so a design ladder would
    be four 150-step runs; the warm pass runs the same fold-under-grad and
    re-plans the same composition in seconds.

    NOTE THE BUDGET. `vram_budget_gb` is 28.03, quoted at 195 tokens under
    mode `fast`, whose planner deliberately grows to fill the card -- so rungs
    above that will record peaks well above the declared figure, and nothing
    refuses them. That is the declared behaviour of the mode, not a fault, but
    it means these rungs do not establish an envelope the way other providers'
    do.
    """
    doc = json.loads(text)
    # input-design.json's own shape: an 80-residue binder in a 195-token
    # complex. Clamped to the tool layer's 8..200 binder range so a rung stays
    # something a caller could also have asked for.
    binder = max(8, min(200, round(n * 80 / 195)))
    target_len = n - binder
    if target_len < 1:
        raise ValueError(f"ef2inv shaper: rung {n} is too small to hold a binder")
    doc["target_name"] = "ladder"  # NOT a preset name, or target_sequence is refused
    # No "|": the worker counts len(target_seq) raw while the kit's own
    # complex_tokens strips chain breaks, and the two must agree.
    doc["target_sequence"] = _tile(PROT, target_len)
    doc["binder_len"] = binder
    doc["pass"] = "warm"
    return json.dumps(doc)


def _proteinmpnn_backbone(text, n):
    """Resize proteinmpnn's inline backbone to exactly n residues.

    NOTHING HERE REBUILDS, AND THAT IS THE FINDING. The only cache in this
    worker is `_model(variant)`, keyed on the weight set and nothing else;
    there is no torch.compile, no CUDA graph and no shape-keyed dict anywhere
    in the file, and upstream is dynamic-shape eager (`torch.topk(...,
    min(self.top_k, X.shape[1]))` adapts k to L at runtime). So this ladder is
    NOT a rebuild test and must not be read as one -- it is a cost-versus-size
    table plus a robustness sweep, and the honest reason to run it is that
    residue count drives the one genuinely sequential part of the model, the
    autoregressive decode, which is L steps long. The mixed phase still earns
    its place: it shows a second DIFFERENT input neither corrupts the held
    model nor breaks the seed replay.

    The harness will print `peak=None` for every rung. That is correct rather
    than broken -- this provider runs on the CPU under `policy = "none"` and
    reports `rss_gib`, because there is no device memory to report.

    THE RESIZE IS esm_if1's RECIPE WITH A DIFFERENT PARSER'S RULES. Rungs at
    or below the record's length truncate it; longer rungs lay whole copies
    down 200 A apart along +x and renumber consecutively. What differs from
    esm_if1:

      - the kit's `fast_parse` rebuilds the sequence over
        `range(min_resn, max_resn + 1)` and emits ANY MISSING NUMBER AS A GAP
        -- sequence character "-" and NaN coordinates, and "-" is inside
        stock's alphabet so it is not dropped. A gap would silently inflate
        the residue count and feed NaN into the featuriser. So the numbering
        has to be strictly consecutive, which is why resseq is rewritten
        rather than carried.
      - residue number is read from `line[22:27]`, FIVE columns, with a
        trailing letter taken as an insertion code. The %4d plus a space below
        keeps column 27 blank, so no rung is read as an icode.
      - columns past 54 are not parsed here (biotite's occupancy/B-factor
        requirement that shaped esm_if1's slicing does not apply), but they
        are carried anyway so the record stays a valid PDB.

    ONE PROPERTY esm_if1 HAS THAT THIS DOES NOT, said plainly: the smoke's
    record is 40 residues and k is `min(48, L)`, so above 48 residues at least
    eight of every residue's neighbours necessarily come from another copy at
    200 A. That is numerically harmless -- the RBF basis saturates, no NaN --
    but the kNN graph does NOT stay inside one copy, so rungs above 48
    residues are a measurement of what a length costs rather than a
    biological backbone. Building from the kit's full 106-residue chain A
    would fix that and would make the shaper read a file the smoke does not
    carry; keeping it self-contained was the trade taken.
    """
    doc = json.loads(text)
    res, order = {}, []
    for line in doc["structure"].splitlines():
        if not line.startswith("ATOM") or len(line) < 54:
            continue
        key = line[22:27]
        if key not in res:
            res[key] = []
            order.append(key)
        res[key].append(line)
    if not order:
        raise ValueError("proteinmpnn shaper: the smoke input carries no ATOM records")

    out, serial, resseq = [], 0, 0
    while resseq < n:
        shift = 200.0 * (resseq // len(order))
        for key in order:
            if resseq >= n:
                break
            resseq += 1
            for line in res[key]:
                serial += 1
                x = float(line[30:38]) + shift
                out.append(
                    "%s%5d%s%s%4d %s%8.3f%s"
                    % (
                        line[:6],
                        serial,
                        line[11:21],
                        "A",
                        resseq,
                        line[27:30],
                        x,
                        line[38:],
                    )
                )
    doc["structure"] = "\n".join(out) + "\nEND\n"
    return json.dumps(doc)


def _genie3_len(text, n):
    """A genie3 request for designs of exactly n residues.

    Here the size really is the key, and generously so: `_engine_key` is a
    sha256 over the WHOLE composed request with only `paths.rootdir` and
    `experiment.name` removed, and the worker holds exactly one engine and
    rebuilds on any mismatch. So every rung is a genuine
    `build_everything` -- checkpoint read, network construction, sampler and
    data module.

    THIS IS THE PROVIDER THE MIXED PHASE WAS WRITTEN FOR, and the ladder's
    second rung is what found it. Upstream's `default_config` is a
    module-level ConfigDict whose `common` section holds module-level
    `FieldReference` objects, so the first `build_sample_config_from_dict` in
    a process succeeds and every later one raises
    "Cannot update a FieldReference from another FieldReference". It has
    nothing to do with the request -- not its length, not its batch size --
    only with being the SECOND build. Four identical requests could never
    have reached it. The worker now deep-copies a pristine config before
    anything builds and rebinds it before every build, and refuses to start
    if the config is already polluted, so a mixed ladder should PASS -- and
    that pass is the regression test for exactly that repair.

    `n_sample` stays at 2 deliberately: at batch size 1 that is two batches of
    the same feature shape, which is the only thing that exercises the CUDA
    graph's capture-then-replay, and the reply's `graph_cache.hits` should
    read 1. Dropping it to 1 leaves a miss and no hit. `n_sample_step` and
    `direction_scale` are held constant because both are also in the engine
    key, and varying two axes at once would confound the ladder.
    """
    import yaml

    doc = yaml.safe_load(text)
    ds = doc["generation"]["dataset"]
    ds["min_length"] = n
    ds["max_length"] = n
    # min == max already pins one length; the measured ladder used n here.
    ds["length_step"] = n
    return yaml.safe_dump(doc, sort_keys=False)


def _boltzgen_len(text, n):
    """A boltzgen monomer of exactly n residues.

    SAY THIS PLAINLY: boltzgen has NO ENGINE KEY, because it holds no engine.
    Upstream re-reads the step's checkpoint inside every run, the kit's
    in-process module is exec'd fresh per request, and `configure` is a clean
    subprocess -- so every request is already a full rebuild and there is no
    cache a ladder could fail to invalidate. What residency buys here is the
    process: imports, the CUDA context and the Triton / cuEquivariance JIT
    caches. This ladder therefore measures the per-request capture shape and
    the VRAM envelope, and it is not a rebuild test.

    It is still worth running, for a reason specific to this provider: the
    kit's cross-attention lever keeps a MODULE-LEVEL `STATS` dict and
    `_disable(reason)` turns the lever off FOR THE PROCESS on a mismatch, and
    the atexit verdict then ends the process with exit 3. So one bad shape
    poisons every later request in a held worker -- genie3's hazard in a
    different place, and only a mixed sequence of shapes can find it.

    `n..n` rather than a range: `parse_polymer` draws
    `np.random.randint(start, end + 1)` per design, so a range would give
    every design in the batch a different shape and the rung would not be one
    length.

    num_designs and diffusion_batch_size stay at 2. Neither is an engine key
    -- they are resolved in a per-request subprocess -- but a diffusion batch
    of ONE is refused by the worker on this mode, and that pre-check exists
    because without it the kit's hoist self-check fails a stride comparison,
    disables the lever for the process and ends it with exit 3. `steps` stays
    ["design"] so the rung is the one GPU step the budget was measured on;
    the full pipeline would also load Boltz-2 for folding, a different and
    larger peak.

    WATCH FOR `produced=NOTHING` RATHER THAN A FAILURE. Upstream SKIPS a
    diffusion batch it cannot fit and still exits 0, so an over-large rung
    comes back successful and empty. `ask` prints produced=NOTHING for it and
    does not count it as failed; read that as a failed rung by hand.
    """
    import yaml

    doc = yaml.safe_load(text)
    doc["specification"]["entities"][0]["protein"]["sequence"] = "%d..%d" % (n, n)
    return yaml.safe_dump(doc, sort_keys=False)


def _rfdiffusion3_case(text, n):
    """n residues, AND a per-rung sampler perturbation -- because length alone
    rebuilds nothing here.

    THE APNOVO TRAP, A THIRD TIME, in the provider whose own measured ladder
    is written in residues. `_build_key` is
    `{"diffusion_batch_size", "inference_sampler"}` and NOTHING ELSE: the
    length, `n_batches`, the seed and the specification are all free, and
    `engine.initialize()` returns early once the engine exists. So a pure
    length ladder would move the tensor shapes and the peak while reusing one
    build for every rung, and would print four greens having rebuilt nothing.

    The rung therefore carries both. The length is what the VRAM envelope is
    quoted in, so it stays the rung's number; `num_timesteps` is perturbed by
    an injective function of it so every rung is also a distinct build key --
    a 2.7 GB checkpoint reload and a model construct per rung.

    THE PERTURBATION IS DELIBERATELY TINY AND SITS ON THE DEFAULT. Upstream's
    default is 200, so 200 + n // 100 gives 201..204 across the measured
    ladder: within about 2% of the configuration the envelope was measured at,
    and `num_timesteps` is a LOOP BOUND rather than a shape, so it moves the
    build key without moving the peak the ladder exists to measure.

    DO NOT LADDER ABOVE THE MEASURED 400 RESIDUES. The kit pins its
    dense-versus-sparse atom-attention decision per shape for the process, and
    on this route a shape it sends sparse is REFUSED -- by raising
    `KernelsRefused`, which subclasses `SystemExit`. That still takes the whole
    resident worker down with exit 5, deliberately: the verdict is about the
    process, not the rung. What has changed is that it is now legible. `serve`
    answers the refusal before it re-raises, so the rung fails with
    `WorkerRequestError(reason="worker_exiting")` naming the route and the
    transcript rather than the connection error it used to be, and the later
    rungs fail to connect as before. A ladder that dies partway is that, not a
    harness fault. The threshold is a joint function of length, diffusion batch
    and CURRENTLY FREE memory, so a co-tenant can trip it at a rung that passed
    before.

    None of the levers the kit refuses by name (classifier-free guidance,
    low-memory mode, the symmetry sampler, compile_model) is set here.
    """
    doc = json.loads(text)
    spec = doc["specification"]
    # The smoke's design name is "smoke60"; read it rather than hard-code it.
    name = next(iter(spec))
    spec[name]["length"] = str(n)
    opts = doc.setdefault("options", {})
    sampler = dict(opts.get("inference_sampler") or {})
    sampler["num_timesteps"] = 200 + n // 100
    opts["inference_sampler"] = sampler
    return json.dumps(doc)


def _boltz_len(text, n):
    """A boltz YAML of n residues -- the rung is the exact token count.

    Boltz does NOT pad: `inferencev2` features the record with
    `max_tokens=None` and `max_atoms=None`, and the batch is one record, so n
    residues go through the trunk as n tokens. The engine is the kit's
    `graph_trunk` lever, whose generations are keyed on `b["z"].shape[1]` with
    no rounding -- one `torch.cuda.MemPool` and one captured set of graphs per
    DISTINCT token count, held at module level across requests. That cache is
    what the provider's "structure pass falls from ~23 s to 5.8 s" is.

    TWO THINGS DECIDE THE RIGHT RUNGS, and the default ladder gets both wrong.
    Graphs are used only inside [MIN, MAX] tokens and the fast row sets
    `BOLTZ_GRAPH_TRUNK_MAX_TOKENS=300`: above it the lever steps aside BY NAME
    (counted `eager:above_max_tokens`) and captures nothing, so rungs of 400
    and 800 would exercise no engine at all. And only two generations are
    kept, so a third distinct count evicts the oldest -- itself worth seeing.
    Hence 100/200/290/400: three capture generations with one eviction, then
    one deliberate rung above the ceiling to exercise the step-aside and the
    pool release.

    `msa: empty` is rewritten onto the chain rather than assumed. A protein
    chain without it defaults to the MSA-SERVER path, which is a different
    mode, not a different size -- and that mode is what this file's MODES
    entry toggles deliberately. A shaper that dropped it would silently merge
    the two axes.

    No ascending discipline is needed for this provider's peaks: its worker
    resets `torch.cuda` peak stats per request through `on_reset`, so every
    rung reports its own peak rather than a session high-water mark.
    """
    seq = _tile(PROT, n)
    out, done = [], False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("sequence:"):
            out.append(line[: len(line) - len(line.lstrip())] + "sequence: " + seq)
            done = True
        elif stripped.startswith("msa:"):
            out.append(line[: len(line) - len(line.lstrip())] + "msa: empty")
        else:
            out.append(line)
    if not done:
        raise ValueError(
            "boltz shaper: no `sequence:` line in the smoke -- re-derive this "
            "from the smoke rather than guessing its shape"
        )
    return chr(10).join(out) + chr(10)


def _chai1_crop(text, n):
    """A chai1 FASTA of n residues -- and n must be chosen to CHANGE THE CROP.

    THIS IS THE apnovo TRAP, LIVE, AND THE DEFAULT LADDER WALKS INTO IT.
    chai-lab pads every input to one of seven exported sizes --
    `AVAILABLE_MODEL_SIZES = [256, 384, 512, 768, 1024, 1536, 2048]`, and
    `pad_size` returns the smallest one >= the token count. The crop, not the
    residue count, is then asserted and threaded through every module as
    `crop_size`, and the kit's hoisted denoiser caches its Inductor compile in
    a dict keyed on `(crop_size, hoister)` that lives for the life of the
    process. So the engine key is the CROP.

    The default `100,200,400,800` lands on crops 256, 256, 512, 1024: rung 2
    is a byte-identical engine to rung 1 and would print green having built
    nothing. DEFAULT_LENGTHS therefore gives this provider 250/380/500/760 ->
    256/384/512/768, four distinct crops and four distinct compiles.

    A rung exactly on a boundary is fine (`pad_size` is `>=`), and one residue
    over a boundary jumps a crop -- useful if you want to assert the bucket
    moved rather than assume it.

    Single chain on purpose: the smoke is one protein chain, the declared
    budget was measured on it, and nothing in the engine key cares about chain
    count. The cost is that `iptm` is vacuous at every rung, which is a real
    gap -- an interface ladder would need two chains with DISTINCT `name=`
    values (duplicate names are refused outright) and distinct sequences (the
    ESM pass deduplicates by sequence, so two identical chains would embed
    once and that leg would stop scaling).

    The header grammar is strict and is reproduced rather than carried:
    exactly one `|`, an entity word from a five-case match, and a label that
    is either `name=<x>` or a bare `<x>`. A second `|` raises.

    CEILING: 2048 tokens, a real refusal -- `raise_if_too_many_tokens` raises
    `UnsupportedInputError`, and `pad_size` would raise before that. Do not
    ladder above it expecting a measurement.

    Like boltz, this worker resets peak memory stats at the top of every
    prediction, so its peaks are per-request and need no ascending discipline.
    """
    if n > 2048:
        raise ValueError(
            "chai1 shaper: %d tokens is above the top exported size (2048); "
            "chai-lab refuses it rather than running it" % n
        )
    return ">protein|name=rung%d" % n + chr(10) + _tile(PROT, n) + chr(10)


# hg38 SNVs whose REF has been checked against the genome this provider reads,
# the hg38 FASTA this provider reads, `$BORZOI_CALICO_WEIGHTS/hg38.ml.fa`
# (worker: `WEIGHTS_ROOT / "hg38.ml.fa"`), through its .fai -- all seven match.
#
# THE CHECK IS THE POINT, because a wrong REF here does not get refused, it
# CRASHES. `vcf_snps` does not validate by default, and `snp_seq1` on a
# mismatch prints "WARNING: ... reference genome does not match any allele"
# and returns an EMPTY LIST (baskerville/vcf.py:244-248). That becomes an
# array of shape (0,) and the Keras call fails inside the model, which reads
# as a provider defect rather than a bad fixture. So these cannot be invented,
# and they cannot be tiled from a pattern the way a protein sequence can.
#
# The first row is the smoke's own variant, so rung 1 is the smoke. The other
# six are the kit's own test input (borzoi/tests/inputs/example_snvs.vcf) --
# the same provenance argument fixtures/README.md makes for gpnstar. Seven is
# more than the ceiling of four, so no row is ever repeated within a run.
_BORZOI_SNVS = [
    ("chr1", 43110773, "G", "A"),
    ("chr1", 5874827, "C", "T"),
    ("chr2", 5540132, "G", "T"),
    ("chr3", 5099582, "C", "T"),
    ("chr5", 6023169, "T", "C"),
    ("chr8", 5724953, "G", "A"),
    ("chr12", 5290537, "C", "G"),
]


def _borzoi_variants(text, n):
    """A request for n variants -- borzoi's rung is a VARIANT COUNT, not a length.

    Nothing in this provider recompiles: `SeqNN` is built once at worker start
    over a fixed `Input(shape=(524288, 4))` and `SeqNN.__call__` is plain eager
    numpy, with no `tf.function` and so no retrace cache to key on. And the
    caller's own sequence never reaches the model at all -- each variant is
    scored on a 524,288-base window cut from the genome around it, so the
    tensor is always (2, 524288, 4), one ref row and one alt row.

    So a length ladder would scale nothing, and this is the axis that does
    scale: cost is per variant, and the count is also what sizes the output
    HDF5 datasets and what `write_pct` takes its percentiles over -- a
    one-row percentile and an n-row percentile are different arithmetic, which
    no number of repeats would reach.

    THE RUNG IS NOT CLAMPED TO THE CEILING ON PURPOSE. The worker refuses more
    than `BORZOI_CALICO_MAX_VARIANTS` (4 by default), so an over-large rung
    shows that refusal happening rather than quietly becoming a smaller run --
    the same choice the opendde entry below makes about its 512-token ceiling.
    Run this one as `--lengths 1,2,3,4`; the default 100,200,400,800 is four
    refusals, which is a real result but not a ladder.
    """
    doc = json.loads(text)
    out = []
    for i in range(n):
        chrom, pos, ref, alt = _BORZOI_SNVS[i % len(_BORZOI_SNVS)]
        # Distinguish the rows if n ever exceeds the pool, so the `snp` dataset
        # and the reply rows stay addressable.
        suffix = "" if i < len(_BORZOI_SNVS) else "_%d" % (i // len(_BORZOI_SNVS))
        out.append(
            {
                "chrom": chrom,
                "pos": pos,
                "ref": ref,
                "alt": alt,
                "id": f"{chrom}_{pos}_{ref}_{alt}_b38{suffix}",
            }
        )
    doc["variants"] = out
    return json.dumps(doc)


# A provider whose ACCURACY depends on a mode the smoke does not exercise
# declares that mode here, and a run that skips it is INCOMPLETE.
#
# Measured for boltz on five PDB entries released after every model's training
# cutoff, two of them with no pre-2024 PDB relative at >=20% identity: mean
# TM-score to the experiment 0.960 through the MSA server and 0.637 without it,
# with one 180-residue target at 0.197 -- which is what two unrelated proteins
# score. The smoke, every ladder rung and every repeat run `msa: empty`, so
# four green repeats certify the configuration no user should choose. The
# provider's own pLDDT reports the collapse honestly (rho 0.99 against measured
# TM over both modes), so this case asserts a record came back at all; grading
# the geometry is a benchmark's job, not an acceptance test's.
MODES = {
    "boltz": [
        {
            "label": "msa server",
            "transform": _boltz_msa_mode,
            "options": {"use_msa_server": True},
            "network": True,
        }
    ],
}

SHAPERS = {
    "mosaic": _mosaic_design,
    # OpenDDE speaks Protenix's AlphaFold-Server style input: a one-job list whose
    # first entity is a proteinChain, so its ladder is shaped exactly like
    # protenix_v1's. The CEILING IS NOT: 400 tokens here against protenix_v1's
    # 800, and 400 is the largest point its budget was ever measured at (512 and
    # 800 were never run). This harness drives the WORKER, so a rung past 400 is
    # refused by MAX_TOKENS in opendde_resident_worker and never reaches
    # opendde_tool's MAX_TOKENS_TOTAL -- which is the refusal opendde's
    # verified_on quotes. Keep --lengths at or below 400 for a ladder; go past it
    # only to exercise the refusal.
    "opendde": lambda x, n: _json_seq(
        x, n, [0, "sequences", 0, "proteinChain", "sequence"]
    ),
    "protenix_v1": lambda x, n: _json_seq(
        x, n, [0, "sequences", 0, "proteinChain", "sequence"]
    ),
    "progen2": _progen2_ctx,
    "atlasfold": _fasta_one,
    "af3_torch": _af3_json,
    "af3_jax": _af3_json,
    "openfold3": lambda t, n: _json_seq(
        t, n, ["queries", "smoke", "chains", 0, "sequence"]
    ),
    # The SAME dialect as openfold3, checked rather than copied: 0.5.0's
    # InferenceQuerySet reads the same {"queries": {<id>: {"chains": [...]}}}
    # document (stock/src/examples/example_inference_inputs/*.json are
    # byte-shaped identically to 0.4.1's), and this provider's smoke keeps the
    # query id "smoke", so the path is the same four keys.
    "openfold3_ob0": lambda t, n: _json_seq(
        t, n, ["queries", "smoke", "chains", 0, "sequence"]
    ),
    "esmfold2": lambda t, n: _json_seq(t, n, [0, "sequences", 0, "sequence"]),
    "esmc": lambda t, n: _tile(PROT, n),
    "e1": _e1_fasta,
    "rosettafold3": lambda t, n: _json_seq(t, n, [0, "components", 0, "seq"]),
    "evo2": lambda t, n: _tile(DNA, n),
    "gpnstar": _gpnstar_vep,
    "esm_if1": _esm_if1_backbone,
    "colabfold": _colabfold_a3m,
    "af2ig": _af2ig_complex,
    "complexa": _complexa_design,
    "colabdesign": _colabdesign_case,
    # NOT a length ladder: everything pads to 512 residues, so the rung is a
    # denoising step count. See _apnovo_steps.
    "apnovo": _apnovo_steps,
    # NOT a length ladder either: the rung is a variant count. See
    # _borzoi_variants, and run it as `--lengths 1,2,3,4`.
    "borzoi_calico": _borzoi_variants,
    # The rung IS the size here, but it is the COMPLEX's token count, and it
    # really does re-plan the composition. See _ef2inv_case.
    "ef2inv": _ef2inv_case,
    # A cost table rather than a rebuild test, and the docstring says so.
    "proteinmpnn": _proteinmpnn_backbone,
    "boltz": _boltz_len,
    # The rung must CHANGE THE CROP, not merely the length. See _chai1_crop.
    "chai1": _chai1_crop,
    "genie3": _genie3_len,
    "boltzgen": _boltzgen_len,
    # Length alone rebuilds NOTHING here; the rung carries a sampler
    # perturbation too. See _rfdiffusion3_case.
    "rfdiffusion3": _rfdiffusion3_case,
}


# THE DEFAULT LADDER IS WRONG FOR SOME PROVIDERS, AND WRONG IN THE WAY THIS
# SCRIPT EXISTS TO CATCH. 100/200/400/800 lands chai1 on crops 256, 256, 512
# and 1024 -- its second rung is a byte-identical engine to its first, and it
# would print green having compiled nothing. It puts two of boltz's four rungs
# above the token ceiling where the graph lever steps aside and captures
# nothing. It asks borzoi_calico for 100 variants against a ceiling of 4, so
# every rung is a refusal rather than a rung.
#
# A provider that knows its own engine key also knows where the rungs belong,
# so it says so here and `--lengths` stays available to override.
DEFAULT_LENGTHS = {
    # crops 256 / 384 / 512 / 768 -- four distinct exported sizes
    "chai1": [250, 380, 500, 760],
    # three capture generations (one eviction at KEEP=2), then one rung above
    # BOLTZ_GRAPH_TRUNK_MAX_TOKENS=300 to exercise the step-aside
    "boltz": [100, 200, 290, 400],
    # the ceiling is 4 variants, and each costs about 255 s
    "borzoi_calico": [1, 2, 3, 4],
    # the smoke's own size, the size the budget was quoted at, the last rung
    # that still gets the trunk graph pool, and the tool layer's ceiling
    "ef2inv": [135, 195, 256, 300],
    # denoising steps, with the published setting as the top rung
    "apnovo": [100, 250, 500, 1000],
    # 106 is the full 5L33 chain A; 400 is the top of what has ever been run
    "proteinmpnn": [106, 200, 400, 800],
    # 670 is the top of the measured envelope and the tool's own ceiling
    "genie3": [100, 200, 400, 670],
    # the measured ladder; nothing here was ever pushed to failure
    "boltzgen": [60, 100, 200, 400, 600],
    # DO NOT RAISE. Past the measured 400 the kit's attention preflight can
    # refuse via a SystemExit subclass, which kills the worker rather than
    # failing the request.
    "rfdiffusion3": [100, 200, 300, 400],
}


# A SHAPER WOULD BE WRONG HERE, AND SAYING "NO SHAPER" IS NOT THE SAME AS
# SAYING SO. The `!! NO SHAPER` block below tells its reader to go and add
# one; for these providers that advice would produce exactly the failure this
# script exists to prevent -- four rungs, one engine, four greens. Each entry
# is the reason, and a run of one of these is COMPLETE rather than incomplete.
NO_SHAPER = {
    "enformer": (
        "every request is centre-cropped or N-padded to Enformer's fixed "
        "196,608 bases before the model sees it (SEQ_LENGTH at "
        "enformer_resident_worker.py:96, applied in _encode), so the tensor is "
        "always (1, 196608) and a length ladder would run the SAME shape four "
        "times. The worker also builds its model once at import and caches "
        "nothing, so no request-reachable key exists to vary. (Under kit mode "
        "`exact`, which is x86-64 only and `off` here, the graph lever keys on "
        "batch size and window length -- and the worker fixes both.)"
    ),
    "enformer_deepmind": (
        "same fixed window, one size up: every request becomes "
        "(1, 393216, 4) (INPUT_LENGTH at "
        "enformer_deepmind_resident_worker.py:103, applied in _one_hot), so an "
        "8 kb sequence and a 393 kb one cost the same ~200 s. It is a TF-Hub "
        "SavedModel called through predict_on_batch with no tf.function of "
        "ours, so nothing is traced per shape either -- two consecutive "
        "identical predictions measured 194.1 s and 205.8 s, i.e. the second "
        "is not cheaper. Its provider.toml already declares this."
    ),
}

# What a rung MEANS, for a provider whose rung is not residues. The label is
# not decoration: a run that printed "ladder 400aa" for apnovo would be
# recording a design length that no rung ever used, and the measured table a
# reader builds from this output would be wrong in the one column it exists
# for. Default "aa".
UNITS = {
    "apnovo": "steps",
    "borzoi_calico": "variants",
    "ef2inv": "tokens",
    "colabdesign": "tokens",
    "af2ig": "res (2 chains)",
    "colabfold": "res (2 chains)",
    "complexa": "res",
    "evo2": "nt",
    "gpnstar": "nt",
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument(
        "--lengths",
        default=None,
        help="comma-separated rungs; defaults to this provider's own ladder "
        "from DEFAULT_LENGTHS, which exists because the generic "
        "100,200,400,800 is actively wrong for several providers",
    )
    ap.add_argument("--repeats", type=int, default=4)
    ap.add_argument(
        "--no-network",
        action="store_true",
        help="skip declared modes that need a service off this host; the run "
        "then reports INCOMPLETE rather than a pass",
    )
    a = ap.parse_args()

    root = Path(__file__).resolve().parents[2] / "src" / "tooluniverse" / "remote"
    mp = root / a.slug / "provider.toml"
    m = M.load(mp)
    smoke = m.resolve(m.smoke)
    if smoke is None:
        print(f"{a.slug}: no [runtime] smoke declared")
        return 2
    text = smoke.read_text()

    out = Path(os.path.expanduser(f"~/.cache/tooluniverse/measured/{a.slug}-verify"))
    out.mkdir(parents=True, exist_ok=True)
    w = backend.worker_for(mp)
    w.request_timeout_s = m.smoke_timeout_s
    w.start_timeout_s = max(w.start_timeout_s, m.smoke_timeout_s)

    def ask(label, payload, name, options=None):
        t0 = time.time()
        try:
            r = w.request(
                {
                    "op": "predict",
                    "input": payload,
                    "out_dir": str(out / name),
                    "name": name,
                    "seed": 0,
                    "options": dict(options or {}),
                }
            )["result"]
        except Exception as exc:
            print(f"  {label:22} FAILED  {str(exc).splitlines()[0][:110]}", flush=True)
            return None
        # The outputs assertion applied here too: a reply is not a result.
        made = bool(r.get("files")) or any(r.get(k) for k in m.output_keys)
        print(
            f"  {label:22} {time.time() - t0:7.1f}s  "
            f"peak={str(r.get('peak_reserved_gib')):7} "
            f"produced={'yes' if made else 'NOTHING'}  {r.get('timing')}",
            flush=True,
        )
        return r

    print(
        f"{a.slug}: build_s={w.request({'op': 'ping'}).get('build_s')}  "
        f"declared={m.vram_budget_gb} GiB"
    )

    shaper = SHAPERS.get(a.slug)
    unit = UNITS.get(a.slug, "aa")
    if a.lengths:
        lens = [int(x) for x in a.lengths.split(",")] if shaper else []
    else:
        lens = list(DEFAULT_LENGTHS.get(a.slug, [100, 200, 400, 800])) if shaper else []
    if lens:
        print(
            "   rungs %s %s (%s)"
            % (
                ",".join(str(x) for x in lens),
                unit,
                "given" if a.lengths else "this provider's own ladder",
            )
        )

    # The ladder runs FIRST and ASCENDING. `peak_reserved_gib` is a running
    # high-water mark in six of the eight workers written so far -- only boltz
    # and enformer reset it per request through `on_reset` -- so one large
    # request earlier in the session pins every later rung to its value. Taking
    # the ladder after a mixed-shape phase made a 100-residue rung read 24.44
    # GiB where a clean session reads 24.08. That number was not wrong; it was
    # answering a different question.
    if lens:
        print("-- ladder, ascending, before anything larger (the budget envelope)")
        for n in lens:
            ask(f"ladder {n}{unit}", shaper(text, n), f"L{n}")

        print("-- mixed shapes (a change and a repeat must both survive)")
        small, big = lens[0], lens[len(lens) // 2]
        for i, n in enumerate([small, small, big, small]):
            ask(f"mixed {i} ({n}{unit})", shaper(text, n), f"m{i}")

    print(f"-- {a.repeats} consecutive identical requests (the acceptance test)")
    ok = 0
    for i in range(a.repeats):
        if ask(f"repeat {i}", text, f"r{i}") is not None:
            ok += 1
    print(f"   -> {ok}/{a.repeats} answered")

    modes = MODES.get(a.slug, [])
    modes_rc = 0
    if modes:
        print("-- declared modes the smoke does not exercise")
        for mode in modes:
            label = mode["label"]
            if mode.get("network") and a.no_network:
                print(
                    f"  {'mode ' + label:22} SKIPPED (--no-network): this run "
                    f"is INCOMPLETE, and {a.slug} is only verified in the "
                    f"mode its smoke runs"
                )
                modes_rc = max(modes_rc, 2)
                continue
            name = "mode_" + label.replace(" ", "_")
            # Start clean, or the case cannot fail. process_inputs skips a
            # record its processed tree already holds, so a second run over a
            # previous run's directory answers in 0.05 s WITHOUT calling the
            # service this case exists to exercise -- measured, with the mode
            # pointed at a server that could not answer and passing anyway.
            shutil.rmtree(out / name, ignore_errors=True)
            if ask(f"mode {label}", mode["transform"](text), name, mode["options"]) is None:
                modes_rc = max(modes_rc, 1)

    if not shaper and a.slug in NO_SHAPER:
        print(
            f"-- no shaper for {a.slug}, DELIBERATELY: {NO_SHAPER[a.slug]}\n"
            f"   Repeats are the whole test for this provider, and this run "
            f"is complete."
        )
    elif not shaper:
        print(
            f"!! NO SHAPER FOR {a.slug}: this run is INCOMPLETE, and not "
            f"only because the budget envelope is unestablished. Identical "
            f"requests rebuild NOTHING -- a held engine is built once and "
            f"replayed -- so they cannot show that the worker can build a "
            f"SECOND engine. genie3 would have passed four identical "
            f"requests and raised on the first one that changed its engine "
            f"key, because upstream's config is a module-level mutable "
            f"permitting one build per process; the ladder found it on its "
            f"second rung. Add a {a.slug} shaper before reading this as a pass."
        )

    w.stop(grace_s=60)
    # A failure outranks an incompleteness, and boltz is why: it has a declared
    # mode and no shaper, so returning 2 for the missing shaper first would
    # report a mode that FAILED as merely unestablished.
    if ok != a.repeats or modes_rc == 1:
        return 1
    if not shaper and a.slug not in NO_SHAPER:
        return 2
    # A skipped mode leaves the run incomplete.
    return modes_rc


if __name__ == "__main__":
    sys.exit(main())
