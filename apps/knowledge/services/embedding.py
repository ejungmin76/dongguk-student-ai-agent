"""Gemini document embedding adapter, kept outside Django models and commands."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from tools.knowledge.chunking import KnowledgeChunk as ChunkPayload

from ..models import EMBEDDING_DIMENSIONS


class EmbeddingError(RuntimeError):
    pass


class DocumentEmbedder(Protocol):
    model_name: str
    dimensions: int

    def embed_documents(self, chunks: Sequence[ChunkPayload]) -> list[list[float]]: ...

    def embed_query(self, query: str) -> list[float]: ...


class GeminiDocumentEmbedder:
    """Official Google GenAI SDK adapter for retrieval-document embeddings."""

    model_name = "gemini-embedding-2"
    dimensions = EMBEDDING_DIMENSIONS

    def __init__(self, api_key: str, *, model_name: str | None = None, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        if not api_key:
            raise EmbeddingError("GEMINI_API_KEY is required to create embeddings.")
        self.model_name = model_name or self.model_name
        self.dimensions = dimensions
        try:
            from google import genai
            from google.genai import types
        except ImportError as error:
            raise EmbeddingError("Install google-genai with pip install -r requirements\\development.txt.") from error
        self._types = types
        self._client = genai.Client(api_key=api_key)

    @staticmethod
    def _retrieval_document_text(chunk: ChunkPayload) -> str:
        section = " > ".join(chunk.heading_path)
        return f"title: {chunk.document_title}\nsection: {section}\ntext: {chunk.content}"

    def embed_documents(self, chunks: Sequence[ChunkPayload]) -> list[list[float]]:
        contents = [
            self._types.Content(parts=[self._types.Part.from_text(text=self._retrieval_document_text(chunk))])
            for chunk in chunks
        ]
        return self._embed_contents(contents, len(chunks))

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed generic retrieval documents such as verified menu breadcrumbs."""

        contents = [
            self._types.Content(parts=[self._types.Part.from_text(text=text)])
            for text in texts
        ]
        return self._embed_contents(contents, len(texts))

    def _embed_contents(self, contents: list, expected_count: int) -> list[list[float]]:
        try:
            response = self._client.models.embed_content(
                model=self.model_name,
                contents=contents,
                config=self._types.EmbedContentConfig(output_dimensionality=self.dimensions),
            )
            vectors = [list(item.values) for item in response.embeddings]
        except Exception as error:
            raise EmbeddingError(f"Gemini embedding request failed: {error}") from error
        if len(vectors) != expected_count or any(len(vector) != self.dimensions for vector in vectors):
            raise EmbeddingError("Gemini returned an unexpected embedding count or dimension.")
        return vectors

    def embed_query(self, query: str) -> list[float]:
        """Embed a student question in Gemini's asymmetric QA retrieval format."""

        if not query.strip():
            raise EmbeddingError("Query must not be blank.")
        try:
            response = self._client.models.embed_content(
                model=self.model_name,
                contents=f"task: question answering | query: {query.strip()}",
                config=self._types.EmbedContentConfig(output_dimensionality=self.dimensions),
            )
            vector = list(response.embeddings[0].values)
        except Exception as error:
            raise EmbeddingError(f"Gemini query embedding request failed: {error}") from error
        if len(vector) != self.dimensions:
            raise EmbeddingError("Gemini returned an unexpected query embedding dimension.")
        return vector
