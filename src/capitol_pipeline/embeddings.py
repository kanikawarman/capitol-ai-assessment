from typing import List
from openai import OpenAI

client = OpenAI()  # uses OPENAI_API_KEY from env


def embed_text(text: str, model: str = "text-embedding-3-small") -> List[float]:
    # TODO: refine model name depending on API version
    response = client.embeddings.create(
        model=model,
        input=text,
    )
    return response.data[0].embedding
