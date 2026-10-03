import asyncio
import json

from openai import APIConnectionError, APIError

from app.config import get_env
from app.llm.client import async_llm
from app.llm.prompt import SYSTEM_PROMPT
from app.services.chat_store import append_message, load_messages, session_path, start_session
from app.services.tools import TOOLS, run_tool

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
                response = await async_llm(messages, model, tools=TOOLS)
                if "reasoning" in response:
                    assistant_message = {
                        "role": "assistant",
                        "content": {
                            "reasoning": response["reasoning"],
                            "result": response["result"],
                        },
                    }
                    messages.append(assistant_message)
                    append_message(session_id, assistant_message)
                    print(f"\nReasoning: {assistant_message['content']['reasoning']}")
                    print(f"Agent: {assistant_message['content']['result']}")
                    break

                messages.append(response)
                append_message(session_id, response)
                result = response["result"]

                if round_index == MAX_TOOL_ROUNDS:
                    print("\nAgent: I stopped because the tool calls did not finish.")
                    break

                for call in result:
                    raw_arguments = call.get("arguments") or "{}"
                    arguments = json.loads(raw_arguments) if isinstance(raw_arguments, str) else raw_arguments
                    print(f"\nCalling {call['name']} {arguments}")
                    tool_message = {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": run_tool(call["name"], arguments),
                    }
                    print(f"Tool result: {tool_message['output']}")
                    messages.append(tool_message)
                    append_message(session_id, tool_message)
        except (APIError, APIConnectionError, RuntimeError) as exc:
            print(f"\nThe model call failed: {exc}")


def main() -> None:
    """Start the terminal chat."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
