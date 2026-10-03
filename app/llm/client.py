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

llm and async_llm return one object:
{"reasoning": "...", "intent": "...", "action": {...}}.
action.type is "response" or "tool_call". A tool call is inside that
object, together with reasoning and intent. A native function_call item
with no JSON message is rejected.

A failed request raises. Connection and HTTP errors come from the SDK.
A response whose status is failed or cancelled, or which carries an error
object, raises RuntimeError with the API message. Nothing is returned in
that case, so the caller does not save it.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

from openai import AsyncOpenAI, OpenAI

from app.config import get_env
from app.llm.messages import to_llm_input
from app.llm.prompt import CONTENT_INTENTS, ELIGIBILITY_INTENT, ELIGIBILITY_TOOL, INTENTS, RETRIEVAL_TOOL


def response_json(response: Any) -> dict[str, Any]:
    """Return reasoning, intent, and action from the model message."""
    data = response.model_dump(mode="json")
    status = data.get("status")
    error = data.get("error")
    if status in {"failed", "cancelled"} or error:
        message = error.get("message") if isinstance(error, dict) else None
        raise RuntimeError(message or f"Model response {status or 'failed'}.")

    parts: list[str] = []
    for item in data.get("output") or []:
        if item.get("type") != "message":
            continue
        for block in item.get("content") or []:
            if block.get("type") == "output_text" and block.get("text"):
                parts.append(block["text"])
    if not parts:
        raise RuntimeError("Model reply did not include a JSON message.")
    return assistant_reply("".join(parts).strip())


def assistant_reply(text: str) -> dict[str, Any]:
    """Read reasoning, intent, and one action from a text reply."""
    try:
        data = json.loads(json_object(text))
    except json.JSONDecodeError as exc:
        preview = " ".join(text.split())[:180]
        raise RuntimeError(f"Model reply was not JSON: {preview}") from exc
    if not isinstance(data, dict):
        raise RuntimeError("Model reply must be a JSON object.")
    reasoning = data.get("reasoning")
    intent = data.get("intent")
    action = data.get("action")
    if not isinstance(reasoning, str) or not isinstance(action, dict) or intent not in INTENTS:
        allowed = ", ".join(INTENTS)
        raise RuntimeError(f"Model reply needs reasoning, an intent ({allowed}), and an action.")
    return {"reasoning": reasoning, "intent": intent, "action": parse_action(action, intent)}


def json_object(text: str) -> str:
    """Return the first JSON object, even with a fence or an extra closing brace."""
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    start = stripped.find("{")
    if start == -1:
        return stripped
    try:
        _, end = json.JSONDecoder().raw_decode(stripped, start)
    except json.JSONDecodeError:
        end = stripped.rfind("}") + 1
        if end <= start:
            return stripped
    return stripped[start:end]


def parse_action(action: dict[str, Any], intent: str) -> dict[str, Any]:
    """Return a response action or one tool call."""
    kind = action.get("type")
    if kind == "response":
        text = action.get("text")
        if not isinstance(text, str):
            raise RuntimeError("A response action needs a text string.")
        return {"type": "response", "text": text}
    if kind == "tool_call":
        return parse_tool_call(action, intent)
    raise RuntimeError('action.type must be "response" or "tool_call".')


def parse_tool_call(action: dict[str, Any], intent: str) -> dict[str, Any]:
    """Accept a retrieval call, or the eligibility tool for the incentive intent."""
    name = action.get("name")
    arguments = tool_arguments(action.get("arguments"))
    if name == RETRIEVAL_TOOL:
        return {"type": "tool_call", "name": name, "arguments": retrieval_arguments(arguments, intent)}
    if name == ELIGIBILITY_TOOL:
        if intent != ELIGIBILITY_INTENT:
            raise RuntimeError(f"{ELIGIBILITY_TOOL} is only valid when intent is {ELIGIBILITY_INTENT}.")
        return {"type": "tool_call", "name": name, "arguments": arguments}
    raise RuntimeError(f"Unknown tool: {name}.")


def tool_arguments(arguments: Any) -> dict[str, Any]:
    """Read tool arguments from an object or a JSON string."""
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise RuntimeError("Tool arguments were not JSON.") from exc
    if not isinstance(arguments, dict):
        raise RuntimeError("Tool arguments must be an object.")
    return arguments


def retrieval_arguments(arguments: dict[str, Any], intent: str) -> dict[str, Any]:
    """Require a query and categories that include the chosen intent."""
    if intent == "non_relevant":
        raise RuntimeError(f"{RETRIEVAL_TOOL} is not used when intent is non_relevant.")
    query = arguments.get("query")
    categories = arguments.get("categories")
    if not isinstance(query, str) or not query.strip():
        raise RuntimeError(f"{RETRIEVAL_TOOL} needs a query string.")
    if not isinstance(categories, list) or not categories:
        raise RuntimeError(f"{RETRIEVAL_TOOL} needs a categories list.")
    if any(category not in CONTENT_INTENTS for category in categories):
        allowed = ", ".join(CONTENT_INTENTS)
        raise RuntimeError(f"Retrieval categories must be one of: {allowed}.")
    if intent not in categories:
        raise RuntimeError("Retrieval categories must include the intent.")
    return {"query": query.strip(), "categories": categories}


def llm(messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
    """Send messages to the model and return reasoning, intent, and action."""
    client = OpenAI(base_url=get_env("OPENAI_API_BASE"), api_key=get_env("OPENAI_API_KEY"))
    try:
        response = client.responses.create(model=model, input=to_llm_input(messages), **kwargs)
        return response_json(response)
    finally:
        client.close()


async def async_llm(messages: list[dict[str, Any]], model: str, **kwargs: Any) -> dict[str, Any]:
    """Send messages without blocking and return reasoning, intent, and action."""
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
