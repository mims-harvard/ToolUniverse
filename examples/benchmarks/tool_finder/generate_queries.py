"""Step 2 - generate queries along a difficulty gradient.

For each (seed tool, distinct test example) pair, the generator is grounded on that
example's real entity and asked to write three queries:

  L1 named     explicitly mentions the resource or database by name
  L2 intent    describes the intent without naming the tool or database
  L3 scenario  embeds the need in a paraphrased research scenario

Using every distinct test example (rather than one per tool) maximizes the number of
genuinely non-duplicate queries, since a different entity yields a different query. The
three difficulties of one (tool, example) pair form a triple, which allows a paired
comparison across difficulty levels on identical underlying needs.

Two filters run afterwards and flag rather than delete: degenerate queries (too short,
or an L2/L3 query that named the tool anyway), and the top 5% lexical-overlap tail
against the tool description, which would otherwise reward pure string matching.

Output: data/queries.jsonl (plus data/queries_sample.jsonl for manual inspection)

Environment:
    BENCH_N_SEEDS            seed tools (default 100; 0 = every tool with examples)
    BENCH_EXAMPLES_PER_TOOL  distinct examples per tool (default 1; 0 = all)
    BENCH_WORKERS            parallel generation requests (default 16)

Usage:
    BENCH_N_SEEDS=0 BENCH_EXAMPLES_PER_TOOL=0 python generate_queries.py
"""

import json
import os
import random
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed

import common as C

N_SEEDS = int(os.environ.get("BENCH_N_SEEDS", "100"))
EXAMPLES_PER_TOOL = int(os.environ.get("BENCH_EXAMPLES_PER_TOOL", "1"))
WORKERS = int(os.environ.get("BENCH_WORKERS", "16"))
SAMPLE_SIZE = int(os.environ.get("BENCH_SAMPLE", "200"))

PROMPT = """You generate natural-language search queries that a scientist would type to FIND a bioinformatics tool. You are given ONE tool and one concrete example of its inputs.

Tool name: {name}
Tool description: {desc}
Parameter schema (JSON): {params}
A real example input for this tool: {example}

Write THREE queries of increasing difficulty for retrieving THIS tool:
- "l1" (named/easy): explicitly mentions the resource/database/method by name. Use the real entity from the example input.
- "l2" (intent/medium): describes the user's intent but MUST NOT name the specific tool, database, or resource. Use the real entity.
- "l3" (scenario/hard): embed the need inside a short research scenario with paraphrased terminology and synonyms; do NOT name the tool/database.

Hard constraints:
- Do NOT copy phrases verbatim from the tool description; substitute synonyms for domain terms where natural.
- Use the real entity (gene symbol, accession, disease, query string, etc.) taken from the example input.
- Each query is one realistic user need, 1-2 sentences, no lists.
- Output STRICT JSON only: {{"l1": "...", "l2": "...", "l3": "..."}}"""


def pick_seeds(corpus, n):
    """Choose seed tools, round-robin across source files so no family dominates."""
    rng = random.Random(C.SEED)
    by_family = defaultdict(list)
    for name, m in corpus["meta"].items():
        if m["test_examples"]:
            by_family[m["source_file"]].append(name)
    for fam in by_family:
        rng.shuffle(by_family[fam])
    families = sorted(by_family)
    rng.shuffle(families)
    if n <= 0:
        return [t for fam in families for t in by_family[fam]]
    seeds, i = [], 0
    while len(seeds) < n and any(by_family.values()):
        fam = families[i % len(families)]
        if by_family[fam]:
            seeds.append(by_family[fam].pop())
        i += 1
        if i > 10 * n + 10000:
            break
    return seeds


def build_units(corpus, seeds, per_tool):
    """List of (tool, example_index, example) over deduplicated examples."""
    units = []
    for name in seeds:
        seen, uniq = set(), []
        for e in corpus["meta"][name]["test_examples"]:
            k = json.dumps(e, sort_keys=True)
            if k not in seen:
                seen.add(k)
                uniq.append(e)
        if per_tool > 0:
            uniq = uniq[:per_tool]
        for i, e in enumerate(uniq):
            units.append((name, i, e))
    return units


def generate_one(client, name, meta, example):
    msg = [
        {
            "role": "user",
            "content": PROMPT.format(
                name=name,
                desc=meta["description"][:1500],
                params=json.dumps(meta["parameter"])[:1200],
                example=json.dumps(example)[:400],
            ),
        }
    ]
    raw = C.chat(client, C.GEN_MODEL, msg, temperature=0.3, max_tokens=600, want_json=True)
    return C.parse_json_lenient(raw)


