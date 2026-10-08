"""An encoder chosen per call (embedding_model) loads from the local cache only.

Tool_RAG's schema offers larger open encoders to whoever calls it, including an
LLM agent. When one agent picked gte-qwen2-7b, the tool call began downloading
about 28 GB of weights into the home model cache; the quota filled and the
surrounding jobs failed. A per-call encoder now never downloads unless
TOOLUNIVERSE_ALLOW_ENCODER_DOWNLOAD=1 is set; the default encoder is unchanged.
"""

import os
import sys
import types

import pytest

os.environ.setdefault("TOOLUNIVERSE_LIGHT_IMPORT", "1")

from tooluniverse import tool_finder_embedding as tfe
from tooluniverse.tool_finder_embedding import ENCODER_DOWNLOAD_ENV, ToolFinderEmbedding


def finder():
    """A default finder without loading any model."""
    instance = object.__new__(ToolFinderEmbedding)
    instance.tool_config = {"name": "Tool_RAG"}
    instance.toolfinder_model = "mims-harvard/ToolRAG-T1-GTE-Qwen2-1.5B"
    instance.exclude_tools = ["Tool_RAG"]
    instance.tooluniverse = object()
    instance._sub_finders = {}
    return instance


@pytest.fixture
def built(monkeypatch):
    """Record every sub-finder construction; a cache-only one finds nothing cached."""
    configs = []

    def construct(self, tool_config, tooluniverse):
        configs.append(tool_config["configs"])
        if tool_config["configs"].get("local_files_only"):
            raise OSError("We couldn't connect to 'https://huggingface.co' and cannot find the "
                          "requested files in the cached path")

    monkeypatch.setattr(ToolFinderEmbedding, "__init__", construct)
    monkeypatch.delenv(ENCODER_DOWNLOAD_ENV, raising=False)
    return configs


@pytest.mark.unit
def test_an_uncached_per_call_encoder_is_not_downloaded(built):
    """The call fails with guidance instead of starting a download."""
    tool = finder()
    with pytest.raises(RuntimeError) as error:
        tool._resolve_finder("gte-qwen2-7b")
    message = str(error.value)
    assert "Alibaba-NLP/gte-Qwen2-7B-instruct" in message and ENCODER_DOWNLOAD_ENV in message
    assert built == [{**tfe.KNOWN_ENCODERS["gte-qwen2-7b"], "exclude_tools": ["Tool_RAG"],
                      "local_files_only": True}]
    assert tool._sub_finders == {}  # nothing half-built is kept


@pytest.mark.unit
def test_the_opt_in_allows_the_download(built, monkeypatch):
    """With the opt-in the sub-finder is built as before, without the cache-only flag."""
    monkeypatch.setenv(ENCODER_DOWNLOAD_ENV, "1")
    tool = finder()
    chosen = tool._resolve_finder("e5-mistral-7b")
    assert "local_files_only" not in built[0]
    assert tool._sub_finders["e5-mistral-7b"] is chosen


@pytest.mark.unit
def test_default_unknown_and_hosted_choices_are_unchanged(built):
    """The default finder, an unknown name and a hosted encoder are not cache-bound."""
    tool = finder()
    assert tool._resolve_finder(None) is tool
    assert tool._resolve_finder("default") is tool
    assert tool._resolve_finder("no-such-encoder") is tool
    tool._resolve_finder("openai-3-large")
    assert built == [{**tfe.KNOWN_ENCODERS["openai-3-large"], "exclude_tools": ["Tool_RAG"]}]


@pytest.mark.unit
def test_load_passes_local_files_only_only_when_configured(monkeypatch):
    """The default load call is unchanged; a cache-only one forbids downloads."""
    calls = []

    class FakeModel:
        def __init__(self, name, **kwargs):
            calls.append((name, kwargs))
            self.tokenizer = types.SimpleNamespace(padding_side="left")
            self.device = "cpu"

    monkeypatch.setitem(sys.modules, "sentence_transformers",
                        types.SimpleNamespace(SentenceTransformer=FakeModel))
    monkeypatch.setitem(sys.modules, "torch",
                        types.SimpleNamespace(cuda=types.SimpleNamespace(is_available=lambda: False)))
    for cache_only in (False, True):
        tool = finder()
        tool.use_openai_embedding = False
        tool.trust_remote_code = False
        tool.local_files_only = cache_only
        tool.load_rag_model()
    assert calls[0] == ("mims-harvard/ToolRAG-T1-GTE-Qwen2-1.5B", {"device": "cpu", "trust_remote_code": False})
    assert calls[1][1] == {"device": "cpu", "trust_remote_code": False, "local_files_only": True}
