"""The message list is what we keep. The model receives a smaller view of it.

A saved turn is one of:

- {"role": "system", "content": "..."}
- {"role": "user", "content": "..."}
- {"role": "assistant", "content": {"reasoning": "...", "result": "..."}} for one written reply
- {"result": [{"type": "function_call", ...}]} when the model called a tool
- {"type": "function_call_output", "call_id": "...", "output": "..."}

`at` stays in the local file. `to_llm_input` does not send it.
A written reply is sent back as one assistant message. A tool-call result is
sent back as those function_call items.
"""

import json
from typing import Any


def to_llm_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the API input from the saved transcript."""
    model_input: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "assistant" and isinstance(message.get("content"), dict):
            model_input.append(
                {"role": "assistant", "content": json.dumps(message["content"])}
            )
            continue
        if "result" in message:
            model_input.extend(message["result"])
            continue
        model_input.append({key: value for key, value in message.items() if key != "at"})
    return model_input
