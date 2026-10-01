from app.config import get_env
from app.llm.client import async_llm_stream
import asyncio
import time


async def main():
    start_time = time.time()
    parts: list[str] = []
    messages = [{"role": "user", "content": "What is 22+223? give me the answer in a single line"}]
    async for delta in async_llm_stream(messages, get_env("OPENAI_DEPLOYMENT_NAME")):
        parts.append(delta)
    response = "".join(parts)
    end_time = time.time()
    print(f"Time taken: {end_time - start_time} seconds")
    return response

if __name__ == "__main__":
    response = asyncio.run(main())
    print(response)