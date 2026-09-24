"""Tool finder that retrieves widely with BM25 and then grades the shortlist.

Embedding finders spend their budget on getting the ranking right with a small number
of candidates. This one does the opposite: it retrieves a wide, cheap lexical shortlist
and then asks a decision model to grade every candidate on the same three-level scale a
relevance judge would use. Grading a hundred candidates costs one round trip, because
the model answers every question in the request in parallel, so widening the shortlist
costs tokens but not latency.

The comparison that matters is not against the embedding finder, which answers in
milliseconds; it is against ``Tool_Finder_LLM``, the other finder that thinks. That one
prefilters with keywords and asks an LLM to choose among ten candidates, and takes about
0.67 s. This one grades a hundred candidates in about 0.64 s and ranks them 52% better
by NDCG@10. Latency grows slowly with the shortlist: 0.35 s at ten candidates, 0.43 s at
thirty, 0.64 s at a hundred, 0.93 s at two hundred.

Two stages:

1. **Retrieval.** BM25 over the tool documents, with stop words and JSON schema
   keywords removed, followed by RM3 pseudo-relevance feedback. No model, no GPU, no
   index server: the catalogue is small enough to score in memory in about 10 ms.
2. **Grading.** One call to TypeSafe's Jev with one ``score`` question per candidate.
   Each answer carries a probability distribution over the three levels, and the
   returned score is the expected relevance, which is what the candidates are sorted
   by. Ties fall back to the retrieval order.

Scoring fine-grained relevance levels rather than a yes/no judgement is a known way to
get more out of a zero-shot ranker; see Zhuang et al., "Beyond Yes and No: Improving
Zero-Shot LLM Rankers via Scoring Fine-Grained Relevance Labels" (NAACL 2024).

Requires ``TYPESAFE_API_KEY``. Without it the tool is not loaded, like any other
key-gated tool.
"""

import collections
import json
import math
import re
import time
import urllib.error
import urllib.request

from .base_tool import BaseTool
from .tool_registry import register_tool

ENDPOINT = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"

# Grading is a hosted third-party call, so every response says so, the way the
# opt-in web_search backends do. What leaves the process is the search text and
# the descriptions of the retrieved candidates.
PROVIDER_NOTICE = (
    "Candidates were graded by TypeSafe's hosted decision model at " + ENDPOINT + ". "
    "The search text and the descriptions of the retrieved tools are sent there; "
    "do not submit sensitive or patient-identifying information."
)

# The three levels a pooled relevance judge uses. The wording is deliberately the
# wording of the judging guideline rather than a paraphrase: the point of the middle
# level is to give the model somewhere to put a tool that does the right thing to the
# wrong resource, which is otherwise forced down to "irrelevant".
RELEVANCE_LEVELS = [
    "irrelevant: the tool does not serve this request",
    "partially relevant: it helps but is not the primary tool, or it performs the "
    "same kind of operation on a different database or resource",
    "directly answers: this tool fully serves the user's need",
]

# Dropped before indexing. The per-tool document is a JSON dump of the tool spec, so
# without this the schema vocabulary dominates: `type`, `properties`, `required` and
# `object` each occur in nearly every tool and together are about a fifth of all
# tokens, and they distort the document length that BM25 normalises by.
_SCHEMA_WORDS = frozenset(
    "type properties required string object boolean integer array items default "
    "number null true false enum parameter name description format "
    "additionalproperties oneof anyof".split()
)
_STOP_WORDS = frozenset(
    "a an and are as at be by for from has he in is it its of on that to was will "
    "with the this but they have i you we not or if then than into over under out up "
    "down all any each".split()
)
_TOKEN = re.compile(r"[a-z0-9]+")


def _tokenize(text):
    return [
        t
        for t in _TOKEN.findall(text.lower())
        if t not in _STOP_WORDS and t not in _SCHEMA_WORDS
    ]


