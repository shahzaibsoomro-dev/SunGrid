"""Save and load one agent conversation per session."""

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import root_dir

_SESSION_ID = re.compile(r"^[0-9a-f]{32}$")


def chats_dir() -> Path:
    """Directory that holds one JSON file per agent session."""
    return root_dir() / "data" / "chats"


def session_path(session_id: str) -> Path:
    """Local JSON file for one agent session."""
    return path(session_id)


def start_session() -> str:
    """Create an empty session file and return its id."""
    session_id = uuid.uuid4().hex
    write(path(session_id), {"session_id": session_id, "messages": []})
    return session_id


def append_message(session_id: str, message: dict[str, Any]) -> None:
    """Append one turn as given, plus the time it was saved."""
    file_path = path(session_id)
    if not file_path.is_file():
        raise FileNotFoundError(f"No chat file for session {session_id}.")

    stored = dict(message)
    stored["at"] = datetime.now(timezone.utc).isoformat()
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    payload["messages"].append(stored)
    write(file_path, payload)


def load_messages(session_id: str) -> list[dict[str, Any]]:
    """Return the saved turns for one agent session, oldest first."""
    file_path = path(session_id)
    if not file_path.is_file():
        raise FileNotFoundError(f"No chat file for session {session_id}.")
    payload = json.loads(file_path.read_text(encoding="utf-8"))
    return payload["messages"]


def path(session_id: str) -> Path:
    if not _SESSION_ID.fullmatch(session_id):
        raise ValueError("session_id must be a 32-character hex id.")
    return chats_dir() / f"{session_id}.json"


def write(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    temporary.replace(path)
