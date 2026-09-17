# HuggingFace Inference Tool Reference

Source: `src/tooluniverse/data/huggingface_inference_tools.json`, type
`HuggingFaceInferenceTool`, all 10 tools declare `optional_api_keys: ["HF_TOKEN"]`.

## Live status (verified, not assumed)

Tested with no `HF_TOKEN` set, against the exact `model_id` values in each
tool's own `test_examples`: **10/10 tools, every example, fails identically**:

```
$ tu test HFInference_classify_text
✗ example 1  tool returned error: Unauthorized for
  distilbert/distilbert-base-uncased-finetuned-sst-2-english. The model may be
  gated/private; set a valid HF_TOKEN with access.
✗ example 2  tool returned error: Unauthorized for
  cardiffnlp/twitter-roberta-base-sentiment-latest. The model may be
  gated/private; set a valid HF_TOKEN with access.
2/2 test(s) failed.
```

Same `Unauthorized for <model_id>. The model may be gated/private; set a valid
HF_TOKEN with access.` message across `classify_text`, `embed_text`,
`fill_mask`, `summarize`, `zero_shot_classify`, `ner`, `question_answering`,
`translate` — and for the two image tools, a slightly more specific message:

```
Unauthorized for google/vit-base-patch16-224. Serverless image inference now
requires a token: set a valid HF_TOKEN with access.
```

A **dummy/invalid** token produces the exact same error (tested:
`HF_TOKEN=dummy_invalid_token_test`), confirming this needs a real, valid
HuggingFace access token — not just any non-empty string — despite every
tool's own `description` field calling `HF_TOKEN` optional ("raises rate
limits"). Get a free token (read scope is enough) at
https://huggingface.co/settings/tokens.

**Implication**: every parameter/response field below is sourced from the
tools' JSON `parameter`/`return_schema` definitions, not a live successful
response — no valid `HF_TOKEN` was available to obtain one. The response
*shape* (field names/types) is authoritative since the tools declare a strict
`oneOf` return schema; the specific quality of any one model's *output* is
not independently re-verified here.

## Shared conventions across all 10 tools

- `model_id` (string, required on every tool): the canonical HuggingFace
  `org/name` repo id. Several tool descriptions explicitly warn that a bare
  alias (not the full `org/name` form) causes hf-inference to return HTTP 400.
- `wait_for_model` (boolean, optional, default false, present on every tool):
  sends `x-wait-for-model` so a cold model blocks until loaded instead of
  returning 503. Retry once with this set to true before concluding a model
  is broken.
- Every `return_schema` is `oneOf` the task's success shape or
  `{"error": "<string>"}` — always check for `error` first.
- `optional_api_keys: ["HF_TOKEN"]` on every tool — see Live status above for
  why this is required in practice despite the "optional" label.

## Per-tool parameters

### HFInference_classify_text
`text` (string, required). Good for sentiment/emotion/topic/NLI classification.
Returns `{model_id, top_label, labels: [{label, score}]}` sorted high to low.

### HFInference_embed_text
`text` (string, required). Forces the feature-extraction pipeline; token-level
outputs are mean-pooled to one vector so sentence-transformers models return a
raw embedding, not a similarity score. Returns
`{model_id, dimension: int, embedding: [float], preview: [float]}`.

### HFInference_fill_mask
`text` (string, required — must contain the model's own mask token) and
`top_k` (integer, optional, default model-dependent, typically 5). **Mask
token by model family**: `[MASK]` for BERT-family models (e.g.
`google-bert/bert-base-uncased`), `<mask>` for RoBERTa/ESM-family models (e.g.
`facebook/esm2_t6_8M_UR50D`) — using the wrong token for a model family is a
likely silent-failure mode (the model just won't find a mask position to
predict). Returns
`{model_id, top_token, predictions: [{token_str, score, sequence}]}`.

### HFInference_summarize
`text` (string, required), `max_length`/`min_length` (integer, optional, in
tokens, model-dependent default). Returns `{model_id, summary_text}`.

### HFInference_zero_shot_classify
`text` (string, required), `candidate_labels` (array of strings, required,
non-empty), `multi_label` (boolean, optional, default false — when true, each
label is scored independently and probabilities need not sum to 1). Returns
`{model_id, top_label, labels: [{label, score}]}` sorted high to low.

### HFInference_ner
`text` (string, required). Returns
`{model_id, entity_count: int, entities: [{entity_group, word, score, start, end}]}`
— `start`/`end` are character offsets into the input `text`.

### HFInference_question_answering
`question` (string, required), `context` (string, required — must contain the
answer). Returns `{model_id, answer, score, start, end}` — `start`/`end` are
character offsets into `context`.

### HFInference_translate
`text` (string, required). The source→target language pair is fixed by the
chosen `model_id` (e.g. `Helsinki-NLP/opus-mt-en-fr` is English→French only —
there is no separate source/target-language parameter). Returns
`{model_id, translation_text}`.

### HFInference_classify_image
Exactly one of `image_url` (public http(s) URL) or `image_path` (local file)
— required, no `text` field. The tool description states serverless image
inference specifically requires `HF_TOKEN` (not just "raises rate limits"
like the text tools claim — consistent with the live 100%-failure result
above). Returns `{model_id, top_label, labels: [{label, score}]}`.

### HFInference_detect_objects
Same `image_url`/`image_path` requirement as `classify_image`. Returns
`{model_id, object_count: int, objects: [{label, score, box: {xmin, ymin, xmax, ymax}}]}`
— box coordinates are in pixels.

## Recommended biomedical model_ids (from the tools' own descriptions)

These are named directly in the JSON `description` fields, which label them
"Verified-live biomedical model_ids" — that verification was performed by
whoever authored the tool, not independently re-confirmed in this session
(no valid `HF_TOKEN` was available). Re-check output quality before relying
on any one of these for a real analysis:

| Task | model_id | Notes |
|---|---|---|
| Literature/sentence embeddings | `NeuML/pubmedbert-base-embeddings`, `pritamdeka/S-PubMedBert-MS-MARCO` | PubMed-tuned |
| Biomedical entity-normalization embeddings | `cambridgeltl/SapBERT-from-PubMedBERT-fulltext` | |
| Protein embeddings | `facebook/esm2_t33_650M_UR50D` (or smaller `t30_150M`/`t12_35M`/`t6_8M`) | |
| Protein masked-LM (uses `<mask>`) | `facebook/esm2_t6_8M_UR50D` and siblings | For proper missense-variant scoring, prefer a dedicated log-likelihood-ratio tool over raw fill-mask, per the tool's own description |
| Biomedical text masked-LM (uses `[MASK]`) | `dmis-lab/biobert-base-cased-v1.2` | |
| Clinical text masked-LM | `emilyalsentzer/Bio_ClinicalBERT` | |
| Genomic sequence masked-LM | `InstaDeepAI/nucleotide-transformer-500m-human-ref` | |
| Biomedical NER (drugs/diseases/dosage/symptoms) | `d4data/biomedical-ner-all` | |
| Disease-focused NER | `OpenMed/OpenMed-NER-DiseaseDetect-BioMed-335M` | |
