from django.db import models
from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from pgvector.django import HnswIndex, VectorField


EMBEDDING_DIMENSIONS = 768


class KnowledgeDocument(models.Model):
    """One current official source document, independently refreshable by source id."""

    source_id = models.CharField(max_length=120, unique=True)
    title = models.CharField(max_length=500)
    canonical_url = models.URLField(max_length=1000)
    source_type = models.CharField(max_length=50)
    category = models.JSONField(default=list)
    effective_year = models.PositiveSmallIntegerField(null=True, blank=True)
    document_status = models.CharField(max_length=20, default="unknown")
    effective_from = models.DateField(null=True, blank=True)
    effective_to = models.DateField(null=True, blank=True)
    fetched_at = models.DateTimeField(null=True, blank=True)
    content_hash = models.CharField(max_length=64)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["source_id"]
        verbose_name = "지식 문서"
        verbose_name_plural = "지식 문서"

    def __str__(self) -> str:
        return self.title


class KnowledgeChunk(models.Model):
    """A searchable, section-aware part of an official document."""

    document = models.ForeignKey(KnowledgeDocument, on_delete=models.CASCADE, related_name="chunks")
    chunk_id = models.CharField(max_length=200, unique=True)
    heading_path = models.JSONField(default=list)
    section_ordinal = models.PositiveIntegerField()
    chunk_ordinal = models.PositiveIntegerField()
    page_start = models.PositiveIntegerField(null=True, blank=True)
    page_end = models.PositiveIntegerField(null=True, blank=True)
    content = models.TextField()
    content_hash = models.CharField(max_length=64)
    search_text = models.TextField(blank=True)
    search_vector = SearchVectorField(null=True)
    embedding = VectorField(dimensions=EMBEDDING_DIMENSIONS, null=True, blank=True)
    embedding_model = models.CharField(max_length=100, blank=True)
    embedded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["document__source_id", "section_ordinal", "chunk_ordinal"]
        indexes = [
            models.Index(
                fields=["document", "section_ordinal", "chunk_ordinal"],
                name="knowledge_k_documen_2e238e_idx",
            ),
            HnswIndex(
                name="knowledge_chunk_embedding_hnsw",
                fields=["embedding"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
            GinIndex(name="knowledge_chunk_fts_gin", fields=["search_vector"]),
        ]
        verbose_name = "지식 청크"
        verbose_name_plural = "지식 청크"

    def __str__(self) -> str:
        return f"{self.document.source_id}: {' > '.join(self.heading_path)}"
