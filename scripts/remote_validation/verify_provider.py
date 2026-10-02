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


SHAPERS = {
    "mosaic": _mosaic_design,
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
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--lengths", default="100,200,400,800")
    ap.add_argument("--repeats", type=int, default=4)
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

    def ask(label, payload, name):
        t0 = time.time()
        try:
            r = w.request(
                {
                    "op": "predict",
                    "input": payload,
                    "out_dir": str(out / name),
                    "name": name,
                    "seed": 0,
                    "options": {},
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
    lens = [int(x) for x in a.lengths.split(",")] if shaper else []

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
            ask(f"ladder {n}aa", shaper(text, n), f"L{n}")

        print("-- mixed shapes (a change and a repeat must both survive)")
        small, big = lens[0], lens[len(lens) // 2]
        for i, n in enumerate([small, small, big, small]):
            ask(f"mixed {i} ({n}aa)", shaper(text, n), f"m{i}")

    print(f"-- {a.repeats} consecutive identical requests (the acceptance test)")
    ok = 0
    for i in range(a.repeats):
        if ask(f"repeat {i}", text, f"r{i}") is not None:
            ok += 1
    print(f"   -> {ok}/{a.repeats} answered")
    if not shaper:
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
    if not shaper:
        return 2
    return 0 if ok == a.repeats else 1


if __name__ == "__main__":
    sys.exit(main())
