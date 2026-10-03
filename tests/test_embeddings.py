"""Embedding calls use the embedding deployment, not the chat deployment."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from app.rag.embeddings import async_embed, embed


class EmbeddingClientTest(unittest.IsolatedAsyncioTestCase):
    def test_embed_returns_vectors_in_input_order(self) -> None:
        client = MagicMock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[
                SimpleNamespace(index=1, embedding=[0.2, 0.3]),
                SimpleNamespace(index=0, embedding=[0.1]),
            ]
        )

        with patch("app.rag.embeddings.OpenAI", return_value=client) as openai:
            with patch("app.rag.embeddings.get_env", side_effect=lambda name: name):
                vectors = embed(["first", "second"], dimensions=8)

        self.assertEqual(vectors, [[0.1], [0.2, 0.3]])
        self.assertEqual(openai.call_args.kwargs["base_url"], "OPENAI_EMBEDDING_API_BASE/openai/v1")
        self.assertEqual(openai.call_args.kwargs["api_key"], "OPENAI_EMBEDDING_API_KEY")
        sent = client.embeddings.create.call_args.kwargs
        self.assertEqual(sent["model"], "OPENAI_EMBEDDING_DEPLOYMENT_NAME")
        self.assertEqual(sent["input"], ["first", "second"])
        self.assertEqual(sent["dimensions"], 8)
        client.close.assert_called_once()

    def test_embed_keeps_a_base_url_that_already_has_the_v1_path(self) -> None:
        client = MagicMock()
        client.embeddings.create.return_value = SimpleNamespace(data=[])

        def env(name: str) -> str:
            if name == "OPENAI_EMBEDDING_API_BASE":
                return "https://example.azure.com/openai/v1/"
            return name

        with patch("app.rag.embeddings.OpenAI", return_value=client) as openai:
            with patch("app.rag.embeddings.get_env", side_effect=env):
                embed(["hi"])

        self.assertEqual(openai.call_args.kwargs["base_url"], "https://example.azure.com/openai/v1")

    async def test_async_embed_returns_vectors(self) -> None:
        client = AsyncMock()
        client.embeddings.create.return_value = SimpleNamespace(
            data=[SimpleNamespace(index=0, embedding=[1.0, 2.0])]
        )

        with patch("app.rag.embeddings.AsyncOpenAI", return_value=client):
            with patch("app.rag.embeddings.get_env", side_effect=lambda name: name):
                vectors = await async_embed(["hi"])

        self.assertEqual(vectors, [[1.0, 2.0]])
        client.close.assert_awaited_once()

    def test_empty_input_does_not_call_the_api(self) -> None:
        with patch("app.rag.embeddings.OpenAI") as openai:
            self.assertEqual(embed([]), [])
        openai.assert_not_called()


if __name__ == "__main__":
    unittest.main()
