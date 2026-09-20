---

name: tooluniverse-ml-inference-utility
description: "Generic ML/NLP/vision inference against any HuggingFace-hosted model (serverless hf-inference provider) — text classification/sentiment, dense text embeddings for semantic similarity, masked-token prediction (including protein language models), summarization, zero-shot classification against caller-supplied labels, named entity recognition, extractive question answering, translation, image classification, and object detection. Use when someone asks to \"classify this text with a HuggingFace model\", \"embed this text for similarity search\", \"run NER on this passage\", \"summarize this with model X\", \"zero-shot classify this against these labels\", \"predict the masked token\", \"classify/detect objects in this image\", or names a specific HuggingFace model_id to run inference with. NOT a domain-analysis skill itself — this is a generic cross-domain utility other skills should reach for as a supporting step, the same way tooluniverse-clinical-terminology-lookup is a supporting lookup step rather..."
---

# Generic ML/NLP/Vision Inference (HuggingFace)

Run any HuggingFace-hosted model for a standard inference task via ToolUniverse's
10 `HFInference_*` tools. This is a **utility skill**: reach for it as a supporting
step inside another workflow (e.g. summarizing a batch of retrieved abstracts,
extracting entities from clinical text, embedding sentences for a similarity
search) rather than treating it as a research domain in its own right.

## Honesty contract (read first) — the token requirement is not actually optional

Every tool's own JSON description says `HF_TOKEN` is an *optional* API key that
merely "raises rate limits." **Live testing on this date contradicts that**: all
10 tools, tested against the exact model IDs in their own `test_examples`, fail
with the identical error with no token set:

```
$ tu test HFInference_classify_text
✗ example 1  tool returned error: Unauthorized for
  distilbert/distilbert-base-uncased-finetuned-sst-2-english. The model may be
  gated/private; set a valid HF_TOKEN with access.
```

This reproduces across text and vision tools alike, and a dummy/invalid token
produces the exact same `Unauthorized` message (confirmed live) — so this is a
"needs a real, valid HuggingFace access token" requirement, not a cosmetic rate
limit. Treat `HF_TOKEN` as **required in practice** even though the tool schema
calls it optional:

1. **Check for `HF_TOKEN` before promising a result.** If it's unset, tell the
   user plainly that HuggingFace's serverless inference now requires a token,
   point them to https://huggingface.co/settings/tokens to create a free one
   (a `read`-scope token is sufficient), and stop rather than guessing an output.
2. **Never fabricate a classification, embedding, summary, or entity list.**
   If the call fails, report the failure — do not describe what a model would
   probably say.
3. **A working call can still fail per-model.** Some models are gated (require
   accepting a license on the HuggingFace model page even with a valid token)
   or cold (first call after inactivity can 503 — retry once with
   `wait_for_model: true` before concluding a model is broken).

Because no valid `HF_TOKEN` was available while building this skill, the
parameter/response documentation below is **schema-derived** (from the tools'
own `parameter`/`return_schema` definitions), not captured from a successful
live call. The specific biomedical `model_id` values named below are pulled
directly from the tools' own JSON descriptions, which label them
"Verified-live" — that verification was performed by whoever built these
tools, not re-confirmed here. Re-verify with a real `HF_TOKEN` before treating
any specific model's *output quality* as proven; the parameter shapes and
error-handling behavior above ARE independently confirmed live.

## When to Use This Skill

Apply when a task needs a quick, generic ML inference call against a named
(or freely chosen) HuggingFace model rather than a purpose-built ToolUniverse
tool:
- Sentiment/topic/emotion classification of a passage of text
- A dense embedding vector for semantic search or similarity scoring between
  two texts (including PubMed-tuned or protein-sequence embedding models)
- Predicting a masked token — including protein language models like ESM2 for
  amino-acid-position prediction (for actual missense-variant pathogenicity
  scoring, prefer a purpose-built log-likelihood-ratio tool if one exists in
  ToolUniverse rather than raw fill-mask, which only ranks tokens)
- Summarizing a passage with a specific named model
- Classifying text against an arbitrary, caller-supplied set of labels with no
  model retraining (zero-shot)
- Extracting named entities (people, organizations, drugs, diseases — several
  biomedical NER models are directly supported) from a passage
- Extractive question answering against a supplied context passage
- Translating text where the language pair is fixed by the chosen model
- Image classification or object detection against a supplied image URL or
  local file path

**NOT for** (route elsewhere):
- Synthesizing/summarizing a *multi-source literature review* — that's the
  calling model's own reasoning task in `tooluniverse-literature-deep-research`,
  not a single-document `HFInference_summarize` call. Reach for
  `HFInference_summarize` only when the task specifically calls for a named
  external model's summary (e.g. reproducing a paper's own summarization
  benchmark, or batch-summarizing many documents with one consistent model)
