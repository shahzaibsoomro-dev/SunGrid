"""Session chat files for the agent conversation."""

import json
import tempfile
import unittest
from pathlib import Path

import app.services.chat_store as chat_store


class ChatStoreTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original = chat_store.chats_dir
        chat_store.chats_dir = lambda: Path(self._tmpdir.name)

    def tearDown(self) -> None:
        chat_store.chats_dir = self._original
        self._tmpdir.cleanup()

    def test_session_file_keeps_turns_in_order(self) -> None:
        session_id = chat_store.start_session()
        chat_store.append_message(session_id, "user", "What is the rooftop rebate?")
        chat_store.append_message(session_id, "assistant", "It is $0.40 per watt, capped at $4,000.")

        messages = chat_store.load_messages(session_id)

        self.assertEqual(
            [message["role"] for message in messages],
            ["user", "assistant"],
        )
        self.assertEqual(messages[0]["content"], "What is the rooftop rebate?")
        saved = json.loads(chat_store.session_path(session_id).read_text(encoding="utf-8"))
        self.assertEqual(saved["session_id"], session_id)
        self.assertEqual(chat_store.session_path(session_id).parent, Path(self._tmpdir.name))

    def test_missing_session_is_rejected(self) -> None:
        with self.assertRaises(FileNotFoundError):
            chat_store.append_message("a" * 32, "user", "hello")


if __name__ == "__main__":
    unittest.main()
