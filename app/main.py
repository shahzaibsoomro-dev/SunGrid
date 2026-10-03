"""Terminal chat. From the project folder, with the virtual environment active:

    python main.py
"""

import asyncio
import json

from openai import APIConnectionError, APIError

from app.config import get_env
from app.llm.client import async_llm
from app.llm.prompt import SYSTEM_PROMPT
from app.services.chat_store import append_message, load_messages, session_path, start_session
from app.services.tools import run_tool

MAX_TOOL_ROUNDS = 3


async def run() -> None:
    """Read turns from the terminal, answer them, and store both sides."""
    session_id = start_session()
    path = session_path(session_id)
    model = get_env("OPENAI_DEPLOYMENT_NAME")
    append_message(session_id, {"role": "system", "content": SYSTEM_PROMPT})
    print(f"Session file: {path}")
    print("Type a message. Type exit to stop.")

    while True:
        user_text = input("\nYou: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print(f"Chat saved at {path}")
            return

        append_message(session_id, {"role": "user", "content": user_text})
        messages = load_messages(session_id)
        try:
            for round_index in range(MAX_TOOL_ROUNDS + 1):
                response = await async_llm(messages, model)
                action = response["action"]
                assistant_message = {
                    "role": "assistant",
                    "content": {
                        "reasoning": response["reasoning"],
                        "intent": response["intent"],
                        "action": action,
                    },
                }
                messages.append(assistant_message)
                append_message(session_id, assistant_message)
                show_block("Reasoning", response["reasoning"])
                show_block("Intent", response["intent"])
                if action["type"] == "response":
                    show_block("Agent", action["text"])
                    break

                if round_index == MAX_TOOL_ROUNDS:
                    print("\nAgent: I stopped because the tool calls did not finish.")
                    break

                show_tool_call(action["name"], action["arguments"])
                tool_message = {
                    "role": "tool",
                    "name": action["name"],
                    "content": await run_tool(action["name"], action["arguments"]),
                }
                show_tool_result(tool_message["content"])
                messages.append(tool_message)
                append_message(session_id, tool_message)
        except (APIError, APIConnectionError, RuntimeError) as exc:
            print(f"\nThe model call failed: {exc}")


def show_block(label: str, body: str) -> None:
    """Print a labeled block, one stored line per row."""
    print(f"\n{label}")
    for line in str(body).splitlines() or [""]:
        print(f"  {line}")


def show_tool_call(name: str, arguments: dict[str, object]) -> None:
    """Print a tool name and each argument on its own line."""
    print(f"\nTool  {name}")
    for key, value in arguments.items():
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        lines = str(value).splitlines() or [""]
        print(f"  {key}: {lines[0]}")
        for line in lines[1:]:
            print(f"  {line}")


def show_tool_result(content: str) -> None:
    """Print a tool result as chunks or as one field per line."""
    print("\nResult")
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        for line in content.splitlines() or [""]:
            print(f"  {line}")
        return
    if isinstance(data, list):
        for index, item in enumerate(data, start=1):
            print(f"\n  {index}. {item.get('source', '')}")
            print(f"     {item.get('section', '')}")
            for line in str(item.get("text", "")).splitlines():
                print(f"     {line}")
        return
    if isinstance(data, dict):
        for key, value in data.items():
            print(f"  {key}: {value}")
        return
    print(f"  {data}")


def main() -> None:
    """Start the terminal chat."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
