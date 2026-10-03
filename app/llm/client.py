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

llm and async_llm return JSON.
A text reply is {"reasoning": "...", "result": "..."}.
A tool call is {"result": [function_call, ...]}.
The caller tells those two shapes apart.

A failed request raises. Connection and HTTP errors come from the SDK.
A response whose status is failed or cancelled, or which carries an error
object, raises RuntimeError with the API message. Nothing is returned in
that case, so the caller does not save it.
"""

import json
from collections.abc import AsyncIterator
from openai import AsyncOpenAI, OpenAI
from app.config import get_env
from app.llm.messages import to_llm_input
from typing import Any


def response_json(response: Any) -> dict[str, Any]:
    """Return a text reply as a string, or tool calls as a list."""
    data = response.model_dump(mode="json")
    status = data.get("status")
    error = data.get("error")
    if status in {"failed", "cancelled"} or error:
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(message or f"Model response {status or 'failed'}.")

    output = data.get("output") or []
    tool_calls = [
        {
            "type": "function_call",
            "call_id": item.get("call_id"),
            "name": item.get("name"),
            "arguments": item.get("arguments"),
        }
        for item in output
        if item.get("type") == "function_call"
    ]
    if tool_calls:
        return {"result": tool_calls}

    parts: list[str] = []
    for item in output:
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if block.get("type") == "output_text" and block.get("text"):
                parts.append(block["text"])
    return assistant_reply("".join(parts).strip())


def assistant_reply(text: str) -> dict[str, str]:
    """Read the required {"reasoning", "result"} JSON from a text reply."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Model reply was not JSON.") from exc
    if not isinstance(data, dict) or "reasoning" not in data or "result" not in data:
        raise RuntimeError('Model reply must be {"reasoning": "...", "result": "..."}.')
    return {"reasoning": str(data["reasoning"]), "result": str(data["result"])}


def llm(messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
    """Send messages to the model and return the reply string or tool calls."""
    client = OpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        response = client.responses.create(model=model, input=to_llm_input(messages), **kwargs)
        return response_json(response)
    finally:
        client.close()


async def async_llm(messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
    """Send messages without blocking and return the reply string or tool calls."""
    client = AsyncOpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        response = await client.responses.create(model=model, input=to_llm_input(messages), **kwargs)
        return response_json(response)
    finally:
        await client.close()


async def async_llm_stream(messages: list[dict[str, Any]], model: str, **kwargs: Any) -> AsyncIterator[str]:
    """Stream reply text from the model, one piece at a time."""
    client = AsyncOpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        stream = await client.responses.create(
            model=model,
            input=to_llm_input(messages),
            stream=True,
            **kwargs,
        )
        async for event in stream:
            if event.type == "response.output_text.delta":
                yield event.delta
    finally:
        await client.close()


