"""LLM client utilities using the new Google GenAI SDK.

The Gemini API key is read from the environment via the Settings object.
"""

from google import genai
from app.config import settings


def get_gemini_client() -> genai.Client:
    """Return a configured GenAI Client instance."""
    if not settings.gemini_api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")
    return genai.Client(api_key=settings.gemini_api_key)


def generate_text(prompt: str, model: str = "gemini-2.0-flash") -> str:
    """One-shot text generation helper."""
    client = get_gemini_client()
    response = client.models.generate_content(model=model, contents=prompt)
    return response.text


def generate_embeddings(text: str) -> list[float]:
    """Generate vector embeddings for semantic search."""
    client = get_gemini_client()
    result = client.models.embed_content(
        model='text-embedding-004',
        contents=text,
    )
    return result.embeddings[0].values
