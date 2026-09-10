from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="knowledgedocument",
            name="document_status",
            field=models.CharField(default="unknown", max_length=20),
        ),
        migrations.AddField(
            model_name="knowledgedocument",
            name="effective_from",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgedocument",
            name="effective_to",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="knowledgechunk",
            name="search_text",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="knowledgechunk",
            name="search_vector",
            field=SearchVectorField(null=True),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=GinIndex(fields=["search_vector"], name="knowledge_chunk_fts_gin"),
        ),
    ]
