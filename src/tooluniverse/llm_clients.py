from __future__ import annotations
from typing import Any, Dict, List, Optional
import os
import re
import time
import json as _json


def _model_family(model_id: str) -> str:
    """Return the provider-independent model portion of a model ID."""
    if not isinstance(model_id, str):
        return ""
    return model_id.rsplit("/", 1)[-1].lower()


def is_reasoning_model(model_id: str) -> bool:
    """True for OpenAI "reasoning" model families (o1/o3/o4/gpt-5 and their
    variants, e.g. "o4-mini", "gpt-5-mini"). These models only support the
    default temperature (reject any explicit value with a 400 error) and
    take `max_completion_tokens` instead of `max_tokens`. Single source of
    truth for both restrictions so the two checks can't drift out of sync
    the way they previously did (temperature normalization was missing
    "gpt-5" even though token-limit routing already had it).
    """
    return _model_family(model_id).startswith(("gpt-5", "o1", "o3", "o4"))


class BaseLLMClient:
    def test_api(self) -> None:
        raise NotImplementedError

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        raise NotImplementedError

    def infer_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ):
        """Default streaming implementation falls back to regular inference."""
        result = self.infer(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            return_json=return_json,
            custom_format=custom_format,
            max_retries=max_retries,
            retry_delay=retry_delay,
        )
        if result is not None:
            yield result


