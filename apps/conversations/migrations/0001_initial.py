# Generated manually for the initial bounded conversation-state schema.

import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ConversationSession",
            fields=[
                ("session_id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("subject_key", models.CharField(db_index=True, max_length=64)),
                ("status", models.CharField(choices=[("active", "활성"), ("expired", "만료")], default="active", max_length=16)),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("last_activity_at", models.DateTimeField(db_index=True)),
                ("version", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"verbose_name": "대화 세션", "verbose_name_plural": "대화 세션"},
        ),
        migrations.CreateModel(
            name="ConversationTurn",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sequence", models.PositiveIntegerField()),
                ("role", models.CharField(choices=[("user", "사용자"), ("assistant", "에이전트")], max_length=16)),
                ("message", models.TextField(max_length=2000)),
                ("response_metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("session", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="turns", to="conversations.conversationsession")),
            ],
            options={"verbose_name": "대화 턴", "verbose_name_plural": "대화 턴", "ordering": ["sequence"]},
        ),
        migrations.AddIndex(model_name="conversationsession", index=models.Index(fields=["subject_key", "last_activity_at"], name="conversatio_subject_2eb507_idx")),
        migrations.AddConstraint(model_name="conversationturn", constraint=models.UniqueConstraint(fields=("session", "sequence"), name="conversation_turn_sequence_unique")),
        migrations.AddIndex(model_name="conversationturn", index=models.Index(fields=["session", "sequence"], name="conversatio_session_7dce4f_idx")),
    ]