WORD = re.compile(r"[a-z0-9]+")


def toks(s):
    return set(WORD.findall(s.lower()))


def jaccard(a, b):
    A, B = toks(a), toks(b)
    return len(A & B) / len(A | B) if A and B else 0.0


def main():
    corpus = C.load_json(C.DATA_DIR / "corpus_snapshot.json")
    seeds = pick_seeds(corpus, N_SEEDS)
    units = build_units(corpus, seeds, EXAMPLES_PER_TOOL)
    C.log(
        f"seeds={len(seeds)} examples/tool={'all' if EXAMPLES_PER_TOOL == 0 else EXAMPLES_PER_TOOL}"
        f" -> {len(units)} units x 3 difficulties = up to {len(units) * 3} queries"
    )
    client = C.openai_client()

    results = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futs = {
            ex.submit(generate_one, client, n, corpus["meta"][n], e): (n, i, e)
            for (n, i, e) in units
        }
        done = 0
        for fut in as_completed(futs):
            n, i, e = futs[fut]
            try:
                obj = fut.result()
            except Exception as exc:  # noqa: BLE001
                C.log(f"  generation failed for {n}[{i}]: {str(exc)[:80]}")
                obj = None
            if obj:
                results[(n, i)] = (e, obj)
            done += 1
            if done % 200 == 0:
                C.log(f"  {done}/{len(units)} units generated")

    rows = []
    for (name, exidx), (example, obj) in results.items():
        meta = corpus["meta"][name]
        for diff in ("l1", "l2", "l3"):
            q = (obj.get(diff) or "").strip()
            if not q:
                continue
            rows.append(
                {
                    "query_id": f"{name}__{diff.upper()}__{exidx:04d}",
                    "source_tool": name,
                    "example_index": exidx,
                    "query": q,
                    "difficulty": diff.upper(),
                    "seed_test_example": example,
                    "modality": meta["source_file"],
                    "heldout": meta["heldout"],
                    "generator_model": C.GEN_MODEL,
                    "dropped_for_overlap": False,
                    "dropped_degenerate": False,
                }
            )

    # Filter 1: degenerate queries.
    n_degenerate = 0
    for r in rows:
        bad = len(r["query"].split()) < 4
        if r["difficulty"] in ("L2", "L3"):
            nm = toks(r["source_tool"].replace("_", " "))
            if nm and len(nm & toks(r["query"])) >= max(2, len(nm) - 1):
                bad = True  # named the tool despite being told not to
        if bad:
            r["dropped_degenerate"] = True
            n_degenerate += 1

    # Filter 2: the top 5% lexical-overlap tail, per difficulty level.
    meta_map = corpus["meta"]
    for r in rows:
        r["_overlap"] = jaccard(r["query"], meta_map[r["source_tool"]]["description"])
    n_overlap = 0
    for diff in ("L1", "L2", "L3"):
        grp = [r for r in rows if r["difficulty"] == diff and not r["dropped_degenerate"]]
        if not grp:
            continue
        ovs = sorted(x["_overlap"] for x in grp)
        threshold = ovs[int(0.95 * (len(ovs) - 1))]
        for r in grp:
            if r["_overlap"] > threshold:
                r["dropped_for_overlap"] = True
                n_overlap += 1
    for r in rows:
        del r["_overlap"]

    C.write_jsonl(C.DATA_DIR / "queries.jsonl", rows)
    kept = [r for r in rows if not r["dropped_degenerate"] and not r["dropped_for_overlap"]]
    rng = random.Random(C.SEED + 1)
    sample = rng.sample(kept, min(SAMPLE_SIZE, len(kept)))
    C.write_jsonl(C.DATA_DIR / "queries_sample.jsonl", sample)

    n_triples = len({(r["source_tool"], r["example_index"]) for r in kept})
    C.log(f"rows={len(rows)} kept={len(kept)} degenerate={n_degenerate} overlap_tail={n_overlap}")
    C.log(
        "kept by difficulty: "
        + ", ".join(f"{d}={sum(1 for r in kept if r['difficulty'] == d)}" for d in ("L1", "L2", "L3"))
    )
    C.log(f"distinct (tool, example) triples: {n_triples}")
    C.log(f"Wrote {C.DATA_DIR / 'queries.jsonl'} and queries_sample.jsonl ({len(sample)} rows)")


if __name__ == "__main__":
    main()
