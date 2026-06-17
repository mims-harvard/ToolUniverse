"""HuggingFace serverless Inference API wrapper for ToolUniverse.

A single tool class (``HuggingFaceInferenceTool``) that runs inference on any
model hosted by HuggingFace's serverless ``hf-inference`` provider, exposed as a
few high-value task wrappers:

* ``classify_text``       — text-classification (e.g. sentiment) -> labels + scores
* ``embed_text``          — feature-extraction / embeddings -> a single vector
* ``fill_mask``           — masked-language-model fill-mask -> ranked candidate tokens
                            (works for protein LMs such as ESM-2 too)
* ``summarize``           — summarization -> condensed summary text
* ``zero_shot_classify``  — zero-shot-classification against caller-supplied labels
* ``ner``                 — token-classification / named-entity recognition
* ``question_answering``  — extractive QA over a question + context
* ``translate``           — machine translation -> translated text
* ``classify_image``      — image-classification -> top labels + scores
* ``detect_objects``      — object-detection -> objects with bounding boxes

Endpoint note
-------------
The historical base ``https://api-inference.huggingface.co/models/{id}`` no
longer resolves — HuggingFace migrated serverless inference to the unified
router. This tool targets the current endpoint::

    https://router.huggingface.co/hf-inference/models/{model_id}

For embeddings the request is sent to the explicit feature-extraction
sub-pipeline (``.../{model_id}/pipeline/feature-extraction``) so that
sentence-transformers models — which otherwise default to a
sentence-similarity pipeline — return a raw embedding vector.

Authentication
--------------
An optional bearer token is read from the ``HF_TOKEN`` environment variable
(never a tool parameter). Many models work token-less with stricter rate
limits; a token raises those limits and unlocks gated models.

The tool never raises: every path returns a ``{"status": ...}`` dict. A model
that is still warming up returns HTTP 503; that is surfaced as a clear,
retryable status rather than an exception.
"""

import os
from typing import Any, Dict, List, Optional

import requests

from .base_tool import BaseTool
from .tool_registry import register_tool

_BASE_URL = "https://router.huggingface.co/hf-inference/models"
_TIMEOUT = 30
_MAX_EMBED_PREVIEW = 8  # vector entries shown in the preview field


def _err(msg: str, **extra: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"status": "error", "error": msg}
    out.update(extra)
    return out


def _ok(data: Any, **metadata: Any) -> Dict[str, Any]:
    meta = {"provider": "hf-inference"}
    meta.update(metadata)
    return {"status": "success", "data": data, "metadata": meta}