class AzureOpenAIClient(BaseLLMClient):
    # Built-in defaults for model families (can be overridden by env)
    DEFAULT_MODEL_LIMITS: Dict[str, Dict[str, int]] = {
        # GPT-4.1 series
        "gpt-4.1": {"max_output": 32768, "context_window": 1_047_576},
        "gpt-4.1-mini": {"max_output": 32768, "context_window": 1_047_576},
        "gpt-4.1-nano": {"max_output": 32768, "context_window": 1_047_576},
        # GPT-4o series
        "gpt-4o-1120": {"max_output": 16384, "context_window": 128_000},
        "gpt-4o-0806": {"max_output": 16384, "context_window": 128_000},
        "gpt-4o-mini-0718": {"max_output": 16384, "context_window": 128_000},
        "gpt-4o": {"max_output": 16384, "context_window": 128_000},  # general prefix
        # O-series
        "o4-mini-0416": {"max_output": 100_000, "context_window": 200_000},
        "o3-mini-0131": {"max_output": 100_000, "context_window": 200_000},
        "o4-mini": {"max_output": 100_000, "context_window": 200_000},
        "o3-mini": {"max_output": 100_000, "context_window": 200_000},
        # Embeddings (for completeness)
        "embedding-ada": {"max_output": 8192, "context_window": 8192},
        "text-embedding-3-small": {"max_output": 8192, "context_window": 8192},
        "text-embedding-3-large": {"max_output": 8192, "context_window": 8192},
    }

    def __init__(self, model_id: str, api_version: Optional[str], logger):
        try:
            from openai import AzureOpenAI as _AzureOpenAI  # type: ignore
            import openai as _openai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("openai AzureOpenAI client is not available") from e
        self._AzureOpenAI = _AzureOpenAI
        self._openai = _openai

        self.model_name = model_id
        self.logger = logger

        resolved_version = api_version or self._resolve_api_version(model_id)
        self.logger.debug(
            f"Resolved Azure API version for {model_id}: {resolved_version}"
        )

        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        if not api_key:
            raise ValueError("AZURE_OPENAI_API_KEY not set")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "https://azure-ai.hms.edu")
        self.client = self._AzureOpenAI(
            azure_endpoint=endpoint, api_key=api_key, api_version=resolved_version
        )
        self.api_version = resolved_version

        # Load env overrides for model limits (JSON dict of {prefix: {max_output, context_window}})
        env_limits_raw = os.getenv("AZURE_DEFAULT_MODEL_LIMITS")
        self._default_limits: Dict[str, Dict[str, int]] = (
            self.DEFAULT_MODEL_LIMITS.copy()
        )
        if env_limits_raw:
            try:
                env_limits = _json.loads(env_limits_raw)
                # shallow merge by keys
                for k, v in env_limits.items():
                    if isinstance(v, dict):
                        base = self._default_limits.get(k, {}).copy()
                        base.update(
                            {
                                kk: int(vv)
                                for kk, vv in v.items()
                                if isinstance(vv, (int, float, str))
                            }
                        )
                        self._default_limits[k] = base
            except Exception:
                # ignore bad env format
                pass

    # --------- helpers (Azure specific) ---------
    def _resolve_api_version(self, model_id: str) -> str:
        mapping_raw = os.getenv("AZURE_OPENAI_API_VERSION_BY_MODEL")
        mapping: Dict[str, str] = {}
        if mapping_raw:
            try:
                mapping = _json.loads(mapping_raw)
            except Exception:
                mapping = {}
        if model_id in mapping:
            return mapping[model_id]
        for k, v in mapping.items():
            try:
                if model_id.startswith(k):
                    return v
            except Exception:
                continue
        try:
            if model_id.startswith("o3-mini") or model_id.startswith("o4-mini"):
                return "2024-12-01-preview"
        except Exception:
            pass
        return os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")

    def _resolve_default_max_tokens(self, model_id: str) -> Optional[int]:
        # Highest priority: explicit env per-model tokens mapping
        mapping_raw = os.getenv("AZURE_MAX_TOKENS_BY_MODEL")
        mapping: Dict[str, Any] = {}
        if mapping_raw:
            try:
                mapping = _json.loads(mapping_raw)
            except Exception:
                mapping = {}
        if model_id in mapping:
            try:
                return int(mapping[model_id])
            except Exception:
                pass
        for k, v in mapping.items():
            try:
                if model_id.startswith(k):
                    return int(v)
            except Exception:
                continue
        # Next: built-in/default-limits map (with env merged)
        if model_id in self._default_limits:
            return int(self._default_limits[model_id].get("max_output", 0)) or None
        for k, v in self._default_limits.items():
            try:
                if model_id.startswith(k):
                    return int(v.get("max_output", 0)) or None
            except Exception:
                continue
        return None

    def _normalize_temperature(
        self, model_id: str, temperature: Optional[float]
    ) -> Optional[float]:
        # Reasoning-style models (o-series and gpt-5 family) only support
        # the default temperature (1) and reject any explicit value with a
        # 400 error. self._model_id defaults to "gpt-5" (see AgenticTool),
        # so is_reasoning_model() previously missing "gpt-5" meant this
        # fired on every default-configured Azure call.
        if is_reasoning_model(model_id):
            if temperature is not None:
                self.logger.warning(
                    f"Model {model_id} does not support 'temperature'; ignoring provided value."
                )
            return None
        return temperature

    # --------- public API ---------
    def test_api(self) -> None:
        test_messages = [{"role": "user", "content": "ping"}]
        token_attempts = [1, 4, 16, 32]
        last_error: Optional[Exception] = None
        for tok in token_attempts:
            try:
                try:
                    self.client.chat.completions.create(
                        model=self.model_name,
                        messages=test_messages,
                        max_tokens=tok,
                        temperature=0,
                    )
                    return
                except self._openai.BadRequestError:  # type: ignore[attr-defined]
                    self.client.chat.completions.create(
                        model=self.model_name,
                        messages=test_messages,
                        max_completion_tokens=tok,
                    )
                    return
            except Exception as e:  # noqa: BLE001
                last_error = e
                msg = str(e).lower()
                if (
                    "max_tokens" in msg
                    or "model output limit" in msg
                    or "finish the message" in msg
                ) and tok != token_attempts[-1]:
                    continue
                break
        if last_error:
            raise ValueError(f"ChatGPT API test failed: {last_error}")
        raise ValueError("ChatGPT API test failed: unknown error")

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        retries = 0
        call_fn = (
            self.client.chat.completions.parse
            if custom_format is not None
            else self.client.chat.completions.create
        )
        response_format = (
            custom_format
            if custom_format is not None
            else ({"type": "json_object"} if return_json else None)
        )
        eff_temp = self._normalize_temperature(self.model_name, temperature)
        eff_max = (
            max_tokens
            if max_tokens is not None
            else self._resolve_default_max_tokens(self.model_name)
        )
        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if eff_temp is not None:
                    kwargs["temperature"] = eff_temp
                try:
                    if eff_max is not None:
                        resp = call_fn(max_tokens=eff_max, **kwargs)
                    else:
                        resp = call_fn(**kwargs)
                except self._openai.BadRequestError as be:  # type: ignore[attr-defined]
                    if eff_max is not None:
                        resp = call_fn(max_completion_tokens=eff_max, **kwargs)
                    else:
                        be_msg = str(be).lower()
                        fallback_limits = [
                            8192,
                            4096,
                            2048,
                            1024,
                            512,
                            256,
                            128,
                            64,
                            32,
                        ]
                        if any(
                            k in be_msg
                            for k in [
                                "max_tokens",
                                "output limit",
                                "finish the message",
                                "max_completion_tokens",
                            ]
                        ):
                            last_exc: Optional[Exception] = be
                            for lim in fallback_limits:
                                try:
                                    try:
                                        resp = call_fn(
                                            max_completion_tokens=lim, **kwargs
                                        )
                                        last_exc = None
                                        break
                                    except Exception as inner_e:  # noqa: BLE001
                                        last_exc = inner_e
                                        resp = call_fn(max_tokens=lim, **kwargs)
                                        last_exc = None
                                        break
                                except Exception as inner2:  # noqa: BLE001
                                    last_exc = inner2
                                    continue
                            if last_exc is not None:
                                raise last_exc
                        else:
                            raise be
                if custom_format is not None:
                    return resp.choices[0].message.parsed.model_dump()
                return resp.choices[0].message.content
            except self._openai.RateLimitError:  # type: ignore[attr-defined]
                self.logger.warning(
                    f"Rate limit exceeded. Retrying in {retry_delay} seconds..."
                )
                retries += 1
                time.sleep(retry_delay * retries)
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"An error occurred: {e}")
                import traceback

                traceback.print_exc()
                break
        self.logger.error("Max retries exceeded. Unable to complete the request.")
        return None

    def infer_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ):
        if return_json or custom_format is not None:
            yield from super().infer_stream(
                messages,
                temperature,
                max_tokens,
                return_json,
                custom_format,
                max_retries,
                retry_delay,
            )
            return

        retries = 0
        eff_temp = self._normalize_temperature(self.model_name, temperature)
        eff_max = (
            max_tokens
            if max_tokens is not None
            else self._resolve_default_max_tokens(self.model_name)
        )

        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": True,
                }
                if eff_temp is not None:
                    kwargs["temperature"] = eff_temp
                if eff_max is not None:
                    kwargs["max_tokens"] = eff_max

                stream = self.client.chat.completions.create(**kwargs)
                for chunk in stream:
                    text = self._extract_text_from_chunk(chunk)
                    if text:
                        yield text
                return
            except self._openai.RateLimitError:  # type: ignore[attr-defined]
                self.logger.warning(
                    f"Rate limit exceeded. Retrying in {retry_delay} seconds (streaming)..."
                )
                retries += 1
                time.sleep(retry_delay * retries)
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Streaming error: {e}")
                break

        # Fallback to non-streaming if streaming fails
        yield from super().infer_stream(
            messages,
            temperature,
            max_tokens,
            return_json,
            custom_format,
            max_retries,
            retry_delay,
        )