- Purpose-built biomedical NLP already covered by a dedicated ToolUniverse
  tool (e.g. a variant-pathogenicity scorer, a dedicated protein-embedding
  tool) — prefer the purpose-built tool; use `HFInference_*` as the fallback
  when no dedicated tool exists for the exact model/task needed
- Training or fine-tuning a model — these tools only call already-hosted
  models for inference

## The 10 Tools

All 10 share the same request shape: `model_id` (required — the HuggingFace
`org/name` repo id; must be the canonical id, not a bare alias, or several of
these return HTTP 400) plus task-specific fields, plus an optional
`wait_for_model` boolean to block through a cold-start instead of getting a
503. All 10 return either the task's result object or `{"error": "..."}` —
always check for `error` before reading the rest.

| Tool | Required params (beyond `model_id`) | Returns |
|---|---|---|
| `HFInference_classify_text` | `text` | `{top_label, labels:[{label,score}]}` |
| `HFInference_embed_text` | `text` | `{dimension, embedding:[float], preview}` |
| `HFInference_fill_mask` | `text` (must contain the model's mask token) | `{top_token, predictions:[{token_str,score,sequence}]}` |
| `HFInference_summarize` | `text` (+ optional `max_length`/`min_length`) | `{summary_text}` |
| `HFInference_zero_shot_classify` | `text`, `candidate_labels` (+ optional `multi_label`) | `{top_label, labels:[{label,score}]}` |
| `HFInference_ner` | `text` | `{entity_count, entities:[{entity_group,word,score,start,end}]}` |
| `HFInference_question_answering` | `question`, `context` | `{answer, score, start, end}` (character offsets into `context`) |
| `HFInference_translate` | `text` (language pair fixed by `model_id`) | `{translation_text}` |
| `HFInference_classify_image` | exactly one of `image_url` / `image_path` | `{top_label, labels:[{label,score}]}` |
| `HFInference_detect_objects` | exactly one of `image_url` / `image_path` | `{object_count, objects:[{label,score,box:{xmin,ymin,xmax,ymax}}]}` |

See `references/hf_inference_tool_reference.md` for the full parameter list
per tool (including every optional field) and the mask-token convention by
model family.

## Choosing a `model_id`

Because these tools call *any* HuggingFace-hosted model, picking the right
`model_id` is the actual skill here — the tool itself is generic. Use the
canonical `org/name` id (e.g. `google-bert/bert-base-uncased`), never a bare
model name. Starting points, taken directly from the tools' own descriptions
(their stated "verified-live" status is the tool author's, not independently
re-confirmed in this session — re-check output quality before relying on it):

- **General sentiment**: `distilbert/distilbert-base-uncased-finetuned-sst-2-english`
  (POSITIVE/NEGATIVE) or `cardiffnlp/twitter-roberta-base-sentiment-latest`
- **General embeddings**: `sentence-transformers/all-MiniLM-L6-v2` (384-dim, fast)
  or `BAAI/bge-small-en-v1.5`
- **Biomedical/literature embeddings**: `NeuML/pubmedbert-base-embeddings` or
  `pritamdeka/S-PubMedBert-MS-MARCO`
- **Biomedical entity normalization embeddings**: `cambridgeltl/SapBERT-from-PubMedBERT-fulltext`
- **Protein embeddings**: `facebook/esm2_t33_650M_UR50D` (or the smaller
  `t30_150M`/`t12_35M`/`t6_8M` variants for speed)
- **Protein masked-LM** (fill-mask on amino-acid sequences, uses `<mask>` not
  `[MASK]`): `facebook/esm2_t6_8M_UR50D` and siblings above
- **Biomedical text masked-LM**: `dmis-lab/biobert-base-cased-v1.2`
- **Clinical text masked-LM**: `emilyalsentzer/Bio_ClinicalBERT`
- **Genomic sequence masked-LM**: `InstaDeepAI/nucleotide-transformer-500m-human-ref`
- **Biomedical NER** (drugs/diseases/dosage/symptoms): `d4data/biomedical-ner-all`
- **Disease-focused NER**: `OpenMed/OpenMed-NER-DiseaseDetect-BioMed-335M`
- **General NER**: `dslim/bert-base-NER` (PER/LOC/ORG/MISC)
- **Summarization**: `facebook/bart-large-cnn` or the lighter `sshleifer/distilbart-cnn-12-6`
- **Zero-shot classification**: `facebook/bart-large-mnli` or the multilingual
  `MoritzLaurer/mDeBERTa-v3-base-mnli-xnli`
- **Extractive QA**: `deepset/roberta-base-squad2`
- **Translation**: `Helsinki-NLP/opus-mt-{src}-{tgt}` (language pair is baked
  into the model name, e.g. `opus-mt-en-fr` for English→French)
- **Image classification**: `google/vit-base-patch16-224` (1000 ImageNet classes)
- **Object detection**: `facebook/detr-resnet-50`

For a purpose-built biomedical missense-variant pathogenicity score, do not
use raw `HFInference_fill_mask` on an ESM2 model — check whether ToolUniverse
already has a dedicated log-likelihood-ratio scoring tool for that (the ESM2
fill-mask description explicitly calls this out) and prefer that instead.

## Workflow

1. **Confirm `HF_TOKEN` is set** before attempting anything — this is the
   single most likely failure mode (see Honesty contract above).
2. **Pick the right tool** for the task (table above) and a canonical
   `model_id` (list above, or a caller-specified one).
3. **Call it once, inspect the response for an `error` key first.** On
   `Unauthorized`, report the token/gating issue plainly rather than retrying
   blindly.
4. **On a cold-model 503, retry once with `wait_for_model: true`** rather than
   concluding the model is unavailable.
5. **Report the tool's actual returned values** — scores, labels, spans,
   boxes — never a description of what the model "probably" returned.

## Finding a model first: HuggingFace Hub search (a different API, no token needed)

`HFInference_*` above *runs* an already-known `model_id`. Three separate tools
search the **HuggingFace Hub** catalog itself (`huggingface.co/api/models` and
`/api/datasets`, not the serverless inference API) to find that `model_id` in
the first place — **live-verified, no `HF_TOKEN` required** for any of the
three, unlike every `HFInference_*` tool above:

| Tool | Purpose | Required params |
|---|---|---|
| `HuggingFace_search_models` | Keyword/task/library search over 500k+ models | `search` (+ optional `limit`, `pipeline_tag`, `library`) |
| `HuggingFace_get_model` | Full metadata (tags, config, license, files) for one known model | `author`, `model_name` (separate fields, not `author/name`) |
| `HuggingFace_search_datasets` | Keyword search over 100k+ datasets | `search` (+ optional `limit`) |

Use single-word or short-phrase queries for `search` — live-tested,
multi-word phrases like `"esm2 protein language model"` return zero results
(the Hub API does substring/token matching, not fuzzy semantic search), while
`"esm2"` alone or `"bert"` with `pipeline_tag`/`library` filters return real
results. Verified live: `search_models({"search": "esm2"})` returns real ESM2
checkpoints (`facebook/esm2_t6_8M_UR50D`, `facebook/esm2_t48_15B_UR50D`, ...)
with real download/like counts; `get_model({"author": "facebook",
"model_name": "esm2_t6_8M_UR50D"})` returns full config including its mask
token convention (`<mask>`, confirmed in `widgetData`); `search_datasets({
"search": "genomics"})` returns real TREC-genomics IR datasets.

**Workflow**: use `HuggingFace_search_models`/`search_datasets` first to find
or confirm a `model_id` (especially to check `pipeline_tag`, `library_name`,
license, and gating status before spending an `HFInference_*` call on it),
then feed that `model_id` into the matching `HFInference_*` tool above to
actually run it.

## An alternative inference platform: Replicate

`Replicate_run_prediction` / `Replicate_get_prediction` call a *different*
hosted-inference platform (replicate.com) rather than HuggingFace's
serverless API — reach for these when a model you need is published on
Replicate but not served by HuggingFace's `hf-inference` provider (Replicate
hosts many image-generation, protein-structure, and audio models that never
appear as `HFInference_*`-compatible endpoints).

- `Replicate_run_prediction`: `input` required; either `model` (`owner/name`,
  latest version) or `version` (a 64-char version hash), not both. Creates
  the prediction and polls up to ~22s; if still running, returns
  `status: "processing"` with an `id` to check later.
- `Replicate_get_prediction`: `prediction_id` required — fetches a
  previously-created prediction's current status/output.

Both **require `REPLICATE_API_TOKEN`** (register at
https://replicate.com/account/api-tokens) — **live-verified**: with no token
set, both fail cleanly with `Tool 'Replicate_run_prediction' requires API
key(s) not set: REPLICATE_API_TOKEN`, before any network call. No token was
available in this environment, so only this key-gating behavior was
confirmed live — a real prediction (e.g. the tool's own `replicate/
hello-world` test example) was not run and its output is not documented
here; do not assume the model/input schema beyond what the tool's own JSON
description states until you've run it with a real token.

## Reference

- `references/hf_inference_tool_reference.md` — full per-tool parameter table
  (every optional field), the live-verified error text for the missing-token
  case, and the mask-token convention (`[MASK]` vs `<mask>`) by model family.
