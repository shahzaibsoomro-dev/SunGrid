"""The message list is what we keep. The model receives a smaller view of it.

A saved turn is one of:

- {"role": "system", "content": "..."}
- {"role": "user", "content": "..."}
- {"role": "assistant", "content": {"reasoning", "intent", "action"}} for one model turn
- {"role": "tool", "name": "...", "content": "..."} after our code runs a tool call

`at` stays in the local file. `to_llm_input` does not send it.
A model turn is sent back as one assistant message containing that JSON.
A tool result is sent back as a user message, because the tool call itself
lives inside the assistant JSON rather than as a native function call.
"""

import json
from typing import Any


def to_llm_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the API input from the saved transcript."""
    model_input: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "assistant" and isinstance(message.get("content"), dict):
            model_input.append({"role": "assistant", "content": json.dumps(message["content"])})
            continue
        if message.get("role") == "tool":
            model_input.append(
                {
                    "role": "user",
                    "content": f"Tool {message.get('name')} returned: {message.get('content')}",
                }
            )
            continue
        model_input.append({key: value for key, value in message.items() if key != "at"})
    return model_input
