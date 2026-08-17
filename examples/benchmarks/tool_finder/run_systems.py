"""Step 3 - run every search strategy and persist its top-10 ranking per query.

Strategies:

  toolrag         Tool_Finder with the default fine-tuned encoder (ToolRAG-T1, 1.5B)
  base            the identical un-fine-tuned base encoder -- the fine-tuning ablation
  keyword         Tool_Finder_Keyword (BM25 over the same documents)
  llm             Tool_Finder_LLM (keyword prefilter, then an LLM picks)
  openai-3-large  Tool_Finder with hosted OpenAI text-embedding-3-large
  openai-3-small  Tool_Finder with hosted OpenAI text-embedding-3-small
  gte-qwen2-7b    Tool_Finder with gte-Qwen2-7B-instruct
  e5-mistral-7b   Tool_Finder with e5-mistral-7b-instruct
  gte-large       gte-large-en-v1.5

Every embedding strategy encodes the identical per-tool document text and the identical
query text, so differences between them come from the encoder alone. Document
embeddings are cached to disk, keyed by model and corpus content.

The four encoder names in the middle of that list are exactly the values accepted by
the ``embedding_model`` parameter of the shipped ``Tool_Finder`` tool, so what this
script measures is reachable from ordinary ToolUniverse calls::

    tu.run({"name": "Tool_Finder",
            "arguments": {"description": "...", "embedding_model": "openai-3-large"}})

Output: data/rankings/<strategy>.jsonl

Usage:
    python run_systems.py                       # every strategy
    python run_systems.py toolrag base          # only the ablation pair
"""

import os
import re
import sys
import time

import numpy as np

import common as C

TOPK = 10
LLM_WORKERS = int(os.environ.get("BENCH_LLM_WORKERS", "8"))

# Strategies loaded through SentenceTransformer. ``prompt`` is applied to queries only.
# ``trust_remote_code`` is required by encoders that ship their architecture as
# repository code, and must stay False for the two strategies that reproduce the
# deployed Tool Finder (see the note in common.st_encode).
ENCODERS = {
    "toolrag": dict(model=C.MODELS["toolrag"], maxlen=4096, prompt="", trc=False),
    "base": dict(model=C.MODELS["gte_base"], maxlen=4096, prompt="", trc=False),
    "gte-qwen2-7b": dict(
        model="Alibaba-NLP/gte-Qwen2-7B-instruct",
        maxlen=4096,
        prompt=C.QUERY_INSTRUCTION,
        trc=True,
    ),
    "e5-mistral-7b": dict(
        model="intfloat/e5-mistral-7b-instruct",
        maxlen=4096,
        prompt=C.QUERY_INSTRUCTION,
        trc=True,
    ),
    "gte-large": dict(
        model="Alibaba-NLP/gte-large-en-v1.5", maxlen=4096, prompt="", trc=True
    ),
}

HOSTED = {
    "openai-3-large": "text-embedding-3-large",
    "openai-3-small": "text-embedding-3-small",
}

ALL_STRATEGIES = ["toolrag", "base", "keyword", "llm", *HOSTED, "gte-qwen2-7b", "e5-mistral-7b", "gte-large"]


def load_inputs():
    corpus = C.load_json(C.DATA_DIR / "corpus_snapshot.json")
    names = corpus["tool_names"]
    docs = [corpus["doc_texts"][n] for n in names]
    queries = [
        r
        for r in C.read_jsonl(C.DATA_DIR / "queries.jsonl")
        if not r["dropped_degenerate"] and not r["dropped_for_overlap"]
    ]
    return corpus, names, docs, queries


def persist(strategy, rows, elapsed):
    C.write_jsonl(C.RANK_DIR / f"{strategy}.jsonl", rows)
    C.save_json(
        C.RANK_DIR / f"{strategy}.meta.json",
        {
            "strategy": strategy,
            "n_queries": len(rows),
            "topk": TOPK,
            "seconds": round(elapsed, 2),
            "sec_per_query": round(elapsed / max(1, len(rows)), 4),
        },
    )
    C.log(f"[{strategy}] {len(rows)} queries in {elapsed:.1f}s")


def _rows(queries, tops):
    return [{"query_id": r["query_id"], "ranked": t} for r, t in zip(queries, tops)]