@register_tool("HuggingFaceInferenceTool")
class HuggingFaceInferenceTool(BaseTool):
    """Run inference on HuggingFace-hosted models (serverless hf-inference)."""

    def __init__(self, tool_config):
        super().__init__(tool_config)
        self.parameter = tool_config.get("parameter", {})

    # ------------------------------------------------------------------ #
    # dispatch
    # ------------------------------------------------------------------ #
    def run(self, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        arguments = arguments or {}
        operation = arguments.get("operation")
        handlers = {
            "classify_text": self._classify_text,
            "embed_text": self._embed_text,
            "fill_mask": self._fill_mask,
            "summarize": self._summarize,
            "zero_shot_classify": self._zero_shot_classify,
            "ner": self._ner,
            "question_answering": self._question_answering,
            "translate": self._translate,
            "classify_image": self._classify_image,
            "detect_objects": self._detect_objects,
        }
        handler = handlers.get(operation)
        if handler is None:
            return _err(
                f"Unknown or missing operation: {operation!r}. "
                f"Expected one of {sorted(handlers)}."
            )
        try:
            return handler(arguments)
        except Exception as exc:  # never raise out of run()
            return _err(f"Unexpected error: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------------ #
    # shared input validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _require_text_and_model(args: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Return an error dict if text/model_id are missing, else None."""
        text = args.get("text")
        if not text or not str(text).strip():
            return _err("Missing required parameter: text")
        if not args.get("model_id"):
            return _err("Missing required parameter: model_id")
        return None

    def _post_text(
        self, args: Dict[str, Any], payload: Dict[str, Any], path_suffix: str = ""
    ) -> Dict[str, Any]:
        """Validate text+model, POST, and unwrap the router response.

        Returns ``{"_json": <body>}`` on success or a ready-made
        ``{"status": "error"|"loading", ...}`` dict on any failure — the same
        shape callers already branch on via the ``"_json"`` key.
        """
        invalid = self._require_text_and_model(args)
        if invalid is not None:
            return invalid
        return self._post(
            args.get("model_id"),
            payload,
            wait_for_model=bool(args.get("wait_for_model", False)),
            path_suffix=path_suffix,
        )

    # ------------------------------------------------------------------ #
    # shared HTTP helper
    # ------------------------------------------------------------------ #
    def _post(
        self,
        model_id: str,
        payload: Dict[str, Any],
        wait_for_model: bool,
        path_suffix: str = "",
    ) -> Dict[str, Any]:
        """POST to the inference router.

        Returns either ``{"_json": <decoded body>}`` on success or a ready-made
        ``{"status": "error"|"loading", ...}`` dict on any failure.
        """
        url = f"{_BASE_URL}/{model_id.strip('/')}{path_suffix}"
        headers = {"Content-Type": "application/json"}
        token = os.environ.get("HF_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if wait_for_model:
            # HF holds the request open until the model finishes loading.
            headers["x-wait-for-model"] = "true"

        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=_TIMEOUT)
        except requests.exceptions.Timeout:
            return _err(
                f"Timeout after {_TIMEOUT}s contacting {model_id}. The model may "
                "be loading — retry, optionally with wait_for_model=true."
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Network error contacting {model_id}: {exc}")

        # Text POSTs use a gated/private-specific 401 message; all other
        # status handling is shared with image POSTs via _interpret_status.
        if resp.status_code == 401:
            return _err(
                f"Unauthorized for {model_id}. The model may be gated/private; "
                "set a valid HF_TOKEN with access."
            )
        return self._interpret_status(resp, model_id)

    # ------------------------------------------------------------------ #
    # shared image input helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _content_type_for(source: str, default: str = "image/jpeg") -> str:
        """Guess an image Content-Type from a URL or file path extension."""
        ext = os.path.splitext(source.split("?")[0])[1].lower()
        return {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".bmp": "image/bmp",
            ".webp": "image/webp",
            ".tif": "image/tiff",
            ".tiff": "image/tiff",
        }.get(ext, default)

    def _load_image_bytes(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve image bytes from image_url or image_path.

        Returns ``{"_bytes": <data>, "_content_type": <ct>}`` on success or a
        ready-made ``{"status": "error", ...}`` dict on any failure.
        """
        image_url = args.get("image_url")
        image_path = args.get("image_path")
        if not image_url and not image_path:
            return _err(
                "Missing image input: provide exactly one of image_url "
                "(a public http(s) URL) or image_path (a local file path)."
            )
        if image_url and image_path:
            return _err("Provide only one of image_url or image_path, not both.")

        if image_path:
            try:
                with open(image_path, "rb") as fh:
                    data = fh.read()
            except OSError as exc:
                return _err(f"Could not read image_path {image_path!r}: {exc}")
            if not data:
                return _err(f"Image file is empty: {image_path}")
            return {
                "_bytes": data,
                "_content_type": self._content_type_for(image_path),
            }

        # image_url
        try:
            resp = requests.get(image_url, timeout=_TIMEOUT)
        except requests.exceptions.Timeout:
            return _err(f"Timeout after {_TIMEOUT}s fetching image_url {image_url}.")
        except requests.exceptions.RequestException as exc:
            return _err(f"Could not fetch image_url {image_url}: {exc}")
        if resp.status_code != 200:
            return _err(
                f"HTTP {resp.status_code} fetching image_url {image_url}. "
                "Ensure it is a public, directly-downloadable image."
            )
        if not resp.content:
            return _err(f"Empty image body from image_url {image_url}.")
        ct = resp.headers.get("content-type", "").split(";")[0].strip()
        if not ct.startswith("image/"):
            ct = self._content_type_for(image_url)
        return {"_bytes": resp.content, "_content_type": ct}

    def _post_image(self, model_id: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate model + load image, then POST the raw image bytes.

        Image models expect the binary image as the request body with the
        image's Content-Type (not JSON). Returns ``{"_json": <body>}`` on
        success or a ready-made ``{"status": ...}`` dict on any failure.
        """
        if not model_id:
            return _err("Missing required parameter: model_id")
        loaded = self._load_image_bytes(args)
        if "_bytes" not in loaded:
            return loaded  # error dict

        url = f"{_BASE_URL}/{model_id.strip('/')}"
        headers = {"Content-Type": loaded["_content_type"]}
        token = os.environ.get("HF_TOKEN", "")
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if bool(args.get("wait_for_model", False)):
            headers["x-wait-for-model"] = "true"

        try:
            resp = requests.post(
                url, data=loaded["_bytes"], headers=headers, timeout=_TIMEOUT
            )
        except requests.exceptions.Timeout:
            return _err(
                f"Timeout after {_TIMEOUT}s contacting {model_id}. The image "
                "model may be loading — retry, optionally with "
                "wait_for_model=true."
            )
        except requests.exceptions.RequestException as exc:
            return _err(f"Network error contacting {model_id}: {exc}")

        return self._interpret_status(resp, model_id)

    def _interpret_status(self, resp, model_id: str) -> Dict[str, Any]:
        """Map an HTTP response to ``{"_json": ...}`` or a status dict.

        Shared status handling for both JSON and image POSTs (503 loading,
        401/404/429, other non-200, and non-JSON bodies).
        """
        if resp.status_code == 503:
            est = None
            try:
                est = resp.json().get("estimated_time")
            except Exception:
                pass
            return {
                "status": "loading",
                "error": (
                    f"Model {model_id} is loading on the HF inference servers"
                    + (
                        f" (~{est:.0f}s estimated)"
                        if isinstance(est, (int, float))
                        else ""
                    )
                    + ". Retry shortly, or pass wait_for_model=true to block "
                    "until it is ready."
                ),
                "estimated_time": est,
            }
        if resp.status_code == 401:
            return _err(
                f"Unauthorized for {model_id}. Serverless image inference now "
                "requires a token: set a valid HF_TOKEN with access."
            )
        if resp.status_code == 404:
            return _err(
                f"Model not found: {model_id}. Check the exact repo id "
                "(e.g. 'org/name')."
            )
        if resp.status_code == 429:
            return _err(
                f"Rate limited for {model_id}. Set HF_TOKEN to raise free-tier "
                "limits, or retry later."
            )
        if resp.status_code != 200:
            detail = ""
            try:
                body = resp.json()
                detail = body.get("error") or str(body)
            except Exception:
                detail = resp.text[:300]
            return _err(f"HTTP {resp.status_code} from {model_id}: {detail}")
        try:
            return {"_json": resp.json()}
        except ValueError:
            return _err(f"Non-JSON response from {model_id}: {resp.text[:200]}")

    # ------------------------------------------------------------------ #
    # shared label-classification parsing
    # ------------------------------------------------------------------ #
    @staticmethod
    def _parse_labels(body: Any) -> Optional[List[Dict[str, Any]]]:
        """Parse a (text|image)-classification body into sorted label dicts.

        Both tasks return ``[{label, score}, ...]`` or, batched, a nested
        ``[[{label, score}, ...]]``. Returns the score-descending label list,
        or ``None`` if the body is not a list of records.
        """
        labels = (
            body[0]
            if (isinstance(body, list) and body and isinstance(body[0], list))
            else body
        )
        if not isinstance(labels, list):
            return None
        return sorted(
            (
                {"label": d.get("label"), "score": d.get("score")}
                for d in labels
                if isinstance(d, dict)
            ),
            key=lambda d: d["score"] if d["score"] is not None else -1.0,
            reverse=True,
        )

    # ------------------------------------------------------------------ #
    # text-classification
    # ------------------------------------------------------------------ #
    def _classify_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        result = self._post_text(args, {"inputs": args.get("text")})
        if "_json" not in result:
            return result  # error / loading dict
        body = result["_json"]

        labels = self._parse_labels(body)
        if labels is None:
            return _err(f"Unexpected classification response: {str(body)[:200]}")
        top = labels[0]["label"] if labels else None
        return _ok(
            {"model_id": model_id, "top_label": top, "labels": labels},
            task="text-classification",
        )

    # ------------------------------------------------------------------ #
    # feature-extraction / embeddings
    # ------------------------------------------------------------------ #
    def _embed_text(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")

        # Force the feature-extraction pipeline so sentence-transformers models
        # return a raw vector instead of routing to sentence-similarity.
        result = self._post_text(
            args,
            {"inputs": args.get("text")},
            path_suffix="/pipeline/feature-extraction",
        )
        if "_json" not in result:
            return result
        body = result["_json"]

        vector = self._flatten_embedding(body)
        if vector is None:
            return _err(
                f"Could not parse embedding from response for {model_id}: "
                f"{str(body)[:200]}"
            )
        return _ok(
            {
                "model_id": model_id,
                "dimension": len(vector),
                "embedding": vector,
                "preview": vector[:_MAX_EMBED_PREVIEW],
            },
            task="feature-extraction",
        )

    @staticmethod
    def _flatten_embedding(body: Any) -> Optional[List[float]]:
        """Reduce an HF feature-extraction response to one 1-D vector.

        Responses may be ``[float, ...]`` (already pooled), ``[[float, ...]]``
        (batch of one), or token-level ``[[[float, ...], ...]]`` which is
        mean-pooled over the token axis.
        """
        if not isinstance(body, list) or not body:
            return None
        first = body[0]

        # Already a flat vector of numbers.
        if isinstance(first, (int, float)):
            return [float(x) for x in body]

        # Batch of one: [[...]]
        if isinstance(first, list) and first and isinstance(first[0], (int, float)):
            return [float(x) for x in first]

        # Token-level: [[[...], [...], ...]] -> mean-pool tokens.
        if isinstance(first, list) and first and isinstance(first[0], list):
            tokens = first  # tokens of the single input
            num = [t for t in tokens if isinstance(t, list) and t]
            if not num:
                return None
            dim = len(num[0])
            pooled = [0.0] * dim
            for tok in num:
                for i in range(dim):
                    pooled[i] += float(tok[i])
            return [v / len(num) for v in pooled]

        return None

    # ------------------------------------------------------------------ #
    # fill-mask
    # ------------------------------------------------------------------ #
    def _fill_mask(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        top_k = args.get("top_k")

        payload: Dict[str, Any] = {"inputs": args.get("text")}
        if isinstance(top_k, int) and top_k > 0:
            payload["parameters"] = {"top_k": top_k}

        result = self._post_text(args, payload)
        if "_json" not in result:
            return result
        body = result["_json"]

        # fill-mask returns [{score, token, token_str, sequence}, ...]; with
        # multiple masks it nests one list per mask.
        if isinstance(body, list) and body and isinstance(body[0], list):
            body = body[0]
        if not isinstance(body, list):
            return _err(f"Unexpected fill-mask response: {str(body)[:200]}")

        predictions = [
            {
                "token_str": (d.get("token_str") or "").strip(),
                "score": d.get("score"),
                "sequence": d.get("sequence"),
            }
            for d in body
            if isinstance(d, dict)
        ]
        if not predictions:
            return _err(
                f"No predictions returned for {model_id}. Ensure the input "
                "contains the model's mask token (e.g. [MASK] for BERT, "
                "<mask> for RoBERTa/ESM)."
            )
        return _ok(
            {
                "model_id": model_id,
                "top_token": predictions[0]["token_str"],
                "predictions": predictions,
            },
            task="fill-mask",
        )

    # ------------------------------------------------------------------ #
    # summarization
    # ------------------------------------------------------------------ #
    def _summarize(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")

        parameters: Dict[str, Any] = {}
        max_length = args.get("max_length")
        min_length = args.get("min_length")
        if isinstance(max_length, int) and max_length > 0:
            parameters["max_length"] = max_length
        if isinstance(min_length, int) and min_length > 0:
            parameters["min_length"] = min_length

        payload: Dict[str, Any] = {"inputs": args.get("text")}
        if parameters:
            payload["parameters"] = parameters

        result = self._post_text(args, payload)
        if "_json" not in result:
            return result
        body = result["_json"]

        # summarization returns [{"summary_text": "..."}].
        item = body[0] if isinstance(body, list) and body else body
        summary = item.get("summary_text") if isinstance(item, dict) else None
        if not summary:
            return _err(f"Unexpected summarization response: {str(body)[:200]}")
        return _ok(
            {"model_id": model_id, "summary_text": summary},
            task="summarization",
        )

    # ------------------------------------------------------------------ #
    # zero-shot-classification
    # ------------------------------------------------------------------ #
    def _zero_shot_classify(self, args: Dict[str, Any]) -> Dict[str, Any]:
        invalid = self._require_text_and_model(args)
        if invalid is not None:
            return invalid
        model_id = args.get("model_id")
        candidate_labels = args.get("candidate_labels")

        if not isinstance(candidate_labels, list) or not candidate_labels:
            return _err(
                "Missing required parameter: candidate_labels (a non-empty list "
                "of strings to classify the text against)."
            )
        labels_in = [str(label) for label in candidate_labels]

        parameters: Dict[str, Any] = {"candidate_labels": labels_in}
        if args.get("multi_label") is not None:
            parameters["multi_label"] = bool(args.get("multi_label"))

        result = self._post_text(
            args, {"inputs": args.get("text"), "parameters": parameters}
        )
        if "_json" not in result:
            return result
        body = result["_json"]

        # The router returns either a flat sorted [{"label","score"}, ...] list
        # or the classic {"labels":[...], "scores":[...]} dict — normalise both.
        labels: List[Dict[str, Any]] = []
        if isinstance(body, list):
            labels = [
                {"label": d.get("label"), "score": d.get("score")}
                for d in body
                if isinstance(d, dict)
            ]
        elif isinstance(body, dict):
            names = body.get("labels")
            scores = body.get("scores")
            if isinstance(names, list) and isinstance(scores, list):
                labels = [{"label": n, "score": s} for n, s in zip(names, scores)]
        if not labels:
            return _err(
                f"Unexpected zero-shot response from {model_id}: {str(body)[:200]}"
            )

        labels = sorted(
            labels,
            key=lambda d: d["score"] if d["score"] is not None else -1.0,
            reverse=True,
        )
        return _ok(
            {
                "model_id": model_id,
                "top_label": labels[0]["label"],
                "labels": labels,
            },
            task="zero-shot-classification",
        )

    # ------------------------------------------------------------------ #
    # token-classification / NER
    # ------------------------------------------------------------------ #
    def _ner(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        result = self._post_text(args, {"inputs": args.get("text")})
        if "_json" not in result:
            return result
        body = result["_json"]

        # token-classification returns [{entity_group|entity, score, word,
        # start, end}, ...]; with batching it may nest one list per input.
        if isinstance(body, list) and body and isinstance(body[0], list):
            body = body[0]
        if not isinstance(body, list):
            return _err(f"Unexpected NER response: {str(body)[:200]}")

        entities = [
            {
                "entity_group": d.get("entity_group") or d.get("entity"),
                "word": d.get("word"),
                "score": d.get("score"),
                "start": d.get("start"),
                "end": d.get("end"),
            }
            for d in body
            if isinstance(d, dict)
        ]
        return _ok(
            {
                "model_id": model_id,
                "entity_count": len(entities),
                "entities": entities,
            },
            task="token-classification",
        )

    # ------------------------------------------------------------------ #
    # extractive question-answering
    # ------------------------------------------------------------------ #
    def _question_answering(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        question = args.get("question")
        context = args.get("context")
        if not model_id:
            return _err("Missing required parameter: model_id")
        if not question or not str(question).strip():
            return _err("Missing required parameter: question")
        if not context or not str(context).strip():
            return _err("Missing required parameter: context")

        result = self._post(
            model_id,
            {"inputs": {"question": question, "context": context}},
            wait_for_model=bool(args.get("wait_for_model", False)),
        )
        if "_json" not in result:
            return result
        body = result["_json"]

        # QA returns a single {"answer","score","start","end"} object (or a
        # one-element list of the same).
        item = body[0] if isinstance(body, list) and body else body
        if not isinstance(item, dict) or "answer" not in item:
            return _err(f"Unexpected QA response from {model_id}: {str(body)[:200]}")
        return _ok(
            {
                "model_id": model_id,
                "answer": item.get("answer"),
                "score": item.get("score"),
                "start": item.get("start"),
                "end": item.get("end"),
            },
            task="question-answering",
        )

    # ------------------------------------------------------------------ #
    # translation
    # ------------------------------------------------------------------ #
    def _translate(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        result = self._post_text(args, {"inputs": args.get("text")})
        if "_json" not in result:
            return result
        body = result["_json"]

        # translation returns [{"translation_text": "..."}].
        item = body[0] if isinstance(body, list) and body else body
        translation = item.get("translation_text") if isinstance(item, dict) else None
        if not translation:
            return _err(f"Unexpected translation response: {str(body)[:200]}")
        return _ok(
            {"model_id": model_id, "translation_text": translation},
            task="translation",
        )

    # ------------------------------------------------------------------ #
    # image-classification
    # ------------------------------------------------------------------ #
    def _classify_image(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        result = self._post_image(model_id, args)
        if "_json" not in result:
            return result  # error / loading dict
        body = result["_json"]

        labels = self._parse_labels(body)
        if labels is None:
            return _err(f"Unexpected image-classification response: {str(body)[:200]}")
        top = labels[0]["label"] if labels else None
        return _ok(
            {"model_id": model_id, "top_label": top, "labels": labels},
            task="image-classification",
        )

    # ------------------------------------------------------------------ #
    # object-detection
    # ------------------------------------------------------------------ #
    def _detect_objects(self, args: Dict[str, Any]) -> Dict[str, Any]:
        model_id = args.get("model_id")
        result = self._post_image(model_id, args)
        if "_json" not in result:
            return result  # error / loading dict
        body = result["_json"]

        # object-detection returns [{score, label, box:{xmin,ymin,xmax,ymax}},
        # ...]; with batching it may nest one list per input.
        if isinstance(body, list) and body and isinstance(body[0], list):
            body = body[0]
        if not isinstance(body, list):
            return _err(f"Unexpected object-detection response: {str(body)[:200]}")

        objects = []
        for d in body:
            if not isinstance(d, dict):
                continue
            box = d.get("box") if isinstance(d.get("box"), dict) else {}
            objects.append(
                {
                    "label": d.get("label"),
                    "score": d.get("score"),
                    "box": {
                        "xmin": box.get("xmin"),
                        "ymin": box.get("ymin"),
                        "xmax": box.get("xmax"),
                        "ymax": box.get("ymax"),
                    },
                }
            )
        objects.sort(
            key=lambda o: o["score"] if o["score"] is not None else -1.0,
            reverse=True,
        )
        return _ok(
            {
                "model_id": model_id,
                "object_count": len(objects),
                "objects": objects,
            },
            task="object-detection",
        )
