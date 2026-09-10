# Generated manually to make the pgvector extension dependency explicit.

import pgvector.django
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("core", "0001_enable_vector"),
    ]

    operations = [
        migrations.CreateModel(
            name="KnowledgeDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source_id", models.CharField(max_length=120, unique=True)),
                ("title", models.CharField(max_length=500)),
                ("canonical_url", models.URLField(max_length=1000)),
                ("source_type", models.CharField(max_length=50)),
                ("category", models.JSONField(default=list)),
                ("effective_year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("fetched_at", models.DateTimeField(blank=True, null=True)),
                ("content_hash", models.CharField(max_length=64)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ["source_id"], "verbose_name": "지식 문서", "verbose_name_plural": "지식 문서"},
        ),
        migrations.CreateModel(
            name="KnowledgeChunk",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("chunk_id", models.CharField(max_length=200, unique=True)),
                ("heading_path", models.JSONField(default=list)),
                ("section_ordinal", models.PositiveIntegerField()),
                ("chunk_ordinal", models.PositiveIntegerField()),
                ("page_start", models.PositiveIntegerField(blank=True, null=True)),
                ("page_end", models.PositiveIntegerField(blank=True, null=True)),
                ("content", models.TextField()),
                ("content_hash", models.CharField(max_length=64)),
                ("embedding", pgvector.django.VectorField(blank=True, dimensions=768, null=True)),
                ("embedding_model", models.CharField(blank=True, max_length=100)),
                ("embedded_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("document", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="chunks", to="knowledge.knowledgedocument")),
            ],
            options={"ordering": ["document__source_id", "section_ordinal", "chunk_ordinal"], "verbose_name": "지식 청크", "verbose_name_plural": "지식 청크"},
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=models.Index(fields=["document", "section_ordinal", "chunk_ordinal"], name="knowledge_k_documen_2e238e_idx"),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=pgvector.django.HnswIndex(ef_construction=64, fields=["embedding"], m=16, name="knowledge_chunk_embedding_hnsw", opclasses=["vector_cosine_ops"]),
        ),
    ]