class GeminiClient(BaseLLMClient):
    def __init__(self, model_name: str, logger):
        try:
            from google import genai  # type: ignore
            from google.genai import types as genai_types  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("google-genai not available") from e
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found")
        self._client = genai.Client(api_key=api_key)
        self._types = genai_types
        self.model_name = model_name
        self.logger = logger

    def _accepts_sampling_parameters(self) -> bool:
        """Return whether this model accepts legacy sampling parameters.

        Gemini 3.6 Flash, Gemini 3.5 Flash-Lite, moving latest aliases,
        and later model generations must use their server defaults.
        """
        model_name = self.model_name.lower().removeprefix("models/")
        if model_name.endswith("-latest") or model_name.startswith(
            "gemini-3.5-flash-lite"
        ):
            return False

        version = re.match(r"gemini-(\d+)(?:\.(\d+))?", model_name)
        if version is None:
            return True
        major = int(version.group(1))
        minor = int(version.group(2) or 0)
        return (major, minor) < (3, 6)

    def _build_config(
        self,
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool = False,
        custom_format: Any = None,
    ):
        kwargs: Dict[str, Any] = {}
        if self._accepts_sampling_parameters():
            kwargs["temperature"] = temperature if temperature is not None else 0
        if max_tokens is not None:
            kwargs["max_output_tokens"] = max_tokens
        if return_json or custom_format is not None:
            kwargs["response_mime_type"] = "application/json"
            if custom_format is not None:
                kwargs["response_schema"] = custom_format
        return self._types.GenerateContentConfig(**kwargs)

    def test_api(self) -> None:
        self._client.models.generate_content(
            model=self.model_name,
            contents="ping",
            config=self._build_config(temperature=0, max_tokens=8),
        )

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        """Run one Gemini completion.

        Return type follows the same contract as the OpenAI-backed clients:

        - ``custom_format`` set: returns the parsed object as a dict, matching
          ``AzureOpenAIClient.infer``. google-genai populates ``response.parsed``
          when ``response_schema`` is set, so the schema case is a structured
          object on both backends and switching models does not change the
          shape callers index into.
        - ``return_json`` set without ``custom_format``: returns the raw JSON
          text. OpenAI asks for ``{"type": "json_object"}`` and returns content;
          this client sets ``response_mime_type`` and returns text. Both hand
          back an unparsed JSON string.
        - Neither set: returns the plain text response.
        """
        contents = ""
        for m in messages:
            if m["role"] in ("user", "system"):
                contents += f"{m['content']}\n"
        retries = 0
        while retries < max_retries:
            try:
                resp = self._client.models.generate_content(
                    model=self.model_name,
                    contents=contents,
                    config=self._build_config(
                        temperature,
                        max_tokens,
                        return_json=return_json,
                        custom_format=custom_format,
                    ),
                )
                if (
                    custom_format is not None
                    and getattr(resp, "parsed", None) is not None
                ):
                    parsed = resp.parsed
                    return (
                        parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
                    )
                return self._extract_text_from_stream_chunk(resp)
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Gemini error: {e}")
                retries += 1
                time.sleep(retry_delay * retries)
        return None

    @staticmethod
    def _extract_text_from_stream_chunk(chunk) -> Optional[str]:
        if chunk is None:
            return None

        candidates = getattr(chunk, "candidates", None)
        if candidates is None and isinstance(chunk, dict):
            candidates = chunk.get("candidates")
        if not candidates:
            text = (
                chunk.get("text")
                if isinstance(chunk, dict)
                else getattr(chunk, "text", None)
            )
            return text or None

        candidate = candidates[0]
        content = getattr(candidate, "content", None)
        if content is None and isinstance(candidate, dict):
            content = candidate.get("content")
        if not content:
            return None

        parts = getattr(content, "parts", None)
        if parts is None and isinstance(content, dict):
            parts = content.get("parts")
        if parts and isinstance(parts, list):
            fragments: List[str] = []
            for part in parts:
                piece = getattr(part, "text", None)
                if piece is None and isinstance(part, dict):
                    piece = part.get("text")
                if piece:
                    fragments.append(piece)
            return "".join(fragments) if fragments else None

        final_text = getattr(content, "text", None)
        if final_text is None and isinstance(content, dict):
            final_text = content.get("text")
        return final_text

    def infer_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ):
        if custom_format is not None:
            yield from super().infer_stream(
                messages,
                temperature,
                max_tokens,
                return_json,
                custom_format,
                max_retries,
                retry_delay,
            )
            return

        contents = ""
        for m in messages:
            if m["role"] in ("user", "system"):
                contents += f"{m['content']}\n"

        retries = 0
        while retries < max_retries:
            try:
                stream = self._client.models.generate_content_stream(
                    model=self.model_name,
                    contents=contents,
                    config=self._build_config(
                        temperature,
                        max_tokens,
                        return_json=return_json,
                        custom_format=custom_format,
                    ),
                )
                for chunk in stream:
                    text = self._extract_text_from_stream_chunk(chunk)
                    if text:
                        yield text
                return
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"Gemini streaming error: {e}")
                retries += 1
                time.sleep(retry_delay * retries)

        yield from super().infer_stream(
            messages,
            temperature,
            max_tokens,
            return_json,
            custom_format,
            max_retries,
            retry_delay,
        )


