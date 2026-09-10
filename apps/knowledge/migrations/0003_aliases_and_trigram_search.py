from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.operations import TrigramExtension
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0002_fts_and_document_validity")]

    operations = [
        TrigramExtension(),
        migrations.AddField(
            model_name="knowledgechunk",
            name="search_label",
            field=models.TextField(blank=True),
        ),
        migrations.AddIndex(
            model_name="knowledgechunk",
            index=GinIndex(fields=["search_label"], name="knowledge_label_trgm_gin", opclasses=["gin_trgm_ops"]),
        ),
        migrations.CreateModel(
            name="KnowledgeTermAlias",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("canonical_term", models.CharField(max_length=200)),
                ("alias", models.CharField(max_length=200)),
                ("source_url", models.URLField(max_length=1000)),
                ("approval_status", models.CharField(choices=[("proposed", "검토중"), ("approved", "승인"), ("retired", "폐기")], default="proposed", max_length=20)),
                ("effective_from", models.DateField(blank=True, null=True)),
                ("effective_to", models.DateField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "공식 용어 별칭", "verbose_name_plural": "공식 용어 별칭"},
        ),
        migrations.AddConstraint(
            model_name="knowledgetermalias",
            constraint=models.UniqueConstraint(fields=("canonical_term", "alias"), name="knowledge_unique_term_alias"),
        ),
    ]
