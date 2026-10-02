"""The three LLM calls share messages, model, and optional settings."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.llm.client import async_llm, async_llm_stream, llm


def _messages() -> list[dict[str, str]]:
    return [{"role": "user", "content": "Hi", "at": "2026-01-01T00:00:00+00:00"}]


def _response() -> MagicMock:
    response = MagicMock()
    response.model_dump.return_value = {
        "id": "resp_1",
        "model": "gpt-5",
        "status": "completed",
        "output": [
            {
                "type": "message",
                "role": "assistant",
                "content": [{"type": "output_text", "text": "Paris"}],
            }
        ],
    }
    return response


class LlmClientTest(unittest.IsolatedAsyncioTestCase):
    def test_llm_sends_messages_model_and_kwargs(self) -> None:
        client = MagicMock()
        client.responses.create.return_value = _response()

        with patch("app.llm.client.OpenAI", return_value=client):
            response = llm(_messages(), "gpt-5", temperature=0)

        sent = client.responses.create.call_args.kwargs
        self.assertEqual(response["result"], "Paris")
        self.assertEqual(sent["model"], "gpt-5")
        self.assertEqual(sent["input"], [{"role": "user", "content": "Hi"}])
        self.assertEqual(sent["temperature"], 0)
        self.assertNotIn("stream", sent)
        client.close.assert_called_once()

    async def test_async_llm_returns_the_full_reply(self) -> None:
        client = AsyncMock()
        client.responses.create.return_value = _response()

        with patch("app.llm.client.AsyncOpenAI", return_value=client):
            response = await async_llm(_messages(), "gpt-5", temperature=0.2)

        sent = client.responses.create.await_args.kwargs
        self.assertEqual(response["result"], "Paris")
        self.assertEqual(sent["model"], "gpt-5")
        self.assertEqual(sent["temperature"], 0.2)
        self.assertNotIn("stream", sent)
        client.close.assert_awaited_once()

    async def test_tool_call_result_is_a_list(self) -> None:
        response = MagicMock()
        response.model_dump.return_value = {
            "status": "completed",
            "output": [
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "check_rebate_eligibility",
                    "arguments": '{"household_zip": "94103"}',
                    "id": "fc_1",
                    "status": "completed",
                }
            ],
        }
        client = AsyncMock()
        client.responses.create.return_value = response

        with patch("app.llm.client.AsyncOpenAI", return_value=client):
            returned = await async_llm(_messages(), "gpt-5", tools=[])

        self.assertEqual(
            returned["result"],
            [
                {
                    "type": "function_call",
                    "call_id": "call_1",
                    "name": "check_rebate_eligibility",
                    "arguments": '{"household_zip": "94103"}',
                }
            ],
        )

    async def test_failed_response_raises_and_returns_nothing(self) -> None:
        response = MagicMock()
        response.model_dump.return_value = {
            "status": "failed",
            "error": {"message": "The model failed to generate a response."},
            "output": [],
        }
        client = AsyncMock()
        client.responses.create.return_value = response

        with patch("app.llm.client.AsyncOpenAI", return_value=client):
            with self.assertRaises(RuntimeError) as raised:
                await async_llm(_messages(), "gpt-5")

        self.assertIn("failed to generate", str(raised.exception))

    async def test_async_llm_stream_yields_text_pieces(self) -> None:
        async def events():
            yield SimpleNamespace(type="response.output_text.delta", delta="Pa")
            yield SimpleNamespace(type="response.completed")
            yield SimpleNamespace(type="response.output_text.delta", delta="ris")

        client = AsyncMock()
        client.responses.create.return_value = events()

        with patch("app.llm.client.AsyncOpenAI", return_value=client):
            pieces = [delta async for delta in async_llm_stream(_messages(), "gpt-5")]

        sent = client.responses.create.await_args.kwargs
        self.assertEqual(pieces, ["Pa", "ris"])
        self.assertEqual(sent["model"], "gpt-5")
        self.assertTrue(sent["stream"])
        client.close.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