class OpenAICompatibleClient(BaseLLMClient):
    """
    Generic OpenAI-compatible chat completions client.

    Supports OpenAI directly and compatible endpoints configured with
    OPENAI_BASE_URL.
    """

    DEFAULT_MODEL_LIMITS: Dict[str, Dict[str, int]] = {
        "gpt-5": {"max_output": 128_000, "context_window": 400_000},
        "gpt-4.1": {"max_output": 32768, "context_window": 1_047_576},
        "gpt-4o": {"max_output": 16384, "context_window": 128_000},
        "o4-mini": {"max_output": 100_000, "context_window": 200_000},
        "o3-mini": {"max_output": 100_000, "context_window": 200_000},
    }

    def __init__(self, model_id: str, logger):
        try:
            from openai import OpenAI as _OpenAI  # type: ignore
            import openai as _openai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("openai client is not available") from e

        self._OpenAI = _OpenAI
        self._openai = _openai
        self.model_name = model_id
        self.logger = logger

        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY not set")

        base_url = os.getenv("OPENAI_BASE_URL")
        # Keep retries in this adapter so its max_retries/retry_delay arguments
        # are authoritative instead of multiplying the SDK's own retries.
        client_kwargs: Dict[str, Any] = {"api_key": api_key, "max_retries": 0}
        if base_url:
            client_kwargs["base_url"] = base_url
        self.client = self._OpenAI(**client_kwargs)

        env_limits_raw = os.getenv("OPENAI_DEFAULT_MODEL_LIMITS")
        self._default_limits: Dict[str, Dict[str, int]] = (
            self.DEFAULT_MODEL_LIMITS.copy()
        )
        if env_limits_raw:
            try:
                env_limits = _json.loads(env_limits_raw)
                for k, v in env_limits.items():
                    if isinstance(v, dict):
                        base = self._default_limits.get(k, {}).copy()
                        base.update(
                            {
                                kk: int(vv)
                                for kk, vv in v.items()
                                if isinstance(vv, (int, float, str))
                            }
                        )
                        self._default_limits[k] = base
            except Exception:
                pass

    def _resolve_default_max_tokens(self, model_id: str) -> Optional[int]:
        mapping_raw = os.getenv("OPENAI_MAX_TOKENS_BY_MODEL")
        mapping: Dict[str, Any] = {}
        if mapping_raw:
            try:
                mapping = _json.loads(mapping_raw)
            except Exception:
                mapping = {}

        model_ids = (model_id, self._model_family(model_id))
        for candidate in model_ids:
            if candidate in mapping:
                try:
                    return int(mapping[candidate])
                except Exception:
                    pass

        for k, v in mapping.items():
            try:
                if any(candidate.startswith(k) for candidate in model_ids):
                    return int(v)
            except Exception:
                continue

        for candidate in model_ids:
            if candidate in self._default_limits:
                return int(self._default_limits[candidate].get("max_output", 0)) or None

        for k, v in self._default_limits.items():
            try:
                if any(candidate.startswith(k) for candidate in model_ids):
                    return int(v.get("max_output", 0)) or None
            except Exception:
                continue

        return None

    @staticmethod
    def _model_family(model_id: str) -> str:
        """Return the provider-independent model portion of a model ID."""
        return model_id.rsplit("/", 1)[-1].lower()

    @classmethod
    def _uses_max_completion_tokens(cls, model_id: str) -> bool:
        return is_reasoning_model(model_id)

    @classmethod
    def _normalize_temperature(
        cls, model_id: str, temperature: Optional[float]
    ) -> Optional[float]:
        # Both this and _uses_max_completion_tokens above now delegate to
        # the single module-level is_reasoning_model() classifier, so the
        # two checks can no longer independently drift out of sync (gpt-5
        # was previously missing from this method only).
        if is_reasoning_model(model_id):
            return None
        return temperature

    @classmethod
    def _set_token_limit(
        cls, kwargs: Dict[str, Any], model_id: str, token_limit: Optional[int]
    ) -> None:
        if token_limit is None:
            return
        key = (
            "max_completion_tokens"
            if cls._uses_max_completion_tokens(model_id)
            else "max_tokens"
        )
        kwargs[key] = token_limit

    @staticmethod
    def _extract_text_from_chunk(chunk: Any) -> Optional[str]:
        if isinstance(chunk, dict):
            choices = chunk.get("choices", [])
        else:
            choices = getattr(chunk, "choices", [])
        if not choices:
            return None

        first = choices[0]
        delta = (
            first.get("delta")
            if isinstance(first, dict)
            else getattr(first, "delta", None)
        )
        if delta is None:
            return None
        content = (
            delta.get("content")
            if isinstance(delta, dict)
            else getattr(delta, "content", None)
        )
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            fragments = []
            for part in content:
                text = (
                    part.get("text")
                    if isinstance(part, dict)
                    else getattr(part, "text", None)
                )
                if text:
                    fragments.append(text)
            return "".join(fragments) or None
        return None

    def _is_retryable_error(self, error: Exception) -> bool:
        retryable_types = tuple(
            error_type
            for error_type in (
                getattr(self._openai, "RateLimitError", None),
                getattr(self._openai, "APIConnectionError", None),
                getattr(self._openai, "APITimeoutError", None),
            )
            if isinstance(error_type, type)
        )
        if retryable_types and isinstance(error, retryable_types):
            return True

        status_code = getattr(error, "status_code", None)
        return status_code in (408, 409, 429) or (
            isinstance(status_code, int) and status_code >= 500
        )

    def test_api(self) -> None:
        test_messages = [{"role": "user", "content": "ping"}]
        token_attempts = [1, 4, 16, 32]
        last_error: Optional[Exception] = None

        for tok in token_attempts:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": test_messages,
                }
                self._set_token_limit(kwargs, self.model_name, tok)
                temperature = self._normalize_temperature(self.model_name, 0)
                if temperature is not None:
                    kwargs["temperature"] = temperature
                self.client.chat.completions.create(**kwargs)
                return
            except Exception as e:  # noqa: BLE001
                last_error = e
                msg = str(e).lower()
                if (
                    "max_tokens" in msg
                    or "model output limit" in msg
                    or "finish the message" in msg
                ) and tok != token_attempts[-1]:
                    continue
                break

        if last_error:
            raise ValueError(f"OpenAI-compatible API test failed: {last_error}")
        raise ValueError("OpenAI-compatible API test failed: unknown error")

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        retries = 0
        call_fn = (
            self.client.chat.completions.parse
            if custom_format is not None
            else self.client.chat.completions.create
        )
        response_format = (
            custom_format
            if custom_format is not None
            else ({"type": "json_object"} if return_json else None)
        )
        eff_max = (
            max_tokens
            if max_tokens is not None
            else self._resolve_default_max_tokens(self.model_name)
        )
        eff_temp = self._normalize_temperature(self.model_name, temperature)

        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if eff_temp is not None:
                    kwargs["temperature"] = eff_temp
                self._set_token_limit(kwargs, self.model_name, eff_max)

                resp = call_fn(**kwargs)
                if custom_format is not None:
                    return resp.choices[0].message.parsed.model_dump()
                return resp.choices[0].message.content
            except Exception as e:  # noqa: BLE001
                if not self._is_retryable_error(e):
                    self.logger.error(f"OpenAI-compatible error: {e}")
                    return None
                retries += 1
                if retries < max_retries:
                    delay = retry_delay * retries
                    self.logger.warning(
                        f"Transient OpenAI-compatible error: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)

        self.logger.error("Max retries exceeded for OpenAI-compatible request")
        return None

    def infer_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ):
        if return_json or custom_format is not None:
            yield from super().infer_stream(
                messages,
                temperature,
                max_tokens,
                return_json,
                custom_format,
                max_retries,
                retry_delay,
            )
            return

        eff_max = (
            max_tokens
            if max_tokens is not None
            else self._resolve_default_max_tokens(self.model_name)
        )
        eff_temp = self._normalize_temperature(self.model_name, temperature)
        retries = 0

        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                    "stream": True,
                }
                if eff_temp is not None:
                    kwargs["temperature"] = eff_temp
                self._set_token_limit(kwargs, self.model_name, eff_max)

                stream = self.client.chat.completions.create(**kwargs)
                for chunk in stream:
                    text = self._extract_text_from_chunk(chunk)
                    if text:
                        yield text
                return
            except Exception as e:  # noqa: BLE001
                if not self._is_retryable_error(e):
                    self.logger.error(f"OpenAI-compatible streaming error: {e}")
                    return
                retries += 1
                if retries < max_retries:
                    delay = retry_delay * retries
                    self.logger.warning(
                        f"Transient OpenAI-compatible streaming error: {e}. "
                        f"Retrying in {delay} seconds..."
                    )
                    time.sleep(delay)

        self.logger.error(
            "Max retries exceeded for OpenAI-compatible streaming request"
        )


