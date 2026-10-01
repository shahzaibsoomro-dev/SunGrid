from app.config import get_env
from app.services.chat_store import append_message, load_messages, session_path, start_session
from openai import APIConnectionError, APIError
from app.llm.client import async_llm_stream
import asyncio


async def run() -> None:
    """Read turns from the terminal, answer them, and store both sides."""
    session_id = start_session()
    path = session_path(session_id)
    model = get_env("OPENAI_DEPLOYMENT_NAME")
    print(f"Session file: {path}")
    print("Type a message. Type exit to stop.")

    while True:
        user_text = input("\nYou: ").strip()
        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            print(f"Chat saved at {path}")
            return

        append_message(session_id, "user", user_text)
        print("\nAgent: ", end="", flush=True)
        parts: list[str] = []
        try:
            async for delta in async_llm_stream(load_messages(session_id), model):
                parts.append(delta)
                print(delta, end="", flush=True)
        except (APIError, APIConnectionError) as exc:
            print(f"\nThe model call failed: {exc}")
            continue
        print()

        reply = "".join(parts).strip()
        if not reply:
            print("The model returned an empty reply. Nothing new was saved for the agent.")
            continue

        append_message(session_id, "assistant", reply)
   


def main() -> None:
    """Start the terminal chat."""
    asyncio.run(run())


if __name__ == "__main__":
    main()
