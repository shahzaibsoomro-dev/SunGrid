"""The message list is what we keep. The model receives a smaller view of it.

A saved turn is one of:

- {"role": "system", "content": "..."}
- {"role": "user", "content": "..."}
- {"result": "text reply"} when the model wrote a message
- {"result": [{"type": "function_call", ...}]} when the model called a tool
- {"type": "function_call_output", "call_id": "...", "output": "..."}

`at` stays in the local file. `to_llm_input` does not send it.
A text result is sent back as an assistant message. A tool-call result is sent
back as those function_call items.
"""

from typing import Any


def to_llm_input(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build the API input from the saved transcript."""
    model_input: list[dict[str, Any]] = []
    for message in messages:
        if "result" in message:
            result = message["result"]
            if isinstance(result, str):
                if result:
                    model_input.append({"role": "assistant", "content": result})
            else:
                model_input.extend(result)
            continue
        model_input.append({key: value for key, value in message.items() if key != "at"})
    return model_input
