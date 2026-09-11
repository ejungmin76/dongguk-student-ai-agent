import django.db.models.deletion
from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NdrimsMenu",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("menu_key", models.SlugField(max_length=120, unique=True)),
                ("title", models.CharField(max_length=200)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
                ("external_menu_id", models.CharField(blank=True, max_length=200)),
                ("source_url", models.URLField(max_length=1000)),
                ("verified_at", models.DateField()),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="children", to="ndrims.ndrimsmenu")),
            ],
            options={"verbose_name": "nDRIMS 메뉴", "verbose_name_plural": "nDRIMS 메뉴", "ordering": ["parent_id", "sort_order", "menu_key"]},
        ),
        migrations.AddConstraint(
            model_name="ndrimsmenu",
            constraint=models.CheckConstraint(condition=~Q(("pk", F("parent"))), name="ndrims_menu_not_own_parent"),
        ),
    ]
