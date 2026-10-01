"""Azure OpenAI client using the responses API.

Every call requires messages and model. Everything else goes through **kwargs
and is forwarded to the API as-is, for example:

- temperature
- max_tokens
- top_p
- tools
- response_format
- provider-specific parameters

Pass only settings the chosen model accepts. A model that does not support
one of these will reject the request. async_llm_stream always sets stream=True,
so do not pass stream yourself.
"""

from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.config import get_env


def llm(messages: list[dict[str, str]], model: str, **kwargs: Any) -> str:
    """Send messages to the model and return the full reply."""
    client = OpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        response = client.responses.create(model=model, input=_to_input(messages), **kwargs)
        return response.output_text
    finally:
        client.close()


async def async_llm(messages: list[dict[str, str]], model: str, **kwargs: Any) -> str:
    """Send messages to the model without blocking, and return the full reply."""
    client = AsyncOpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        response = await client.responses.create(model=model, input=_to_input(messages), **kwargs)
        return response.output_text
    finally:
        await client.close()


async def async_llm_stream(
    messages: list[dict[str, str]],
    model: str,
    **kwargs: Any,
) -> AsyncIterator[str]:
    """Stream reply text from the model, one piece at a time."""
    client = AsyncOpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        stream = await client.responses.create(
            model=model,
            input=_to_input(messages),
            stream=True,
            **kwargs,
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
    finally:
        await client.close()


def _to_input(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    """Keep role and content. Stored turns also carry a timestamp the API does not accept."""
    return [{"role": message["role"], "content": message["content"]} for message in messages]
