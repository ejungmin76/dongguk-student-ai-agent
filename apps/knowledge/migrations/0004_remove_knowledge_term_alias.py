from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("knowledge", "0003_aliases_and_trigram_search")]

    operations = [
        migrations.DeleteModel(name="KnowledgeTermAlias"),
    ]
