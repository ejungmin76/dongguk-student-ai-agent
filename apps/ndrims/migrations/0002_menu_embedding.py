import pgvector.django
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("ndrims", "0001_initial")]

    operations = [
        migrations.AddField(model_name="ndrimsmenu", name="embedding", field=pgvector.django.VectorField(blank=True, dimensions=768, null=True)),
        migrations.AddField(model_name="ndrimsmenu", name="embedding_model", field=models.CharField(blank=True, max_length=100)),
        migrations.AddField(model_name="ndrimsmenu", name="embedding_source_hash", field=models.CharField(blank=True, max_length=64)),
        migrations.AddField(model_name="ndrimsmenu", name="embedded_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddIndex(
            model_name="ndrimsmenu",
            index=pgvector.django.HnswIndex(ef_construction=64, fields=["embedding"], m=16, name="ndrims_menu_embedding_hnsw", opclasses=["vector_cosine_ops"]),
        ),
    ]
