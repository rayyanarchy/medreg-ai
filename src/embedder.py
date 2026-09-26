"""
Embedding wrapper around the OpenAI API.
Used both to embed chunks once (when building the index) and to embed
a user's question every time, at query time — same function, either use.
"""

import os
from openai import OpenAI

MODEL = "text-embedding-3-small"

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY not set. Add it to a .env file or your environment."
            )
        _client = OpenAI(api_key=api_key)
    return _client


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Embeds a batch of texts in a single API call.
    Returns one vector per input text, in the same order.
    """
    if not texts:
        return []

    client = _get_client()
    response = client.embeddings.create(model=MODEL, input=texts)
    return [item.embedding for item in response.data]


def embed_query(query: str) -> list[float]:
    """Embeds one piece of text — e.g. the user's question at query time."""
    return embed_texts([query])[0]