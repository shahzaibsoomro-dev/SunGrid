"""Embed text with the Azure embedding deployment from .env.

embed and async_embed take a list of strings and return one vector per string,
in the same order. Other settings go through **kwargs and are forwarded to the
API as-is, for example dimensions and encoding_format. Pass only settings this
deployment accepts.

The embedding host in .env is the resource root. The client calls the OpenAI
v1 path on that host, the same shape as the chat base URL.
"""

from openai import AsyncOpenAI, OpenAI
from typing import Any

from app.config import get_env


def base_url() -> str:
    """Return the embeddings base URL, including the OpenAI v1 path."""
    base = get_env("OPENAI_EMBEDDING_API_BASE").rstrip("/")
    if not base.endswith("/openai/v1"):
        return f"{base}/openai/v1"
    return base


def vectors(response: Any) -> list[list[float]]:
    """Read embedding vectors in input order."""
    ordered = sorted(response.data, key=lambda item: item.index)
    return [list(item.embedding) for item in ordered]


def embed(texts: list[str], **kwargs: Any) -> list[list[float]]:
    """Return one embedding vector for each text."""
    if not texts:
        return []
    client = OpenAI(base_url=base_url(), api_key=get_env("OPENAI_EMBEDDING_API_KEY"))
    try:
        response = client.embeddings.create(
            model=get_env("OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            input=texts,
            **kwargs,
        )
        return vectors(response)
    finally:
        client.close()


async def async_embed(texts: list[str], **kwargs: Any) -> list[list[float]]:
    """Return one embedding vector for each text without blocking."""
    if not texts:
        return []
    client = AsyncOpenAI(base_url=base_url(), api_key=get_env("OPENAI_EMBEDDING_API_KEY"))
    try:
        response = await client.embeddings.create(
            model=get_env("OPENAI_EMBEDDING_DEPLOYMENT_NAME"),
            input=texts,
            **kwargs,
        )
        return vectors(response)
    finally:
        await client.close()
