"""Azure OpenAI client using the responses API."""

from openai import OpenAI

from app.config import get_env


def get_client() -> OpenAI:
    """Build a client from OPENAI_API_BASE and OPENAI_API_KEY."""
    return OpenAI(
        base_url=get_env("OPENAI_API_BASE"),
        api_key=get_env("OPENAI_API_KEY"),
    )


async def complete(user_input: str) -> str:
    """Send one input to OPENAI_DEPLOYMENT_NAME and return the reply text."""
    response = get_client().responses.create(
        model=get_env("OPENAI_DEPLOYMENT_NAME"),
        input=user_input,
    )
    return response.output_text
