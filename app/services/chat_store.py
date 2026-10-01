"""Save and load one agent conversation per session."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.config import root_dir

_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")
_ROLES = {"user", "assistant"}


def chats_dir() -> Path:
    """Directory that holds one JSON file per agent session."""
    return root_dir() / "data" / "chats"


def session_path(session_id: str) -> Path:
    """Local JSON file for one agent session."""
    return _path(session_id)


def start_session() -> str:
    """Create an empty session file and return its id."""
    session_id = uuid.uuid4().hex
    _write(_path(session_id), {"session_id": session_id, "messages": []})
    return session_id


def append_message(session_id: str, role: str, content: str) -> None:
    """Append one user or assistant turn to an existing session."""
    if role not in _ROLES:
        raise ValueError("role must be 'user' or 'assistant'.")
    text = content.strip()
    if not text:
        raise ValueError("message content is empty.")

    path = _path(session_id)
    if not path.is_file():
        raise FileNotFoundError(f"No chat file for session {session_id}.")

    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["messages"].append(
        {
            "role": role,
            "content": text,
            "at": datetime.now(timezone.utc).isoformat(),
        }
    )
    _write(path, payload)


def load_messages(session_id: str) -> list[dict[str, str]]:
    """Return the saved turns for one agent session, oldest first."""
    path = _path(session_id)
    if not path.is_file():
        raise FileNotFoundError(f"No chat file for session {session_id}.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["messages"]


def _path(session_id: str) -> Path:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("session_id must be a 32-character hex id.")
    return chats_dir() / f"{session_id}.json"


def _write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)
