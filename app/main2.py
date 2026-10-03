"""Streamlit chat. From the project folder, with the virtual environment active:

    streamlit run main2.py
"""

import asyncio
import json

import streamlit as st
from openai import APIConnectionError, APIError

from app.config import get_env
from app.llm.client import async_llm
from app.llm.prompt import SYSTEM_PROMPT
from app.services.chat_store import append_message, list_sessions, load_messages, session_path, start_session
from app.services.tools import run_tool

MAX_TOOL_ROUNDS = 3


async def answer(session_id: str) -> str | None:
    """Run one member turn, including tool calls, and save each step."""
    messages = load_messages(session_id)
    model = get_env("OPENAI_DEPLOYMENT_NAME")
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
        if action["type"] == "response":
            return None
        if round_index == MAX_TOOL_ROUNDS:
            return "I stopped because the tool calls did not finish."
        tool_message = {
            "role": "tool",
            "name": action["name"],
            "content": await run_tool(action["name"], action["arguments"]),
        }
        messages.append(tool_message)
        append_message(session_id, tool_message)
    return None


def open_new_chat() -> str:
    """Start a saved session and remember it in this browser tab."""
    session_id = start_session()
    append_message(session_id, {"role": "system", "content": SYSTEM_PROMPT})
    st.session_state.session_id = session_id
    st.session_state.notice = ""
    return session_id


def active_session_id() -> str:
    """Reuse the open session, or start one on the first visit."""
    session_id = st.session_state.get("session_id", "")
    if isinstance(session_id, str) and session_id:
        try:
            if session_path(session_id).is_file():
                return session_id
        except ValueError:
            pass
    return open_new_chat()


def main() -> None:
    """Show the copilot, the open chat, and earlier sessions."""
    st.set_page_config(
        page_title="SunGrid Cooperative",
        page_icon="☀",
        layout="centered",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
        <style>
        [data-testid="stSidebar"] code {
            white-space: pre-wrap !important;
            word-break: break-all;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    session_id = active_session_id()
    draw_sidebar(session_id)
    st.title("SunGrid Cooperative")
    st.markdown(
        "Member-support copilot for program policies, rebates, billing, "
        "installation, and company updates. Ask in plain language. "
        "Each reply keeps the intent, the reasoning, any tool call, "
        "and the document chunks the answer came from."
    )
    notice = st.session_state.get("notice", "")
    if isinstance(notice, str) and notice:
        st.warning(notice)
    draw_transcript(load_messages(session_id))
    user_text = st.chat_input("Ask about a policy, a bill, or a rebate")
    if user_text and user_text.strip():
        send(session_id, user_text.strip())


def draw_sidebar(session_id: str) -> None:
    """Session id, a new chat, and the saved sessions."""
    with st.sidebar:
        st.header("Sessions")
        st.caption("Session id")
        st.code(session_id, language=None)
        if st.button("New chat", type="primary", use_container_width=True):
            open_new_chat()
            st.rerun()
        st.divider()
        st.caption("Earlier chats")
        sessions = list_sessions()
        if not sessions:
            st.caption("No saved chats yet.")
            return
        for item in sessions:
            label = session_label(item)
            if item["session_id"] == session_id:
                st.markdown(f"**{label}**")
                continue
            if st.button(label, key=f"open-{item['session_id']}", use_container_width=True):
                st.session_state.session_id = item["session_id"]
                st.session_state.notice = ""
                st.rerun()


def session_label(item: dict[str, str]) -> str:
    """Short row for one saved chat."""
    preview = " ".join(item["preview"].split())
    if len(preview) > 42:
        preview = preview[:42] + "…"
    started = item["started"][:16].replace("T", " ")
    if started:
        return f"{started}  {preview}"
    return preview


def send(session_id: str, user_text: str) -> None:
    """Save the member message, answer it, and redraw the chat."""
    append_message(session_id, {"role": "user", "content": user_text})
    st.session_state.notice = ""
    try:
        with st.spinner("One moment…"):
            notice = asyncio.run(answer(session_id))
        st.session_state.notice = notice or ""
    except (APIError, APIConnectionError, RuntimeError) as exc:
        st.session_state.notice = f"The model call failed: {exc}"
    st.rerun()


def draw_transcript(messages: list[dict[str, object]]) -> None:
    """Show member messages and the steps that answered them."""
    turns = member_turns(messages)
    if not turns:
        st.caption("Ask about membership tiers, when bills are issued, or the rooftop rebate.")
        return
    for turn in turns:
        with st.chat_message("user"):
            st.markdown(str(turn["user"]))
        steps = turn["steps"]
        if not isinstance(steps, list) or not steps:
            continue
        with st.chat_message("assistant"):
            for step in steps:
                if isinstance(step, dict):
                    draw_step(step)


def member_turns(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    """Group each member message with the assistant and tool steps after it."""
    turns: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for message in messages:
        role = message.get("role")
        if role == "user" and isinstance(message.get("content"), str):
            current = {"user": message["content"], "steps": []}
            turns.append(current)
            continue
        if current is None or role not in {"assistant", "tool"}:
            continue
        steps = current["steps"]
        if isinstance(steps, list):
            steps.append(message)
    return turns


def draw_step(message: dict[str, object]) -> None:
    """Show one saved assistant turn or one tool result."""
    if message.get("role") == "tool":
        draw_tool_result(str(message.get("name") or ""), str(message.get("content") or ""))
        return
    content = message.get("content")
    if not isinstance(content, dict):
        st.markdown(str(content or ""))
        return
    action = content.get("action")
    st.caption(f"Intent · {content.get('intent', '')}")
    st.markdown(str(content.get("reasoning") or ""))
    if not isinstance(action, dict):
        return
    if action.get("type") == "tool_call":
        draw_tool_call(str(action.get("name") or ""), action.get("arguments"))
        return
    st.markdown(str(action.get("text") or ""))


def draw_tool_call(name: str, arguments: object) -> None:
    """Show the tool name and each argument."""
    st.markdown(f"**Tool** · `{name}`")
    if not isinstance(arguments, dict):
        return
    for key, value in arguments.items():
        if isinstance(value, list):
            value = ", ".join(str(item) for item in value)
        st.text(f"{key}: {value}")


def draw_tool_result(name: str, content: str) -> None:
    """Show retrieved chunks, or one field per line for another tool."""
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        st.text(content)
        return
    if isinstance(data, list):
        st.markdown(f"**Relevant chunks** · `{name}`")
        if not data:
            st.caption("No chunks were close enough to use.")
            return
        for index, item in enumerate(data, start=1):
            if not isinstance(item, dict):
                st.text(str(item))
                continue
            with st.container(border=True):
                st.markdown(f"**{index}. {item.get('source', '')}**")
                st.caption(str(item.get("section", "")))
                st.markdown(str(item.get("text", "")))
        return
    if isinstance(data, dict):
        st.markdown(f"**Result** · `{name}`")
        for key, value in data.items():
            st.text(f"{key}: {value}")
        return
    st.text(str(data))


if __name__ == "__main__":
    main()
