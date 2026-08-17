"""Shared utilities for the Tool Finder retrieval benchmark.

This module centralizes:
  * corpus construction (identical document text for every embedding system, so the
    comparison isolates the encoder and nothing else),
  * OpenAI / Azure OpenAI chat + embedding helpers (query generation and judging),
  * SentenceTransformer embedding helpers,
  * small IO helpers.

The per-tool document text reproduces exactly what ``ToolFinderEmbedding`` indexes::

    json.dumps(tooluniverse.prepare_tool_prompts([tool])[0])

encoded with ``prompt=""`` and ``normalize_embeddings=True``. See
``src/tooluniverse/tool_finder_embedding.py`` (``load_tool_desc_embedding`` and
``rag_infer``) for the deployed code path this mirrors.
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
import time
from pathlib import Path

# --------------------------------------------------------------------------- paths
HERE = Path(__file__).resolve().parent
DATA_DIR = HERE / "data"
RANK_DIR = DATA_DIR / "rankings"
RESULTS_DIR = HERE / "results"
CACHE_DIR = HERE / "cache"
for _d in (DATA_DIR, RANK_DIR, RESULTS_DIR, CACHE_DIR):
    _d.mkdir(parents=True, exist_ok=True)


def find_repo() -> Path:
    """Locate the ToolUniverse checkout.

    Only ``build_corpus.py`` needs this, to read the git commit and the per-tool
    source-file map. Set ``TOOLUNIVERSE_REPO`` to override; otherwise the installed
    package location is used.
    """
    env = os.environ.get("TOOLUNIVERSE_REPO")
    if env:
        return Path(env)
    try:
        import tooluniverse as _tu

        return Path(_tu.__file__).resolve().parents[2]
    except Exception:
        return HERE


REPO = find_repo()
TOOLDATA_DIR = REPO / "src" / "tooluniverse" / "data"

# Tools that are not retrieval targets (the finders themselves and control tokens).
EXCLUDE_TOOLS = [
    "Tool_RAG",
    "Tool_Finder",
    "Tool_Finder_LLM",
    "Tool_Finder_Keyword",
    "Tool_Finder_Find_Tools",
    "Finish",
    "CallAgent",
]

# Encoders under comparison. The first is the fine-tuned model shipped as the
# Tool Finder default; the second is its identical un-fine-tuned base, which is the
# ablation that isolates the contribution of fine-tuning.
MODELS = {
    "toolrag": "mims-harvard/ToolRAG-T1-GTE-Qwen2-1.5B",
    "gte_base": "Alibaba-NLP/gte-Qwen2-1.5B-instruct",
}

# Instruction-tuned retrievers expect the task instruction on the query only.
QUERY_INSTRUCTION = (
    "Instruct: Given a natural-language request from a scientist, retrieve the "
    "software tool that can fulfill it\nQuery: "
)

EMBED_MODEL = os.environ.get("BENCH_EMBED_MODEL", "text-embedding-3-large")
GEN_MODEL = os.environ.get("BENCH_GEN_MODEL", "gpt-5")   # query generator
JUDGE_MODEL = os.environ.get("BENCH_JUDGE_MODEL", "gpt-5")  # pooled relevance judge
LLM_FINDER_MODEL = os.environ.get("BENCH_LLM_FINDER_MODEL", "gpt-4.1")

SEED = 20260622

# Fine-tuning cutoff of the released ToolRAG-T1 checkpoint. Tools whose source file
# was added after this date could not have been seen during fine-tuning, and queries
# targeting them form the leakage-free held-out split.
HELDOUT_CUTOFF = "2025-03-15"


# --------------------------------------------------------------------------- IO
def read_jsonl(path):
    rows = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path, rows):
    with open(str(path), "w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def load_json(path):
    with open(path) as f:
        return json.load(f)


def save_json(path, obj):
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def md5(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()


def log(*a):
    print(*a, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- corpus
def get_tooluniverse():
    """Load a ToolUniverse instance with the full catalogue."""
    from tooluniverse import ToolUniverse

    tu = ToolUniverse()
    tu.load_tools()
    return tu


def _source_file_map():
    """Map tool name -> source ``*_tools.json`` stem, used as an application-area proxy."""
    m = {}
    for fp in glob.glob(str(TOOLDATA_DIR / "*_tools.json")):
        stem = Path(fp).stem
        try:
            cfg = json.load(open(fp))
        except Exception:
            continue
        items = cfg if isinstance(cfg, list) else cfg.get("tools", [])
        if not isinstance(items, list):
            continue
        for t in items:
            if isinstance(t, dict) and "name" in t:
                m[t["name"]] = stem
    return m


def build_corpus(tu):
    """Build the retrieval pool.

    Returns a dict with:
      ``tool_names`` ordered pool of tool names (special tools excluded),
      ``doc_texts``  {tool_name: document text} -- identical for every embedder,
      ``meta``       {tool_name: {description, parameter, test_examples, source_file, ...}}

    Ordering matches ``ToolFinderEmbedding``'s indexing order.
    """
    tool_names, _ = tu.refresh_tool_name_desc(
        enable_full_desc=True, exclude_names=EXCLUDE_TOOLS
    )
    name_set = set(tool_names)
    filtered = [t for t in tu.all_tools if t["name"] in name_set]
    prepared = tu.prepare_tool_prompts(filtered)
    src_map = _source_file_map()

    doc_texts, meta = {}, {}
    for raw, prep in zip(filtered, prepared):
        n = raw["name"]
        doc_texts[n] = json.dumps(prep)
        orig = raw.get("original_name", n)
        meta[n] = {
            "description": raw.get("description", ""),
            "parameter": raw.get("parameter", {}),
            "test_examples": raw.get("test_examples", []),
            "source_file": src_map.get(orig, src_map.get(n, "unknown")),
            "original_name": orig,
        }
    return {
        "tool_names": [t["name"] for t in filtered],
        "doc_texts": doc_texts,
        "meta": meta,
    }


# --------------------------------------------------------------------------- LLM API
def openai_client():
    """Return an OpenAI-compatible client.

    Set ``AZURE_OPENAI_ENDPOINT`` (plus ``AZURE_OPENAI_API_KEY``) to use Azure OpenAI,
    or ``OPENAI_API_KEY`` alone to use the public OpenAI API. Credentials are read from
    the environment only; never commit them.
    """
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    if endpoint:
        from openai import AzureOpenAI

        key = os.environ.get("AZURE_OPENAI_API_KEY")
        if not key:
            raise RuntimeError("AZURE_OPENAI_ENDPOINT is set but AZURE_OPENAI_API_KEY is not")
        return AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-12-01-preview"),
        )
    from openai import OpenAI

    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY (or AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_API_KEY)")
    return OpenAI()


def chat(client, model, messages, max_retries=6, temperature=0.0, max_tokens=1024, want_json=True):
    """Chat completion with retries. Reasoning models take ``max_completion_tokens``."""
    last = None
    for attempt in range(max_retries):
        try:
            kw = {"model": model, "messages": messages}
            if model.startswith("gpt-5") or model.startswith("o"):
                kw["max_completion_tokens"] = max(max_tokens, 4096)
            else:
                kw["max_tokens"] = max_tokens
                kw["temperature"] = temperature
            if want_json:
                kw["response_format"] = {"type": "json_object"}
            r = client.chat.completions.create(**kw)
            return r.choices[0].message.content or ""
        except Exception as e:  # noqa: BLE001
            last = e
            wait = min(2**attempt, 30)
            log(f"[chat retry {attempt + 1}/{max_retries} model={model}] {str(e)[:120]}; sleep {wait}s")
            time.sleep(wait)
    raise RuntimeError(f"chat failed after {max_retries} attempts: {last}")


def embed(client, texts, model=None, batch=64, max_retries=6):
    """Embed texts with a hosted model, returning L2-normalized float32 vectors."""
    import numpy as np

    model = model or EMBED_MODEL
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i : i + batch]
        for attempt in range(max_retries):
            try:
                r = client.embeddings.create(model=model, input=chunk)
                out.extend([d.embedding for d in r.data])
                break
            except Exception as e:  # noqa: BLE001
                wait = min(2**attempt, 30)
                log(f"[embed retry {attempt + 1}] {str(e)[:100]}; sleep {wait}s")
                time.sleep(wait)
        else:
            raise RuntimeError("embedding request failed after retries")
    arr = np.asarray(out, dtype="float32")
    arr /= np.linalg.norm(arr, axis=1, keepdims=True) + 1e-12
    return arr


def parse_json_lenient(s: str):
    """Best-effort JSON extraction from an LLM response."""
    s = s.strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.startswith("json"):
            s = s[4:]
    try:
        return json.loads(s)
    except Exception:
        a, b = s.find("{"), s.rfind("}")
        if a != -1 and b != -1 and b > a:
            try:
                return json.loads(s[a : b + 1])
            except Exception:
                return None
    return None


# --------------------------------------------------------- SentenceTransformer
def st_encode(model_name, texts, device="cuda", max_seq_length=4096, batch_size=32, prompt=""):
    """Encode exactly as the deployed Tool Finder does.

    Note the missing ``trust_remote_code``: this is deliberate and it matters. The
    deployed finder loads the model without it, which selects the native Qwen2
    architecture rather than the repository's custom class. Loading the same
    checkpoint *with* ``trust_remote_code=True`` produces different vectors and
    changes the measured ranking, so reproducing the shipped behavior requires
    omitting it here.
    """
    import torch
    from sentence_transformers import SentenceTransformer

    dev = device if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(model_name, device=dev)
    try:
        m.max_seq_length = max_seq_length
        m.tokenizer.padding_side = "right"
    except Exception:
        pass
    emb = m.encode(
        texts,
        prompt=prompt,
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=batch_size,
        show_progress_bar=True,
    )
    del m
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return emb.astype("float32")


def st_encode_pair(
    model_name,
    docs,
    queries,
    doc_prompt="",
    query_prompt="",
    device="cuda",
    max_seq_length=4096,
    batch_size=16,
    trust_remote_code=True,
    padding_side="right",
):
    """Load a model once and encode documents and queries, with optional prefixes.

    Instruction-tuned retrievers take the instruction on the query only; documents get
    no prefix. Used for the alternative encoders, each in its intended configuration.

    ``padding_side`` is set explicitly and defaults to "right" to match the deployed
    Tool Finder. It is not cosmetic: these encoders pool the last token, so the padding
    side determines which token that is, and leaving it at the tokenizer's own default
    silently changes the embeddings for anything shorter than the batch maximum.
    """
    import torch
    from sentence_transformers import SentenceTransformer

    dev = device if torch.cuda.is_available() else "cpu"
    m = SentenceTransformer(model_name, device=dev, trust_remote_code=trust_remote_code)
    try:
        m.max_seq_length = max_seq_length
        m.tokenizer.padding_side = padding_side
    except Exception:
        pass
    kw = dict(
        normalize_embeddings=True,
        convert_to_numpy=True,
        batch_size=batch_size,
        show_progress_bar=True,
    )
    demb = m.encode(docs, prompt=doc_prompt, **kw).astype("float32")
    qemb = m.encode(queries, prompt=query_prompt, **kw).astype("float32")
    del m
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    return demb, qemb


def cosine_topk(query_emb, doc_emb, tool_names, k=10):
    """Top-k tool names per query from normalized embeddings."""
    import numpy as np

    sims = query_emb @ doc_emb.T
    k = min(k, doc_emb.shape[0])
    idx = np.argpartition(-sims, kth=k - 1, axis=1)[:, :k]
    out = []
    for r in range(sims.shape[0]):
        order = idx[r][np.argsort(-sims[r, idx[r]])]
        out.append([tool_names[i] for i in order])
    return out