def run_encoder(strategy, names, docs, queries, corpus_md5):
    cfg = ENCODERS[strategy]
    t0 = time.time()
    cache = C.CACHE_DIR / f"{strategy}_{cfg['model'].replace('/', '_')}_{corpus_md5[:8]}.npy"
    qtexts = [r["query"] for r in queries]

    if cache.exists():
        C.log(f"[{strategy}] document embedding cache hit; encoding queries only")
        demb = np.load(cache)
        _, qemb = C.st_encode_pair(
            cfg["model"],
            docs[:1],
            qtexts,
            query_prompt=cfg["prompt"],
            max_seq_length=cfg["maxlen"],
            trust_remote_code=cfg["trc"],
        )
    else:
        C.log(f"[{strategy}] encoding {len(docs)} documents + {len(qtexts)} queries with {cfg['model']}")
        demb, qemb = C.st_encode_pair(
            cfg["model"],
            docs,
            qtexts,
            query_prompt=cfg["prompt"],
            max_seq_length=cfg["maxlen"],
            trust_remote_code=cfg["trc"],
        )
        np.save(cache, demb)

    persist(strategy, _rows(queries, C.cosine_topk(qemb, demb, names, k=TOPK)), time.time() - t0)


def run_hosted(strategy, names, docs, queries, corpus_md5):
    model = HOSTED[strategy]
    t0 = time.time()
    cache = C.CACHE_DIR / f"{strategy}_{model}_{corpus_md5[:8]}.npy"
    client = C.openai_client()
    if cache.exists():
        C.log(f"[{strategy}] document embedding cache hit")
        demb = np.load(cache)
    else:
        C.log(f"[{strategy}] embedding {len(docs)} documents with {model}")
        demb = C.embed(client, docs, model=model)
        np.save(cache, demb)
    qemb = C.embed(client, [r["query"] for r in queries], model=model)
    persist(strategy, _rows(queries, C.cosine_topk(qemb, demb, names, k=TOPK)), time.time() - t0)


def run_keyword(tu, queries):
    t0 = time.time()
    rows = []
    for i, r in enumerate(queries):
        out = tu.run(
            {
                "name": "Tool_Finder_Keyword",
                "arguments": {
                    "description": r["query"],
                    "limit": TOPK,
                    "return_call_result": True,
                },
            }
        )
        names = out[1] if isinstance(out, tuple) else []
        rows.append({"query_id": r["query_id"], "ranked": list(names)[:TOPK]})
        if (i + 1) % 50 == 0:
            C.log(f"  [keyword] {i + 1}/{len(queries)}")
    persist("keyword", rows, time.time() - t0)


def run_llm(tu, queries):
    from concurrent.futures import ThreadPoolExecutor, as_completed

    from tooluniverse.tool_finder_llm import ToolFinderLLM

    finder = ToolFinderLLM(
        {
            "name": "Tool_Finder_LLM",
            "type": "ToolFinderLLM",
            "description": "LLM tool finder",
            "configs": {
                "api_type": "CHATGPT",
                "model_id": C.LLM_FINDER_MODEL,
                "temperature": 0.0,
                "return_json": True,
            },
        },
        tooluniverse=tu,
    )
    t0 = time.time()

    def one(r):
        names = []
        try:
            res = finder.find_tools_llm(r["query"], limit=TOPK, include_reasoning=False)
            for t in res.get("selected_tools", []) if isinstance(res, dict) else []:
                nm = t.get("name") if isinstance(t, dict) else (t if isinstance(t, str) else None)
                if nm:
                    names.append(nm)
        except Exception as e:  # noqa: BLE001
            C.log(f"  [llm] failed on {r['query_id']}: {str(e)[:80]}")
        return {"query_id": r["query_id"], "ranked": names[:TOPK]}

    rows = [None] * len(queries)
    with ThreadPoolExecutor(max_workers=LLM_WORKERS) as ex:
        futs = {ex.submit(one, r): i for i, r in enumerate(queries)}
        done = 0
        for fut in as_completed(futs):
            rows[futs[fut]] = fut.result()
            done += 1
            if done % 25 == 0:
                C.log(f"  [llm] {done}/{len(queries)}")
    persist("llm", rows, time.time() - t0)


def main():
    want = sys.argv[1:] or ALL_STRATEGIES
    corpus, names, docs, queries = load_inputs()
    corpus_md5 = C.md5("".join(docs))
    C.log(f"strategies={want} pool={len(names)} queries={len(queries)} corpus={corpus_md5[:8]}")

    tu = C.get_tooluniverse() if any(s in want for s in ("keyword", "llm")) else None

    for s in want:
        if s in ENCODERS:
            run_encoder(s, names, docs, queries, corpus_md5)
        elif s in HOSTED:
            run_hosted(s, names, docs, queries, corpus_md5)
        elif s == "keyword":
            run_keyword(tu, queries)
        elif s == "llm":
            run_llm(tu, queries)
        else:
            C.log(f"unknown strategy: {s}")


if __name__ == "__main__":
    main()