class OpenRouterClient(BaseLLMClient):
    """
    OpenRouter client using OpenAI SDK with custom base URL.
    Supports models from OpenAI, Anthropic, Google, Qwen, and many other providers.
    """

    # Default model limits based on latest OpenRouter offerings
    DEFAULT_MODEL_LIMITS: Dict[str, Dict[str, int]] = {
        "openai/gpt-5": {"max_output": 128_000, "context_window": 400_000},
        "openai/gpt-5-codex": {"max_output": 128_000, "context_window": 400_000},
        "google/gemini-2.5-flash": {"max_output": 65_536, "context_window": 1_000_000},
        "google/gemini-2.5-pro": {"max_output": 65_536, "context_window": 1_000_000},
        "anthropic/claude-sonnet-4.5": {
            "max_output": 16_384,
            "context_window": 1_000_000,
        },
    }

    def __init__(self, model_id: str, logger):
        try:
            from openai import OpenAI as _OpenAI  # type: ignore
            import openai as _openai  # type: ignore
        except Exception as e:  # pragma: no cover
            raise RuntimeError("openai client is not available") from e

        self._OpenAI = _OpenAI
        self._openai = _openai
        self.model_name = model_id
        self.logger = logger

        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set")

        # Optional headers for OpenRouter
        default_headers = {}
        if site_url := os.getenv("OPENROUTER_SITE_URL"):
            default_headers["HTTP-Referer"] = site_url
        if site_name := os.getenv("OPENROUTER_SITE_NAME"):
            default_headers["X-Title"] = site_name

        self.client = self._OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers=default_headers if default_headers else None,
        )

        # Load env overrides for model limits
        env_limits_raw = os.getenv("OPENROUTER_DEFAULT_MODEL_LIMITS")
        self._default_limits: Dict[str, Dict[str, int]] = (
            self.DEFAULT_MODEL_LIMITS.copy()
        )
        if env_limits_raw:
            try:
                env_limits = _json.loads(env_limits_raw)
                for k, v in env_limits.items():
                    if isinstance(v, dict):
                        base = self._default_limits.get(k, {}).copy()
                        base.update(
                            {
                                kk: int(vv)
                                for kk, vv in v.items()
                                if isinstance(vv, (int, float, str))
                            }
                        )
                        self._default_limits[k] = base
            except Exception:
                pass

    def _resolve_default_max_tokens(self, model_id: str) -> Optional[int]:
        """Resolve default max tokens for a model."""
        # Highest priority: explicit env per-model tokens mapping
        mapping_raw = os.getenv("OPENROUTER_MAX_TOKENS_BY_MODEL")
        mapping: Dict[str, Any] = {}
        if mapping_raw:
            try:
                mapping = _json.loads(mapping_raw)
            except Exception:
                mapping = {}

        if model_id in mapping:
            try:
                return int(mapping[model_id])
            except Exception:
                pass

        # Check for prefix match
        for k, v in mapping.items():
            try:
                if model_id.startswith(k):
                    return int(v)
            except Exception:
                continue

        # Next: built-in/default-limits map
        if model_id in self._default_limits:
            return int(self._default_limits[model_id].get("max_output", 0)) or None

        # Check for prefix match in default limits
        for k, v in self._default_limits.items():
            try:
                if model_id.startswith(k):
                    return int(v.get("max_output", 0)) or None
            except Exception:
                continue

        return None

    def test_api(self) -> None:
        """Test API connectivity with minimal token usage."""
        test_messages = [{"role": "user", "content": "ping"}]
        token_attempts = [1, 4, 16, 32]
        last_error: Optional[Exception] = None

        for tok in token_attempts:
            try:
                self.client.chat.completions.create(
                    model=self.model_name,
                    messages=test_messages,
                    max_tokens=tok,
                    temperature=0,
                )
                return
            except Exception as e:  # noqa: BLE001
                last_error = e
                msg = str(e).lower()
                if (
                    "max_tokens" in msg
                    or "model output limit" in msg
                    or "finish the message" in msg
                ) and tok != token_attempts[-1]:
                    continue
                break

        if last_error:
            raise ValueError(f"OpenRouter API test failed: {last_error}")
        raise ValueError("OpenRouter API test failed: unknown error")

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        """Execute inference using OpenRouter."""
        retries = 0
        call_fn = (
            self.client.chat.completions.parse
            if custom_format is not None
            else self.client.chat.completions.create
        )

        response_format = (
            custom_format
            if custom_format is not None
            else ({"type": "json_object"} if return_json else None)
        )

        eff_max = (
            max_tokens
            if max_tokens is not None
            else self._resolve_default_max_tokens(self.model_name)
        )

        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                }

                if response_format is not None:
                    kwargs["response_format"] = response_format
                if temperature is not None:
                    kwargs["temperature"] = temperature
                if eff_max is not None:
                    kwargs["max_tokens"] = eff_max

                resp = call_fn(**kwargs)

                if custom_format is not None:
                    return resp.choices[0].message.parsed.model_dump()
                return resp.choices[0].message.content

            except self._openai.RateLimitError:  # type: ignore[attr-defined]
                self.logger.warning(
                    f"Rate limit exceeded. Retrying in {retry_delay} seconds..."
                )
                retries += 1
                time.sleep(retry_delay * retries)
            except Exception as e:  # noqa: BLE001
                self.logger.error(f"OpenRouter error: {e}")
                import traceback

                traceback.print_exc()
                break

        self.logger.error("Max retries exceeded. Unable to complete the request.")
        return None