class _BM25:
    """Okapi BM25 over an in-memory catalogue, with term-at-a-time scoring."""

    def __init__(self, documents, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.documents = documents
        self.n_docs = len(documents)
        self.doc_len = [len(d) for d in documents]
        self.avg_len = (sum(self.doc_len) / self.n_docs) if self.n_docs else 1.0
        self.postings = collections.defaultdict(list)
        for i, doc in enumerate(documents):
            for term, freq in collections.Counter(doc).items():
                self.postings[term].append((i, freq))

    def scores(self, query_terms):
        out = collections.defaultdict(float)
        for term, q_freq in collections.Counter(query_terms).items():
            hits = self.postings.get(term)
            if not hits:
                continue
            idf = math.log(1.0 + (self.n_docs - len(hits) + 0.5) / (len(hits) + 0.5))
            weight = idf * q_freq
            for doc_id, freq in hits:
                norm = 1.0 - self.b + self.b * self.doc_len[doc_id] / self.avg_len
                out[doc_id] += weight * freq * (self.k1 + 1.0) / (freq + self.k1 * norm)
        return out

    def top(self, query_terms, k):
        scores = self.scores(query_terms)
        return sorted(scores, key=lambda i: (-scores[i], i))[:k]


@register_tool("ToolFinderJev")
class ToolFinderJev(BaseTool):
    """Wide lexical retrieval followed by graded relevance scoring."""

    def __init__(self, tool_config, tooluniverse=None):
        super().__init__(tool_config)
        self.tooluniverse = tooluniverse
        configs = tool_config.get("configs", {}) or {}
        self.exclude_tools = configs.get(
            "exclude_tools",
            [
                "Tool_RAG",
                "Tool_Finder",
                "Tool_Finder_LLM",
                "Tool_Finder_Keyword",
                "Tool_Finder_Jev",
                "Finish",
                "CallAgent",
            ],
        )
        # 100 is where the measured quality curve flattens: going to 200 doubles the
        # tokens for about a point of NDCG@10, and only 0.6% of the candidates in that
        # extra band turned out to be relevant at all.
        self.candidate_depth = int(configs.get("candidate_depth", 100))
        self.description_chars = int(configs.get("description_chars", 400))
        self.model = configs.get("model", DEFAULT_MODEL)
        self.timeout = int(configs.get("timeout", 60))
        self.rm3 = configs.get("rm3", {}) or {}
        self._index = None
        self._index_names = None
        self._index_key = None

    # ------------------------------------------------------------------ index
    def _catalogue(self):
        tools = self.tooluniverse.return_all_loaded_tools(copy_tools=False)
        return [t for t in tools if t.get("name", "") not in self.exclude_tools]

    def _ensure_index(self, tools):
        key = frozenset(t.get("name", "") for t in tools)
        if self._index is not None and key == self._index_key:
            return
        self._index_names = [t.get("name", "") for t in tools]
        self._index = _BM25([_tokenize(json.dumps(t)) for t in tools])
        self._index_key = key

    def _retrieve(self, query, depth):
        """BM25 with RM3 pseudo-relevance feedback. Returns tool names, best first."""
        terms = _tokenize(query)
        if not terms:
            return []
        fb_docs = int(self.rm3.get("feedback_documents", 10))
        fb_terms = int(self.rm3.get("feedback_terms", 30))
        weight = int(self.rm3.get("query_weight", 3))

        expanded = list(terms)
        if fb_docs > 0 and fb_terms > 0:
            # RM3: take the terms that dominate the first-pass winners and add them to
            # the query. The original terms are repeated so that feedback supplements
            # the request rather than drifting away from it.
            counts = collections.Counter()
            for doc_id in self._index.top(terms, fb_docs):
                counts.update(self._index.documents[doc_id])
            seen = set(terms)
            extra = [t for t, _ in counts.most_common(fb_terms * 3) if t not in seen]
            expanded = terms * weight + extra[:fb_terms]

        return [self._index_names[i] for i in self._index.top(expanded, depth)]

    # ------------------------------------------------------------------ grading
    def _api_key(self):
        # Resolved per request, not once at construction, so a hosted multi-tenant
        # deployment keeps each caller's key to that caller.
        key = self.credential("TYPESAFE_API_KEY")
        if not key:
            raise RuntimeError(
                "TYPESAFE_API_KEY is not set; Tool_Finder_Jev needs it to grade candidates"
            )
        return key

    def _grade(self, query, candidates, descriptions):
        questions = {
            f"c{i}": {
                "type": "score",
                "instructions": (
                    f"How well does the tool `{name}` answer the request?\n"
                    f"Tool description: {descriptions[name]}"
                ),
                "criteria": RELEVANCE_LEVELS,
            }
            for i, name in enumerate(candidates)
        }
        body = json.dumps(
            {
                "state": {"request": query},
                "questions": questions,
                "model": self.model,
            }
        ).encode()
        request = urllib.request.Request(
            ENDPOINT,
            data=body,
            headers={
                "Authorization": f"Bearer {self._api_key()}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read())
        answers = payload.get("answers", {})
        return [
            float(answers.get(f"c{i}", {}).get("score", 0.0))
            for i in range(len(candidates))
        ]

    # ------------------------------------------------------------------ search
    def _search(self, query, limit, categories=None):
        """Return ``(tool_names, grading_error)``.

        ``grading_error`` is None when the shortlist was graded. When the grading
        call fails the retrieval order is returned instead of nothing: BM25 has
        already produced a usable shortlist, and a provider outage should degrade
        the ranking rather than leave the caller with no tools. A missing
        credential is not degraded this way -- that is a configuration error the
        caller has to see.
        """
        tools = self._catalogue()
        if categories:
            wanted = set(categories)
            tools = [t for t in tools if t.get("category") in wanted]
        if not tools:
            return [], None
        self._ensure_index(tools)
        by_name = {t.get("name", ""): t for t in tools}

        candidates = self._retrieve(query, self.candidate_depth)
        if not candidates:
            return [], None
        descriptions = {
            n: (by_name[n].get("description", "") or "").replace("\n", " ")[
                : self.description_chars
            ]
            for n in candidates
        }
        try:
            scores = self._grade(query, candidates, descriptions)
        except RuntimeError:
            # Raised for a missing credential, which is a configuration error the
            # caller has to see rather than a provider outage to rank around.
            raise
        except urllib.error.HTTPError as exc:
            return candidates[:limit], f"HTTP {exc.code}: {exc.reason}"
        except Exception as exc:  # noqa: BLE001 - any provider-side failure degrades
            return candidates[:limit], str(exc)
        # Sort by graded relevance; equal scores keep the retrieval order.
        ranked = sorted(range(len(candidates)), key=lambda i: (-scores[i], i))
        return [candidates[i] for i in ranked[:limit]], None

    # ------------------------------------------------------------------ interface
    def find_tools(
        self,
        message=None,
        picked_tool_names=None,
        rag_num=5,
        return_call_result=False,
        categories=None,
    ):
        """Match the interface of the other finders so this is a drop-in replacement."""
        if picked_tool_names is None:
            assert message is not None, "message or picked_tool_names is required"
            picked_tool_names, _ = self._search(message, rag_num, categories)

        picked = [n for n in picked_tool_names if n not in self.exclude_tools][:rag_num]
        specs = self.tooluniverse.get_tool_specification_by_names(picked)
        prompts = self.tooluniverse.prepare_tool_prompts(specs)
        if return_call_result:
            return prompts, picked
        return prompts

    def run(self, arguments):
        query = arguments.get("description") or arguments.get("query")
        if not query:
            return {"error": "description is required"}
        limit = int(arguments.get("limit", 10))
        picked = arguments.get("picked_tool_names")
        try:
            started = time.time()
            grading_error = None
            if picked is None:
                picked, grading_error = self._search(
                    query, limit, arguments.get("categories")
                )
            prompts, names = self.find_tools(
                picked_tool_names=picked,
                rag_num=limit,
                return_call_result=True,
            )
            if not arguments.get("return_call_result", True):
                return prompts
            payload = {
                "tools": names,
                "tool_prompts": prompts,
                "candidate_depth": self.candidate_depth,
                "seconds": round(time.time() - started, 2),
            }
            if arguments.get("picked_tool_names") is None:
                # Only a search reaches the grader, so only a search discloses it.
                payload["graded"] = grading_error is None
                payload["provider_notice"] = PROVIDER_NOTICE
                if grading_error is not None:
                    payload["grading_error"] = grading_error
                    payload["note"] = (
                        "Grading was unavailable, so these are the BM25 retrieval "
                        "results in retrieval order rather than graded relevance "
                        "order."
                    )
            return payload
        except RuntimeError as exc:
            return {"error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"error": f"Tool_Finder_Jev failed: {exc}"}
