"""Provider/model resolution helpers based on explicit args and environment.

Resolution order
---------------
provider: explicit > EMBED_PROVIDER > by available creds (azure > openai > huggingface > local)
model   : explicit > EMBED_MODEL > provider defaults
"""

import os


def resolve_provider(explicit: str | None = None) -> str:
    """Resolve an embedding provider string.

    Order: explicit → EMBED_PROVIDER → available credentials (azure > openai > huggingface > local).
    """

    if explicit:
        return explicit
    env = os.getenv("EMBED_PROVIDER")
    if env:
        return env
    if os.getenv("AZURE_OPENAI_API_KEY"):
        return "azure"
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    if os.getenv("HF_TOKEN"):
        return "huggingface"
    return "local"


def resolve_model(provider: str, explicit: str | None = None) -> str:
    """Resolve an embedding model/deployment id for the given provider.

    Order: explicit → EMBED_MODEL → provider default (env override where applicable).
    """

    if explicit:
        return explicit
    em = os.getenv("EMBED_MODEL")
    if em:
        return em
    if provider == "azure":
        # deployment name
        return os.getenv("AZURE_OPENAI_DEPLOYMENT", "text-embedding-3-small")
    if provider == "huggingface":
        return os.getenv("HF_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    if provider == "local":
        return os.getenv("LOCAL_EMBED_MODEL", "all-MiniLM-L6-v2")
    # openai/default
    return "text-embedding-3-small"