class VLLMClient(BaseLLMClient):
    def __init__(self, model_name: str, server_url: str, logger):
        try:
            from openai import OpenAI
        except Exception as e:
            raise RuntimeError("openai package not available for vLLM client") from e

        if not server_url:
            raise ValueError("VLLM_SERVER_URL must be provided")

        self.model_name = model_name
        # Ensure server_url ends with /v1 for OpenAI-compatible API
        if not server_url.endswith("/v1"):
            server_url = server_url.rstrip("/") + "/v1"
        self.server_url = server_url
        self.logger = logger

        self.client = OpenAI(
            api_key="EMPTY",
            base_url=self.server_url,
        )

    def test_api(self) -> None:
        test_messages = [{"role": "user", "content": "ping"}]
        try:
            self.client.chat.completions.create(
                model=self.model_name,
                messages=test_messages,
                max_tokens=8,
                temperature=0,
            )
        except Exception as e:
            raise ValueError(f"vLLM API test failed: {e}")

    def infer(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float],
        max_tokens: Optional[int],
        return_json: bool,
        custom_format: Any = None,
        max_retries: int = 5,
        retry_delay: int = 5,
    ) -> Optional[str]:
        if custom_format is not None:
            self.logger.warning("vLLM does not support custom format, ignoring")

        retries = 0
        while retries < max_retries:
            try:
                kwargs: Dict[str, Any] = {
                    "model": self.model_name,
                    "messages": messages,
                }

                if temperature is not None:
                    kwargs["temperature"] = temperature

                if max_tokens is not None:
                    kwargs["max_tokens"] = max_tokens

                if return_json:
                    kwargs["response_format"] = {"type": "json_object"}

                resp = self.client.chat.completions.create(**kwargs)
                return resp.choices[0].message.content

            except Exception as e:
                self.logger.error(f"vLLM error: {e}")
                retries += 1
                if retries < max_retries:
                    time.sleep(retry_delay * retries)

        self.logger.error("Max retries exceeded for vLLM request")
        return None
